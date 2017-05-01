import re

from allauth.account.adapter import get_adapter
from allauth.account.models import EmailConfirmation
from allauth.account.utils import user_pk_to_url_str, url_str_to_user_pk
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.core.urlresolvers import reverse
from rest_framework import permissions, status
from rest_framework.exceptions import NotAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from badgeuser.permissions import BadgeUserIsAuthenticatedUser
from badgeuser.serializers_v2 import BadgeUserTokenSerializerV2
from composition.tasks import process_email_verification
from entity.api import BaseEntityDetailView
from mainsite.models import BadgrApp
from mainsite.utils import OriginSetting
from .models import BadgeUser, CachedEmailAddress
from .serializers import BadgeUserProfileSerializer, EmailSerializer, BadgeUserTokenSerializerV1


class BadgeUserProfile(APIView):
    serializer_class = BadgeUserProfileSerializer
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        """
        Signup for a new account
        ---
        serializer: BadgeUserProfileSerializer
        """
        serializer = self.serializer_class(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        new_user = serializer.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get(self, request):
        """
        Get the current user's profile
        ---
        serializer: BadgeUserProfileSerializer
        """
        if request.user.is_anonymous():
            raise NotAuthenticated()

        serializer = BadgeUserProfileSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        """
        Update the current user's profile
        ---
        serializer: BadgeUserProfileSerializer
        """
        if request.user.is_anonymous():
            raise NotAuthenticated()

        serializer = BadgeUserProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated_user = serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)


class BadgeUserToken(BaseEntityDetailView):
    model = BadgeUser
    permission_classes = (BadgeUserIsAuthenticatedUser,)
    v1_serializer_class = BadgeUserTokenSerializerV1
    v2_serializer_class = BadgeUserTokenSerializerV2

    def get_object(self, request, **kwargs):
        return request.user

    def get(self, request, **kwargs):
        """
        Get the authenticated user's auth token.
        A new auth token will be created if none already exist for this user.
        """
        return super(BadgeUserToken, self).get(request, **kwargs)

    def put(self, request, **kwargs):
        """
        Invalidate the old token (if it exists) and create a new one.
        """
        request.user.replace_token()  # generate new token first
        return super(BadgeUserToken, self).put(request, **kwargs)


