# Created by wiggins@concentricsky.com on 3/31/16.
import basic_models
from django.db import models
import cachemodel


class RecipientProfile(cachemodel.CacheModel):
    badge_user = models.ForeignKey('badgeuser.BadgeUser', null=True, blank=True)
    recipient_identifier = models.EmailField(max_length=1024)
    public = models.BooleanField(default=False)
    display_name = models.CharField(max_length=254)

    def __unicode__(self):
        if self.display_name:
            return self.display_name
        return self.recipient_identifier


class RecipientGroup(basic_models.DefaultModel):
    issuer = models.ForeignKey('issuer.Issuer')
    name = models.CharField(max_length=254)
    description = models.TextField(blank=True, null=True)
    members = models.ManyToManyField('RecipientProfile', through='recipient.RecipientGroupMembership')

    def __unicode__(self):
        return self.name

    def publish(self):
        super(RecipientGroup, self).publish()
        self.issuer.publish()

    def delete(self, *args, **kwargs):
        issuer = self.issuer
        ret = super(RecipientGroup, self).delete(*args, **kwargs)
        issuer.publish()
        return ret

    @cachemodel.cached_method(auto_publish=True)
    def cached_members(self):
        return self.members.all()


class RecipientGroupMembership(cachemodel.CacheModel):
    recipient_profile = models.ForeignKey('recipient.RecipientProfile')
    recipient_group = models.ForeignKey('recipient.RecipientGroup')
    membership_name = models.CharField(max_length=254)

    def publish(self):
        super(RecipientGroupMembership, self).publish()
        self.recipient_group.publish()

    def delete(self, *args, **kwargs):
        group = self.recipient_group
        ret = super(RecipientGroupMembership, self).delete(*args, **kwargs)
        group.publish()
        return ret


