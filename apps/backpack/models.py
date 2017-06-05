# encoding: utf-8
from __future__ import unicode_literals

import cachemodel
from django.db import models, transaction

from entity.models import BaseVersionedEntity
from issuer.models import BaseAuditedModel, BadgeInstance


class BackpackCollection(BaseAuditedModel, BaseVersionedEntity):
    name = models.CharField(max_length=128)
    description = models.CharField(max_length=255, blank=True)
    share_hash = models.CharField(max_length=255, null=False, blank=True)

    # slug has been deprecated, but keep for legacy collections redirects
    slug = models.CharField(max_length=254, blank=True, null=True, default=None)

    assertions = models.ManyToManyField('issuer.BadgeInstance', blank=True, through='backpack.BackpackCollectionBadgeInstance')

    @cachemodel.cached_method(auto_publish=True)
    def cached_badgeinstances(self):
        return self.assertions.all()

    @property
    def badge_items(self):
        return self.cached_badgeinstances()

    @badge_items.setter
    def badge_items(self, value):
        """
        Update this collection's list of BackpackCollectionBadgeInstance from a list of BadgeInstance EntityRelatedFieldV2 serializer data
        """
        with transaction.atomic():
            existing_badges = {b.entity_id: b for b in self.badge_items}
            # add missing badges
            for badge_entity_id in value:
                try:
                    badgeinstance = BadgeInstance.cached.get(entity_id=badge_entity_id)
                except BadgeInstance.DoesNotExist:
                    pass
                else:
                    if badge_entity_id not in existing_badges.keys():
                        BackpackCollectionBadgeInstance.cached.get_or_create(
                            collection=self,
                            badgeinstance=badgeinstance
                        )

            # remove badges no longer in collection
            for badge_entity_id, badgeinstance in existing_badges.items():
                if badge_entity_id not in value:
                    BackpackCollectionBadgeInstance.objects.filter(
                        collection=self,
                        badgeinstance=badgeinstance
                    ).delete()


class BackpackCollectionBadgeInstance(cachemodel.CacheModel):
    collection = models.ForeignKey('backpack.BackpackCollection')
    badgeinstance = models.ForeignKey('issuer.BadgeInstance')

    def publish(self):
        super(BackpackCollectionBadgeInstance, self).publish()
        self.collection.publish()

    def delete(self):
        super(BackpackCollectionBadgeInstance, self).delete()
        self.collection.publish()

