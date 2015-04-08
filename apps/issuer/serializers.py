from rest_framework import serializers

from mainsite.serializers import WritableJSONField

from .models import Issuer, BadgeClass, BadgeInstance
import utils


class AbstractComponentSerializer(serializers.Serializer):
    created_at = serializers.DateTimeField(read_only=True)
    created_by = serializers.HyperlinkedRelatedField(view_name='user_detail', lookup_field='username', read_only=True)


class IssuerSerializer(AbstractComponentSerializer):
    json = WritableJSONField(max_length=16384, read_only=True, required=False)
    name = serializers.CharField(max_length=1024)
    slug = serializers.CharField(max_length=255, allow_blank=True, required=False)
    image = serializers.ImageField(allow_empty_file=False, use_url=True, required=False)
    email = serializers.EmailField(max_length=255, required=True, write_only=True)
    description = serializers.CharField(max_length=1024, required=True, write_only=True)
    url = serializers.URLField(max_length=1024, required=True, write_only=True)
    owner = serializers.HyperlinkedRelatedField(view_name='user_detail', lookup_field='username', read_only=True)
    editors = serializers.HyperlinkedRelatedField(many=True, view_name='user_detail', lookup_field='username', read_only=True)
    staff = serializers.HyperlinkedRelatedField(many=True, view_name='user_detail', lookup_field='username', read_only=True)

    def validate(self, data):
        # TODO: ensure email is a confirmed email in owner/creator's account
        # ^^^ that validation requires the request.user, which might be in self.context
        return data

    def create(self, validated_data, **kwargs):
        validated_data['json'] = {
            '@context': utils.CURRENT_OBI_CONTEXT_IRI,
            'type': 'Issuer',
            'name': validated_data.get('name'),
            'url': validated_data.pop('url'),
            'email': validated_data.pop('email'),
            'description': validated_data.pop('description')
        }

        new_issuer = Issuer(**validated_data)

        # Add id to new issuer, which is depenent on an instance being initiated
        new_issuer.json['id'] = new_issuer.get_full_url()

        if validated_data.get('image') is not None:
            new_issuer.json['image'] = new_issuer.get_full_url() + '/image'

        new_issuer.save()

        return new_issuer


class IssuerRoleActionSerializer(serializers.Serializer):
    """ A serializer used for validating user role change POSTS """
    action = serializers.ChoiceField(('add', 'remove',), allow_blank=True)
    username = serializers.CharField(allow_blank=False)


class BadgeClassSerializer(AbstractComponentSerializer):
    issuer = serializers.HyperlinkedRelatedField(view_name='issuer_json', read_only=True, lookup_field='slug')
    json = WritableJSONField(max_length=16384, read_only=True, required=False)
    name = serializers.CharField(max_length=255)
    image = serializers.ImageField(allow_empty_file=False, use_url=True)
    slug = serializers.CharField(max_length=255, allow_blank=True, required=False)
    criteria = serializers.CharField(allow_blank=True, required=False, write_only=True)

    def validate_image(self, image):
        # TODO: Make sure it's a PNG (square if possible), and remove any baked-in badge assertion that exists.
        return image

    def validate(self, data):

        if utils.test_probable_url(data.get('criteria')):
            data['criteria_url'] = data.pop('criteria')
        elif not isinstance(data.get('criteria'), (str, unicode)):
            raise serializers.ValidationError(
                "Provided criteria text could not be properly processed as URL or plain text."
            )
        else:
            data['criteria_text'] = data.pop('criteria')

        return data

    def create(self, validated_data, **kwargs):

        # TODO: except KeyError on pops for invalid keys? or just ensure they're there with validate()
        # "gets" data that must be in both model and model.json,
        # "pops" data that shouldn't be sent to model init
        validated_data['json'] = {
            '@context': utils.CURRENT_OBI_CONTEXT_IRI,
            'type': 'BadgeClass',
            'name': validated_data.get('name'),
            'description': validated_data.pop('description'),
            'issuer': validated_data.get('issuer').get_full_url()
        }

        # If criteria_url, put it in the json field directly:
        try:
            validated_data['json']['criteria'] = validated_data.pop('criteria_url')
        except KeyError:
            pass

        # remove criteria_text from data before model init
        try:
            criteria_text = validated_data.pop('criteria_text')
        except KeyError:
            criteria_text = ''

        new_badgeclass = BadgeClass(**validated_data)

        full_url = new_badgeclass.get_full_url()
        # Augment with id, image and criteria link
        new_badgeclass.json['id'] = full_url
        new_badgeclass.json['image'] = full_url + '/image'

        if new_badgeclass.json.get('criteria')is None or criteria_text == '':
            new_badgeclass.json['criteria'] = full_url + '/criteria'
            new_badgeclass.criteria_text = criteria_text

        new_badgeclass.save()
        return new_badgeclass


class BadgeInstanceSerializer(AbstractComponentSerializer):
    json = WritableJSONField(max_length=16384, read_only=True, required=False)
    issuer = serializers.HyperlinkedRelatedField(view_name='issuer_json', read_only=True,  lookup_field='slug')
    badgeclass = serializers.HyperlinkedRelatedField(view_name='badgeclass_json', read_only=True, lookup_field='slug')
    slug = serializers.CharField(max_length=255, read_only=True)
    image = serializers.ImageField(read_only=True)  # use_url=True, might be necessary
    email = serializers.EmailField(max_length=255)
    evidence = serializers.URLField(write_only=True, required=False, allow_blank=True, max_length=1024)

    revoked = serializers.BooleanField(read_only=True)
    revocation_reason = serializers.CharField(read_only=True)

    create_notification = serializers.BooleanField(write_only=True, required=False)

    def create(self, validated_data, **kwargs):
        # Assemble Badge Object
        validated_data['json'] = {
            # 'id': TO BE ADDED IN SAVE
            '@context': utils.CURRENT_OBI_CONTEXT_IRI,
            'type': 'Assertion',
            'recipient': {
                'type': 'email',
                'hashed': True
                # 'email': TO BE ADDED IN SAVE
            },
            'badge': validated_data.get('badgeclass').get_full_url(),
            'verify': {
                'type': 'hosted'
                # 'url': TO BE ADDED IN SAVE
            }

        }

        try:
            create_notification = validated_data.pop('create_notification')
        except KeyError:
            create_notification = False

        try:
            evidence = validated_data.pop('evidence')
        except KeyError:
            pass
        else:
            validated_data['json']['evidence'] = evidence

        new_assertion = BadgeInstance(**validated_data)

        # Augment json with id
        full_url = new_assertion.get_full_url()  # this sets the slug
        new_assertion.json['id'] = full_url
        new_assertion.json['verify']['url'] = full_url
        new_assertion.json['image'] = full_url + '/image'

        new_assertion.save()

        if create_notification is True:
            new_assertion.notify_earner()

        return new_assertion
