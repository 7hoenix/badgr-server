from django.db import models
from django.conf import settings
from django.core.mail import send_mail
import django.template.loader

import uuid
import datetime
import json

import basic_models
import cachemodel
from jsonfield import JSONField

from autoslug import AutoSlugField
from mainsite.utils import slugify
from badgeanalysis.models import OpenBadge
from badgeanalysis.utils import generate_sha256_hashstring, bake


"""
EarnerNotification sends a template-based email informing the earner of any remotely hosted badge assertion.
"""
class EarnerNotification(basic_models.TimestampedModel):
    url = models.URLField(verbose_name='Assertion URL', max_length=2048)
    email = models.EmailField(max_length=254, blank=False)
    badge = models.ForeignKey(OpenBadge, blank=True, null=True)

    def get_form(self):
        from issuer.forms import NotifyEarnerForm
        return NotifyEarnerForm(instance=self)

    @classmethod
    def detect_existing(cls, url):
        try:
            cls.objects.get(url=url)
        except EarnerNotification.DoesNotExist:
            return False
        except EarnerNotification.MultipleObjectsReturned:
            return False
        else:
            return True

    def send_email(self):
        http_origin = getattr(settings, 'HTTP_ORIGIN', None)
        ob = self.badge
        email_context = {
            'badge_name': ob.ldProp('bc', 'name'),
            'badge_description': ob.ldProp('bc', 'description'),
            'issuer_name': ob.ldProp('iss', 'name'),
            'issuer_url': ob.ldProp('iss', 'url'),
            'image_url': ob.get_baked_image_url(**{'origin': http_origin})
        }
        t = django.template.loader.get_template('issuer/notify_earner_email.txt')
        ht = django.template.loader.get_template('issuer/notify_earner_email.html')
        text_output_message = t.render(email_context)
        html_output_message = ht.render(email_context)
        mail_meta = {
            'subject': 'Congratulations, you earned a badge!',
            # 'from_address': email_context['issuer_name'] + ' Badges <noreply@oregonbadgealliance.org>',
            'from_address': 'Oregon Badge Alliance' + ' Badges <noreply@oregonbadgealliance.org>',
            'to_addresses': [self.email]
        }

        try:
            send_mail(
                mail_meta['subject'],
                text_output_message,
                mail_meta['from_address'],
                mail_meta['to_addresses'],
                fail_silently=False,
                html_message=html_output_message
            )
        except Exception as e:
            raise e


"""
A base class for Issuer badge objects, those that are part of badges issue
by users on this system.
"""
class AbstractBadgeObject(cachemodel.CacheModel):
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(getattr(settings, 'AUTH_USER_MODEL'), blank=True, null=True)

    badge_object = JSONField()

    class Meta:
        abstract = True

    # Subclasses must implement 'slug' as a field
    def get_slug(self):
        if self.slug is None or self.slug == '':
            # If there isn't a slug, object has been initialized but not saved,
            # so this change will be saved later in present process; fine not to save now.
            self.slug = slugify(self.name)
        return self.slug

    def get_full_url(self):
        return str(getattr(settings, 'HTTP_ORIGIN')) + self.get_absolute_url()

    # Handle updating badge_object in case initial slug guess was modified on save because of a uniqueness constraint
    def process_real_full_url(self):
        self.badge_object['id'] = self.get_full_url()

    def save(self):
        super(AbstractBadgeObject, self).save()

        # Make adjustments if the slug has changed due to uniqueness constraint
        object_id = self.badge_object.get('id')
        if object_id != self.get_full_url():
            self.process_real_full_url()
            super(AbstractBadgeObject, self).save()

    # Quick getter for values stored in the badge_object
    def prop(self, property_name):
        return self.badge_object.get(property_name)


"""
Open Badges Specification IssuerOrg object
"""
class Issuer(AbstractBadgeObject):
    name = models.CharField(max_length=1024)
    slug = AutoSlugField(max_length=255, populate_from='name', unique=True, blank=False, editable=True)

    owner = models.ForeignKey(getattr(settings, 'AUTH_USER_MODEL'), related_name='owner', on_delete=models.PROTECT, null=False)
    # editors may define badgeclasses and issue badges
    editors = models.ManyToManyField(getattr(settings, 'AUTH_USER_MODEL'), db_table='issuer_editors', related_name='issuers_editor_for')
    # staff may issue badges from badgeclasses that already exist
    staff = models.ManyToManyField(getattr(settings, 'AUTH_USER_MODEL'), db_table='issuer_staff', related_name='issuers_staff_for')

    image = models.ImageField(upload_to='uploads/issuers', blank=True)

    def get_absolute_url(self):
        return "/public/issuers/%s" % self.get_slug()


