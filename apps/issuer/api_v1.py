# encoding: utf-8
from __future__ import unicode_literals
import urlparse

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import UploadedFile
from rest_framework import status, authentication
from rest_framework.exceptions import ValidationError, PermissionDenied, NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

import badgrlog
from badgeuser.models import CachedEmailAddress
from entity.api import BaseEntityListView, BaseEntityDetailView
from issuer.models import Issuer, IssuerStaff, BadgeClass, BadgeInstance
from issuer.permissions import (MayIssueBadgeClass, MayEditBadgeClass,
                                IsEditor, IsStaff, IsOwnerOrStaff, ApprovedIssuersOnly)
from issuer.serializers_v1 import (IssuerSerializerV1, BadgeClassSerializerV1,
                                   BadgeInstanceSerializerV1, IssuerRoleActionSerializerV1,
                                   IssuerStaffSerializerV1)
from issuer.serializers_v2 import IssuerSerializerV2
from issuer.utils import get_badgeclass_by_identifier
from mainsite.permissions import AuthenticatedWithVerifiedEmail


logger = badgrlog.BadgrLogger()


class AbstractIssuerAPIEndpoint(APIView):
    authentication_classes = (
        authentication.TokenAuthentication,
        authentication.SessionAuthentication,
        authentication.BasicAuthentication,
    )
    permission_classes = (AuthenticatedWithVerifiedEmail,)

    def get_object(self, slug, queryset=None):
        """ Ensure user has permissions on Issuer """

        queryset = queryset if queryset is not None else self.queryset
        try:
            obj = queryset.get(slug=slug)
        except self.model.DoesNotExist:
            return None

        try:
            self.check_object_permissions(self.request, obj)
        except PermissionDenied:
            return None
        else:
            return obj

    def get_list(self, slug=None, queryset=None, related=None):
        """ Ensure user has permissions on Issuer, and return badgeclass queryset if so. """
        queryset = queryset if queryset is not None else self.queryset

        obj = queryset
        if slug is not None:
            obj = queryset.filter(slug=slug)
        if related is not None:
            obj = queryset.select_related(related)

        if not obj.exists():
            return self.model.objects.none()

        try:
            self.check_object_permissions(self.request, obj[0])
        except PermissionDenied:
            return self.model.objects.none()
        else:
            return obj


class IssuerStaffList(AbstractIssuerAPIEndpoint):
    """ View or modify an issuer's staff members and privileges """
    role = 'staff'
    queryset = Issuer.objects.all()
    model = Issuer
    permission_classes = (AuthenticatedWithVerifiedEmail, IsOwnerOrStaff,)

    def get(self, request, slug):
        """
        Get a list of users associated with a role on an Issuer
        ---
        parameters:
            - name: slug
              type: string
              paramType: path
              description: The slug of the issuer whose roles to view.
              required: true
        """
        current_issuer = self.get_object(slug)

        if current_issuer is None:
            return Response(
                "Issuer %s not found. Authenticated user must have owner, editor or staff rights on the issuer." % slug,
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = IssuerStaffSerializerV1(
            IssuerStaff.objects.filter(issuer=current_issuer),
            many=True
        )

        if len(serializer.data) == 0:
            return Response([], status=status.HTTP_200_OK)
        return Response(serializer.data)

    def post(self, request, slug):
        """
        Add or remove a user from a role on an issuer. Limited to Owner users only.
        ---
        parameters:
            - name: slug
              type: string
              paramType: path
              description: The slug of the issuer whose roles to modify.
              required: true
            - name: action
              type: string
              paramType: form
              description: The action to perform on the user. Must be one of 'add', 'modify', or 'remove'.
              required: true
            - name: username
              type: string
              paramType: form
              description: The username of the user to add or remove from this role.
              required: false
            - name: email
              type: string
              paramType: form
              description: A verified email address of the user to add or remove from this role.
              required: false
            - name: editor
              type: boolean
              paramType: form
              description: Should the user have editor privileges?
              defaultValue: false
              required: false
        """
        # validate POST data
        serializer = IssuerRoleActionSerializerV1(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        current_issuer = self.get_object(slug)
        if current_issuer is None:
            return Response(
                "Issuer %s not found. Authenticated user must be Issuer's owner to modify user permissions." % slug,
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            if serializer.validated_data.get('username'):
                user_id = serializer.validated_data.get('username')
                user_to_modify = get_user_model().objects.get(username=user_id)
            else:
                user_id = serializer.validated_data.get('email')
                user_to_modify = CachedEmailAddress.objects.get(
                    email=user_id).user
        except (get_user_model().DoesNotExist, CachedEmailAddress.DoesNotExist,):
            error_text = "User {} not found. Cannot modify Issuer permissions.".format(user_id)
            if user_id is None:
                error_text = 'User not found. Neither email address or username was provided.'
            return Response(
                error_text, status=status.HTTP_404_NOT_FOUND
            )

        action = serializer.validated_data.get('action')
        if action in ('add', 'modify'):

            editor_privilege = serializer.validated_data.get('editor')
            staff_instance, created = IssuerStaff.objects.get_or_create(
                user=user_to_modify,
                issuer=current_issuer,
                defaults={
                    'role': IssuerStaff.ROLE_EDITOR if editor_privilege else IssuerStaff.ROLE_STAFF
                }
            )

            if created is False and staff_instance.editor != editor_privilege:
                staff_instance.editor = editor_privilege
                staff_instance.save(update_fields=('editor',))

        elif action == 'remove':
            IssuerStaff.objects.filter(user=user_to_modify, issuer=current_issuer).delete()
            return Response(
                "User %s has been removed from %s staff." % (user_to_modify.username, current_issuer.name),
                status=status.HTTP_200_OK)

        # update cached issuers and badgeclasses for user
        user_to_modify.save()

        return Response(IssuerStaffSerializerV1(staff_instance).data)


class FindBadgeClassDetail(AbstractIssuerAPIEndpoint):
    """
    GET a specific BadgeClass by searching by identifier
    """
    permission_classes = (AuthenticatedWithVerifiedEmail,)

    def get(self, request):
        """
        GET a specific BadgeClass by searching by identifier
        ---
        serializer: BadgeClassSerializer
        parameters:
            - name: identifier
              required: true
              type: string
              paramType: form
              description: The identifier of the badge possible values: JSONld identifier, BadgeClass.id, or BadgeClass.slug
        """
        identifier = request.query_params.get('identifier')
        badge = get_badgeclass_by_identifier(identifier)
        if badge is None:
            raise NotFound("No BadgeClass found by identifier: {}".format(identifier))

        serializer = BadgeClassSerializerV1(badge)
        return Response(serializer.data)