class BadgeUserEmailList(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        """
        Get a list of user's registered emails.
        ---
        serializer: EmailSerializer
        """
        instances = request.user.cached_emails()
        serializer = EmailSerializer(instances, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request):
        """
        Register a new unverified email.
        ---
        serializer: EmailSerializer
        parameters:
            - name: email
              description: The email to register
              required: true
              type: string
              paramType: form
        """
        serializer = EmailSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        email_address = serializer.save(user=request.user)
        email = serializer.data
        email_address.send_confirmation(request)
        return Response(email, status=status.HTTP_201_CREATED)


class BadgeUserEmailView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get_email(self, **kwargs):
        try:
            email_address = CachedEmailAddress.cached.get(**kwargs)
        except CachedEmailAddress.DoesNotExist:
            return None
        else:
            return email_address

class BadgeUserEmailDetail(BadgeUserEmailView):
    model = CachedEmailAddress

    def get(self, request, id):
        """
        Get detail for one registered email.
        ---
        serializer: EmailSerializer
        parameters:
            - name: id
              type: string
              paramType: path
              description: the id of the registered email
              required: true
        """
        email_address = self.get_email(pk=id)
        if email_address is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if email_address.user_id != self.request.user.id:
            return Response(status=status.HTTP_403_FORBIDDEN)

        serializer = EmailSerializer(email_address, context={'request': request})
        return Response(serializer.data)

    def delete(self, request, id):
        """
        Remove a registered email for the current user.
        ---
        parameters:
            - name: id
              type: string
              paramType: path
              description: the id of the registered email
              required: true
        """
        email_address = self.get_email(pk=id)
        if email_address is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if email_address.user_id != request.user.id:
            return Response(status=status.HTTP_403_FORBIDDEN)

        if email_address.primary:
            return Response({'error': "Can not remove primary email address"}, status=status.HTTP_400_BAD_REQUEST)

        if self.request.user.emailaddress_set.count() == 1:
            return Response({'error': "Can not remove only email address"}, status=status.HTTP_400_BAD_REQUEST)

        email_address.delete()
        return Response(status.HTTP_200_OK)

    def put(self, request, id):
        """
        Update a registered email for the current user.
        serializer: EmailSerializer
        ---
        parameters:
            - name: id
              type: string
              paramType: path
              description: the id of the registered email
              required: true
            - name: primary
              type: boolean
              paramType: form
              description: Should this email be primary contact for the user
              required: false
            - name: resend
              type: boolean
              paramType: form
              description: Request the verification email be resent
              required: false
        """
        email_address = self.get_email(pk=id)
        if email_address is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if email_address.user_id != request.user.id:
            return Response(status=status.HTTP_403_FORBIDDEN)

        if email_address.verified:
            if request.data.get('primary'):
                email_address.set_as_primary()
                email_address.publish()
        else:
            if request.data.get('resend'):
                email_address.send_confirmation(request=request)

        serializer = EmailSerializer(email_address, context={'request': request})
        serialized = serializer.data
        return Response(serialized, status=status.HTTP_200_OK)


class UserTokenMixin(object):
    def _get_user(self, uidb36):
        User = get_user_model()
        try:
            pk = url_str_to_user_pk(uidb36)
            return User.objects.get(pk=pk)
        except (ValueError, User.DoesNotExist):
            return None


class BadgeUserForgotPassword(UserTokenMixin, BadgeUserEmailView):
    permission_classes = ()

    def get(self, request, *args, **kwargs):
        badgr_app = BadgrApp.objects.get_current(request)
        redirect_url = badgr_app.forgot_password_redirect
        token = request.GET.get('token','')
        tokenized_url = "{}{}".format(redirect_url, token)
        return Response(status=status.HTTP_302_FOUND, headers={'Location': tokenized_url})

    def post(self, request):
        """
        Request an account recovery email.
        ---
        parameters:
            - name: email
              type: string
              paramType: form
              description: The email address on file to send recovery email
              required: true
        """

        email = request.data.get('email')
        email_address = self.get_email(email=email)
        if email_address is None:
            # return 200 here because we don't want to expose information about which emails we know about
            return Response(status=status.HTTP_200_OK)

        # taken from allauth.account.forms.ResetPasswordForm

        # fetch user from database directly to avoid cache
        UserCls = get_user_model()
        try:
            user = UserCls.objects.get(pk=email_address.user_id)
        except UserCls.DoesNotExist:
            return Response(status=status.HTTP_200_OK)

        temp_key = default_token_generator.make_token(user)
        token = "{uidb36}-{key}".format(uidb36=user_pk_to_url_str(user),
                                        key=temp_key)
        reset_url = "{}{}?token={}".format(OriginSetting.HTTP, reverse('v1_api_user_forgot_password'), token)

        email_context = {
            "site": get_current_site(request),
            "user": user,
            "password_reset_url": reset_url,
        }
        get_adapter().send_mail('account/email/password_reset_key', email, email_context)

        return Response(status=status.HTTP_200_OK)

    def put(self, request):
        """
        Recover an account and set a new password.
        ---
        parameters:
            - name: token
              type: string
              paramType: form
              description: The token received in the recovery email
              required: true
            - name: password
              type: string
              paramType: form
              description: The new password to use
              required: true
        """
        token = request.data.get('token')
        password = request.data.get('password')

        matches = re.search(r'([0-9A-Za-z]+)-(.*)', token)
        if not matches:
            return Response({'error': "Invalid Token"}, status=status.HTTP_404_NOT_FOUND)
        uidb36 = matches.group(1)
        key = matches.group(2)
        if not (uidb36 and key):
            return Response({'error': "Invalid Token"}, status=status.HTTP_404_NOT_FOUND)

        user = self._get_user(uidb36)
        if user is None:
            return Response({'error': "Invalid token"}, status=status.HTTP_404_NOT_FOUND)

        if not default_token_generator.check_token(user, key):
            return Response({'error': "invalid token"}, status=status.HTTP_404_NOT_FOUND)

        user.set_password(password)
        user.save()
        return Response(status=status.HTTP_200_OK)


class BadgeUserEmailConfirm(UserTokenMixin, BadgeUserEmailView):
    permission_classes = ()

    def get(self, request, **kwargs):
        """
        Confirm an email address with a token provided in an email
        ---
        parameters:
            - name: token
              type: string
              paramType: form
              description: The token received in the recovery email
              required: true
        """

        token = request.query_params.get('token')

        try:
            emailconfirmation = EmailConfirmation.objects.get(pk=kwargs.get('confirm_id'))
        except EmailConfirmation.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        try:
            email_address = CachedEmailAddress.cached.get(pk=emailconfirmation.email_address_id)
        except CachedEmailAddress.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        matches = re.search(r'([0-9A-Za-z]+)-(.*)', token)
        if not matches:
            return Response(status=status.HTTP_404_NOT_FOUND)
        uidb36 = matches.group(1)
        key = matches.group(2)
        if not (uidb36 and key):
            return Response(status=status.HTTP_404_NOT_FOUND)

        user = self._get_user(uidb36)
        if user is None or not default_token_generator.check_token(user, key):
            return Response(status=status.HTTP_404_NOT_FOUND)

        if email_address.user != user:
            return Response(status=status.HTTP_404_NOT_FOUND)

        old_primary = CachedEmailAddress.objects.get_primary(user)
        if old_primary is None:
            email_address.primary = True
        email_address.verified = True
        email_address.save()

        process_email_verification.delay(email_address.pk)

        # get badgr_app url redirect
        redirect_url = get_adapter().get_email_confirmation_redirect_url(request)

        return Response(status=status.HTTP_302_FOUND, headers={'Location': redirect_url})