"""
Open Badges Specification BadgeClass object
"""
class IssuerBadgeClass(AbstractBadgeObject):
    issuer = models.ForeignKey(Issuer, blank=False, null=False, on_delete=models.PROTECT, related_name="badgeclasses")
    name = models.CharField(max_length=255)
    slug = AutoSlugField(max_length=255, populate_from='name', unique=True, blank=False, editable=True)
    criteria_text = models.TextField(blank=True, null=True)  # TODO: refactor to be a rich text field via ckeditor
    image = models.ImageField(upload_to='uploads/badges', blank=True)

    @property
    def owner(self):
        return self.issuer.owner

    # TODO: Here's the replacement for criteria_url
    @property
    def criteria_url(self):
        return self.badge_object.get('criteria')

    def get_absolute_url(self):
        return "/public/badges/%s" % self.get_slug()

    def process_real_full_url(self):
        self.badge_object['image'] = self.get_full_url() + '/image'
        if self.badge_object.get('criteria') is None or self.badge_object.get('criteria') == '':
            self.badge_object['criteria'] = self.get_full_url() + '/criteria'

        super(IssuerBadgeClass, self).process_real_full_url()


"""
Open Badges Specification Assertion object
"""
class IssuerAssertion(AbstractBadgeObject):
    badgeclass = models.ForeignKey(
        IssuerBadgeClass,
        blank=False,
        null=False,
        on_delete=models.PROTECT,
        related_name='assertions'
    )
    email = models.EmailField(max_length=255, blank=False, null=False)
    # in the future, obi_issuer might be different from badgeclass.obi_issuer sometimes
    issuer = models.ForeignKey(Issuer, blank=False, null=False, related_name='assertions')
    slug = AutoSlugField(max_length=255, populate_from='get_new_slug', unique=True, blank=False, editable=False)
    image = models.ImageField(upload_to='issued/badges', blank=True)
    revoked = models.BooleanField(default=False)
    revocation_reason = models.CharField(max_length=255, blank=True, null=True, default=None)

    @property
    def owner(self):
        return self.obi_issuer.owner

    def get_absolute_url(self):
        return "/public/assertions/%s" % self.get_slug()

    def get_new_slug(self):
        return str(uuid.uuid4())

    def get_slug(self):
        if self.slug is None or self.slug == '':
            self.slug = self.get_new_slug()
        return self.slug

    def save(self, *args, **kwargs):
        if self.pk is None:
            salt = self.get_new_slug()
            self.badge_object['recipient']['salt'] = salt
            self.badge_object['recipient']['identity'] = generate_sha256_hashstring(self.email, salt)

            self.created_at = datetime.datetime.now()
            self.badge_object['issuedOn'] = self.created_at.isoformat()

            self.image = bake(self.badgeclass.image, json.dumps(self.badge_object, indent=2))
            self.image.open()

        if self.revoked is False:
            self.revocation_reason = None
        # Don't need to worry about id uniqueness, so can skip immediate super's save method.
        super(AbstractBadgeObject, self).save(*args, **kwargs)

    def notify_earner(self):
        """
        Sends an email notification to the badge earner.
        This process involves creating a badgeanalysis.models.OpenBadge
        returns the EarnerNotification instance.

        TODO: consider making this an option on initial save and having a foreign key to
        the notification model instance (which would link through to the OpenBadge)
        """
        http_origin = getattr(settings, 'HTTP_ORIGIN', None)
        try:
            email_context = {
                'badge_name': self.badgeclass.name,
                'badge_description': self.badgeclass.prop('description'),
                'issuer_name': self.issuer.name,
                'issuer_url': self.issuer.prop('url'),
                'image_url': self.get_full_url() + '/image'
            }
        except KeyError as e:
            # for when a property isn't stored right in a badge_object
            raise e

        t = django.template.loader.get_template('issuer/notify_earner_email.txt')
        ht = django.template.loader.get_template('issuer/notify_earner_email.html')
        text_output_message = t.render(email_context)
        html_output_message = ht.render(email_context)
        mail_meta = {
            'subject': 'Congratulations, you earned a badge!',
            # 'from_address': email_context['issuer_name'] + ' Badges <noreply@oregonbadgealliance.org>',
            'from_address': 'Oregon Badge Alliance' + ' Badges <noreply@oregonbadgealliance.org>',
            'to_addresses': [self.email]
        }

        try:
            send_mail(
                mail_meta['subject'],
                text_output_message,
                mail_meta['from_address'],
                mail_meta['to_addresses'],
                fail_silently=False,
                html_message=html_output_message
            )
        except Exception as e:
            raise e
