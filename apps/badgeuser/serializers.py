from rest_framework import serializers

# from rest_framework.exceptions import ValidationError
# from models import BadgeUser
# from badgeanalysis.validation_messages import BadgeValidationError
# from badgeanalysis.models import OpenBadge
from badgeuser.models import BadgeUser
from earner.serializers import EarnerBadgeSerializer
from consumer.serializers import ConsumerBadgeDetailSerializer
from rest_framework.authtoken.models import Token


class VerifiedEmailsField(serializers.Field):
    def to_representation(self, obj):
        addresses = []
        for emailaddress in obj.all():
            addresses.append(emailaddress.email)
        return addresses


class UserProfileField(serializers.Serializer):
    """
    Receives the entire BadgeUser instance and returns a dict
    with profile information
    """
    def to_representation(self, obj):
        addresses = []
        for emailaddress in obj.emailaddress_set.all():
            addresses.append(emailaddress.email)

        profile = {
            'id': obj.id,
            'name': obj.name,
            'username': obj.username,
            'earnerIds': addresses
        }
        return profile


class BadgeUserSerializer(serializers.ModelSerializer):
    """
    The BadgeUserSerializer brings together the necessary context information about
    a user's roles as Issuer, Earner, and Consumer
    """
    class Meta:
        model = BadgeUser
        fields = ('userProfile', 'earnerBadges', 'consumerBadges')

    userProfile = UserProfileField(source='*', read_only=True)
    earnerBadges = EarnerBadgeSerializer(many=True, read_only=True, source='earnerbadge_set')
    consumerBadges = ConsumerBadgeDetailSerializer(many=True, read_only=True, source='consumerbadge_set')
    # issuerRoles


class TokenSerializer(serializers.Serializer):
    username = serializers.SlugRelatedField(slug_field='username', queryset=BadgeUser.objects.all())
    replace = serializers.BooleanField(default=False, required=False, write_only=True)
    token = serializers.CharField(max_length=40, read_only=True)

    def create(self, validated_data, **kwargs):
        if validated_data.get('replace') is True:
            Token.objects.filter(user=validated_data.get('username')).delete()

        token, created = Token.objects.get_or_create(user=validated_data.get('username'))
        return token.key
