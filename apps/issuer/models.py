import datetime
import json
import re
import uuid
import cachemodel

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.db import models
from django.template.loader import get_template

from openbadges_bakery import bake

from mainsite.models import (AbstractIssuer, AbstractBadgeClass,
                             AbstractBadgeInstance)

from .utils import generate_sha256_hashstring, badgr_import_url


AUTH_USER_MODEL = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')


class Issuer(AbstractIssuer):
    owner = models.ForeignKey(AUTH_USER_MODEL, related_name='issuers',
                              on_delete=models.PROTECT, null=False)
    staff = models.ManyToManyField(AUTH_USER_MODEL, through='IssuerStaff')

    @cachemodel.cached_method(auto_publish=True)
    def cached_staff(self):
        return self.staff.all()

    @cachemodel.cached_method(auto_publish=True)
    def cached_editors(self):
        UserModel = get_user_model()
        return UserModel.objects.filter(issuerstaff__issuer=self, issuerstaff__editor=True)


class IssuerStaff(models.Model):
    issuer = models.ForeignKey(Issuer)
    user = models.ForeignKey(AUTH_USER_MODEL)
    editor = models.BooleanField(default=False)

    class Meta:
        unique_together = ('issuer', 'user')


class BadgeClass(AbstractBadgeClass):
    issuer = models.ForeignKey(Issuer, blank=False, null=False,
                               on_delete=models.PROTECT,
                               related_name="badgeclasses")


class BadgeInstance(AbstractBadgeInstance):
    badgeclass = models.ForeignKey(BadgeClass, blank=False, null=False,
                                   on_delete=models.PROTECT,
                                   related_name='badgeinstances')
    issuer = models.ForeignKey(Issuer, blank=False, null=False)

    @property
    def extended_json(self):
        extended_json = self.json
        extended_json['badge'] = self.badgeclass.json
        extended_json['badge']['issuer'] = self.issuer.json

        return extended_json

    def get_absolute_url(self):
        return reverse('badgeinstance_json', kwargs={'slug': self.slug})

    def get_new_slug(self):
        return str(uuid.uuid4())

    def save(self, *args, **kwargs):
        if self.pk is None:
            self.json['recipient']['salt'] = salt = self.get_new_slug()
            self.json['recipient']['identity'] = generate_sha256_hashstring(self.email, salt)

            self.created_at = datetime.datetime.now()
            self.json['issuedOn'] = self.created_at.isoformat()

            imageFile = default_storage.open(self.badgeclass.image.file.name)
            self.image = bake(imageFile, json.dumps(self.json, indent=2))

            self.image.open()

        if self.revoked is False:
            self.revocation_reason = None

        # TODO: If we don't want AutoSlugField to ensure uniqueness, configure it
        super(BadgeInstance, self).save(*args, **kwargs)

    def notify_earner(self):
        """
        Sends an email notification to the badge earner.
        This process involves creating a badgeanalysis.models.OpenBadge
        returns the EarnerNotification instance.

        TODO: consider making this an option on initial save and having a foreign key to
        the notification model instance (which would link through to the OpenBadge)
        """
        try:
            email_context = {
                'badge_name': self.badgeclass.name,
                'badge_description': self.badgeclass.prop('description'),
                'issuer_name': re.sub(r'[^\w\s]+', '', self.issuer.name, 0, re.I),
                'issuer_url': self.issuer.prop('url'),
                'issuer_image_url': self.issuer.get_full_url() + '/image',
                'image_url': self.get_full_url() + '/image',
                'badgr_import_url': badgr_import_url(self)
            }
        except KeyError as e:
            # A property isn't stored right in json
            raise e

        text_template = get_template('issuer/notify_earner_email.txt')
        html_template = get_template('issuer/notify_earner_email.html')
        text_output_message = text_template.render(email_context)
        html_output_message = html_template.render(email_context)
        mail_meta = {
            'subject': 'Congratulations, you earned a badge!',
            'from_address': '"' + email_context['issuer_name'] + '" <' + getattr(settings, 'DEFAULT_FROM_EMAIL') + '>',
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
