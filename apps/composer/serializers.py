import json

from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework import serializers

from integrity_verifier import RemoteBadgeInstance, AnalyzedBadgeInstance
from integrity_verifier.utils import get_instance_url_from_image, get_instance_url_from_assertion
from credential_store.models import StoredBadgeInstance
from credential_store.format import V1InstanceSerializer

from .models import Collection, StoredBadgeInstanceCollection

RECIPIENT_ERROR = {
    'recipient':
    "Badge recipient was not among any of user's confirmed identifiers"
}


class EarnerBadgeSerializer(serializers.Serializer):
    recipient_id = serializers.CharField(required=False)
    id = serializers.IntegerField(required=False)

    assertion = serializers.DictField(required=False, write_only=True)
    url = serializers.URLField(required=False, write_only=True)
    image = serializers.ImageField(required=False, write_only=True)

    json = V1InstanceSerializer(read_only=True)
    errors = serializers.ListField(read_only=True)

    def to_representation(self, obj):
        if self.context.get('format', 'v1') == 'plain':
            self.fields.json = serializers.DictField(read_only=True)
        return super(EarnerBadgeSerializer, self).to_representation(obj)

    def validate(self, data):
        # Remove empty DictField
        if data.get('assertion') == {}:
            data.pop('assertion', None)

        instance_input_fields = set(('url', 'image', 'assertion'))
        valid_inputs = {key: data.get(key) for
                        key in instance_input_fields.intersection(data.keys())}

        if len(valid_inputs.keys()) != 1:
            raise serializers.ValidationError(
                "Only one instance input field allowed. Recieved "
                + json.dumps(valid_inputs.keys())
            )

        return data

    def create(self, validated_data):
        user = self.context.get('request').user

        if validated_data.get('url') is not None:
            url = validated_data.get('url')
        elif validated_data.get('image') is not None:
            image = validated_data.get('image')
            image.open()
            url = get_instance_url_from_image(image)
        elif validated_data.get('assertion') is not None:
            url = get_instance_url_from_assertion(
                validated_data.get('assertion')
            )

        try:
            rbi = RemoteBadgeInstance(url)
        except DjangoValidationError as e:
            raise e

        abi = AnalyzedBadgeInstance(rbi, recipient_ids=[id.email for id in user.emailaddress_set.all()])
        if len(
            [x for x in abi.non_component_errors if x[0] == 'error.recipient']
        ) != 0:
            raise serializers.ValidationError(RECIPIENT_ERROR)

        if not abi.is_valid():
            raise serializers.ValidationError(abi.all_errors())
        else:
            new_instance = StoredBadgeInstance.from_analyzed_instance(
                abi, **{'recipient_user': user}
            )

            return new_instance


class EarnerBadgeReferenceListSerializer(serializers.ListSerializer):

    def create(self, validated_data):
        collection = self.context.get('collection')
        user = self.context.get('request').user

        if not isinstance(validated_data, list):
            validated_data = [validated_data]

        id_set = [x.get('instance', {}).get('id') for x in validated_data]

        badge_set = StoredBadgeInstance.objects.filter(
            recipient_user=user, id__in=id_set
        ).exclude(collection=collection)

        new_records = []

        for badge in badge_set:
            description = [
                item for item in validated_data if
                item.get('instance', {}).get('id') == badge.id
            ][0].get('description', '')

            new_records.append(StoredBadgeInstanceCollection(
                instance=badge,
                collection=collection,
                description=description
            ))

        if len(new_records) > 0:
            return StoredBadgeInstanceCollection.objects.bulk_create(new_records)
        else:
            return new_records


class EarnerBadgeReferenceSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=True, source='instance.id')
    description = serializers.CharField(required=False)

    class Meta:
        list_serializer_class = EarnerBadgeReferenceListSerializer

    def create(self, validated_data):
        collection = self.context.get('collection')
        user = self.context.get('request').user

        badge_query = StoredBadgeInstance.objects.filter(
            recipient_user=user,
            id=validated_data.get('instance',{}).get('id'),
        ).exclude(collection=collection)

        if not badge_query.exists():
            return []

        description = validated_data.get('description', '')

        new_record = StoredBadgeInstanceCollection(
            instance=badge_query[0], collection=collection,
            description=description
        )

        new_record.save()
        return new_record


class CollectionSerializer(serializers.Serializer):
    name = serializers.CharField(required=True, max_length=128)
    slug = serializers.CharField(required=False, max_length=128)
    description = serializers.CharField(required=False, max_length=255)
    badges = serializers.ListField(
        required=False, child=EarnerBadgeReferenceSerializer(),
        source='storedbadgeinstancecollection_set.all'
    )

    def create(self, validated_data):
        user = self.context.get('request').user

        new_collection = Collection(
            name=validated_data.get('name'),
            slug=validated_data.get('slug', None),
            description=validated_data.get('description', ''),
            recipient=user
        )

        if validated_data.get('badges') is not None:
            raise NotImplementedError("Adding badges to collection on creation not implemented.")

        new_collection.save()
        return new_collection
