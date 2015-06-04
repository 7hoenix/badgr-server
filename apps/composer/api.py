from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework import authentication, permissions, status, serializers
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from mainsite.permissions import IsOwner
from credential_store.models import StoredBadgeInstance

from .serializers import (EarnerBadgeSerializer,
                          EarnerBadgeReferenceSerializer,
                          CollectionSerializer)
from .models import Collection, StoredBadgeInstanceCollection


class EarnerBadgeList(APIView):
    """
    Retrieve a list of user's earned badges or post a new badge.
    """
    queryset = StoredBadgeInstance.objects.all()
    permission_classes = (permissions.IsAuthenticated, IsOwner,)

    def get(self, request):
        """
        GET a list of all the logged-in user's earned badges
        ---
        serializer: EarnerBadgeSerializer
        """
        user_badges = self.queryset.filter(recipient_user=request.user)
        serializer = EarnerBadgeSerializer(
            user_badges, many=True, context={
                'request': request,
                'format': request.query_params.get('json_format', 'v1')
            }
        )

        return Response(serializer.data)

    def post(self, request):
        """
        POST badge information to add a badge to the logged-in user's account.
        Badgealong with either a badge image file, hosted
        badge assertion URL, or badge assertion content itself.
        ---
        serializer: EarnerBadgeSerializer
        parameters:
            - name: image
              description: A baked badge image file
              required: false
              type: file
              paramType: form
            - name: assertion
              description: The signed or hosted assertion content, either as a JSON string or base64-encoded JWT
              required: false
              type: string
              paramType: form
            - name: url
              description: The URL of a hosted assertion
              required: false
              type: string
              paramType: form
        """
        serializer = EarnerBadgeSerializer(data=request.data, context={'request': request})

        serializer.is_valid(raise_exception=True)
        serializer.save()

        # if serializer.instance.version is None:
        #     return Response()

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class EarnerBadgeDetail(APIView):
    queryset = StoredBadgeInstance.objects.all()
    permission_classes = (permissions.IsAuthenticated,)
    """
    View or delete a stored badge earned by a recipient.
    """
    def get(self, request, badge_id):
        """
        GET details on one badge
        ---
        serializer: EarnerBadgeSerializer
        parameters:
            - name: badge_id
              description: the unique id of the earner's badge to view
              required: true
              type: integer
              paramType: path
        """
        try:
            user_badge = self.queryset.get(
                recipient_user=request.user, id=badge_id
            )
        except StoredBadgeInstance.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = EarnerBadgeSerializer(
            user_badge, context={
                'request': request,
                'format': request.query_params.get('json_format', 'v1')
            }
        )

        return Response(serializer.data)

    def delete(self, request, badge_id):
        """
        DELETE one stored badge from the logged-in earner's collection
        ---
        parameters:
            - name: badge_id
              description: the unique id of the earner's badge to delete
              required: true
              type: integer
              paramType: path
        """
        try:
            self.queryset.get(
                recipient_user=request.user, id=badge_id
            ).delete()
        except StoredBadgeInstance.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        return Response(status=status.HTTP_204_NO_CONTENT)


class EarnerCollectionList(APIView):
    """
    Retrieve a list of Collections or post to create a new collection
    """
    queryset = Collection.objects.all()
    permission_classes = (permissions.IsAuthenticated, IsOwner,)

    def get(self, request):
        """
        GET a list of the logged-in user's Collections.
        ---
        serializer: CollectionSerializer
        """
        user_collections = self.queryset.filter(recipient=request.user)

        serializer = CollectionSerializer(
            user_collections, many=True, context={'request': request}
        )

        return Response(serializer.data)

    def post(self, request):
        """
        POST a new collection to the logged-in user's account.
        ---
        serializer: CollectionSerializer
        """
        serializer = CollectionSerializer(
            data=request.data, context={'request': request}
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class EarnerCollectionDetail(APIView):
    """
    View details of one Collection, update or delete it
    """
    queryset = Collection.objects.all()
    permission_classes = (permissions.IsAuthenticated, IsOwner,)

    def get(self, request, slug):
        """
        GET a single collection details, by slug
        """
        try:
            user_collection = self.queryset.get(
                recipient=request.user,
                slug=slug
            )
        except (Collection.MultipleObjectsReturned,
                Collection.DoesNotExist):
            return Response(status=status.HTTP_404_NOT_FOUND)

        else:
            serializer = CollectionSerializer(user_collection)
            return Response(serializer.data)

    def put(self, request, slug):
        """
        Update the description of a badge collection.
        ---
        serializer: CollectionSerializer
        parameters:
            - name: slug
              description: The collection's slug identifier
              required: true
              type: string
              paramType: path
            - name: description
              description: A description of the collection.
              required: false
              type: string
              paramType: form
        """
        description = request.data.get('description')
        try:
            description = str(description)
        except TypeError:
            return serializers.ValidationError(
                "Server could not understand description"
            )

        try:
            collection = self.queryset.get(
                recipient=request.user,
                slug=slug
            )
        except Collection.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if description:
            collection.description = description

        collection.save()

        serializer = CollectionSerializer(collection)
        return Response(serializer.data)

    def delete(self, request, slug):
        """
        Delete a collection
        ---
        parameters:
            - name: slug
              description: "The collection's slug identifier"
              type: string
              paramType: path
        """
        try:
            user_collection = self.queryset.get(
                recipient=request.user,
                slug=slug
            )
        except (Collection.MultipleObjectsReturned,
                Collection.DoesNotExist):
            return Response(status=status.HTTP_404_NOT_FOUND)

        else:
            user_collection.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)


class EarnerCollectionBadgesList(APIView):
    """
    POST to add badges to collection, PUT to update collection to a
    new list of ids.
    """
    queryset = StoredBadgeInstanceCollection.objects.all()
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, slug):
        """
        GET the badges in a single Collection
        """
        collection_badges = self.queryset.filter(
            collection__slug=slug, instance__recipient_user=request.user
        )

        serializer = EarnerBadgeReferenceSerializer(
            collection_badges, many=True
        )
        return Response(serializer.data)

    def post(self, request, slug):
        """
        POST new badge(s) to add them to a existing Collection.
        Returns resulting complete list of collection contents.
        """
        try:
            collection = Collection.objects.get(
                recipient=request.user, slug=slug
            )
        except (Collection.MultipleObjectsReturned,
                Collection.DoesNotExist):
            return Response(
                "Badge collection %s not found." % slug,
                status=status.HTTP_404_NOT_FOUND
            )

        add_many = isinstance(request.data, list)
        serializer = EarnerBadgeReferenceSerializer(
            data=request.data, many=add_many,
            context={'collection': collection, 'request': request}
        )
        serializer.is_valid(raise_exception=True)

        new_records = serializer.save()

        if new_records == []:
            return Response(
                "No new records could be added to collection. " +
                "Check for missing/unknown badge references, unauthorized " +
                "access, or badges already existing in collection.",
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def put(self, request, slug):
        """
        Update the list of badges included in a collection among
        those added to the logged-in user's badges. Cannot be used to
        change the description of a badge in the collection, but can
        be used to add descriptions to new badges to be added from the
        user's existing badges. Cannot be used to add new badges to the
        user's account at this time.
        ---
        serializer: EarnerBadgeReferenceSerializer
        parameters:
            - name: slug
              description: The collection's slug identifier
              required: true
              type: string
              paramType: path
            - name: badges
              description: A JSON serialization of all the badges to be included in this collection, replacing the list that currently exists.
              required: false
              paramType: form
        """
        badges = request.data.get('badges')

        try:
            collection = Collection.objects.get(
                recipient=request.user,
                slug=slug
            )
        except Collection.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if badges:
            serializer = EarnerBadgeReferenceSerializer(
                data=badges, many=isinstance(badges, list),
                context={'collection': collection, 'request': request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()

            badge_ids = [
                item.get('id') for item in badges
            ]

            StoredBadgeInstanceCollection.objects.filter(
                collection=collection
            ).exclude(instance__id__in=badge_ids).delete()

        serializer = EarnerBadgeReferenceSerializer(
            collection.storedbadgeinstancecollection_set.all(), many=True
        )
        return Response(serializer.data)


class EarnerCollectionBadgeDetail(APIView):
    """
    Update details on a single item in the collection or remove it from
    the collection
    """
    queryset = StoredBadgeInstanceCollection.objects.all()
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, collection_slug, badge_id):
        try:
            item = self.queryset.get(
                instance__recipient_user=request.user,
                collection__slug=collection_slug,
                instance__id=int(badge_id)
            )
        except StoredBadgeInstanceCollection.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = EarnerBadgeReferenceSerializer(item)
        return Response(serializer.data)

    def put(self, request, collection_slug, badge_id):
        """
        Update the description of a badge in a collection.
        ---
        parameters:
            - name: description
              description: Earner's annotation about a badge particular to this collection's audience.
              required: true
              type: string
              paramType: form
            - name: collection_slug
              description: The collection's slug identifier
              required: true
              type: string
              paramType: path
            - name: badge_id
              description: The stored badge's integer identifier
              required: true
              type: integer
              paramType: path
        """
        description = request.data.get('description', '')

        try:
            description = str(description)
        except TypeError:
            return serializers.ValidationError(
                "Server could not understand description"
            )

        try:
            item = self.queryset.get(
                instance__recipient_user=request.user,
                collection__slug=collection_slug,
                instance__id=int(badge_id)
            )
        except StoredBadgeInstanceCollection.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        item.description = description
        item.save()

        serializer = EarnerBadgeReferenceSerializer(item)
        return Response(serializer.data)

    def delete(self, request, collection_slug, badge_id):
        """
        Remove a badge from a collection (does not delete it
        from the earner's account)
        ---
        parameters:
            - name: collection_slug
              description: The collection's slug identifier
              required: true
              type: string
              paramType: path
            - name: badge_id
              description: The stored badge's integer identifier
              required: true
              type: integer
              paramType: path
        """
        try:
            self.queryset.get(
                instance__recipient_user=request.user,
                collection__slug=collection_slug,
                instance__id=int(badge_id)
            ).delete()
        except StoredBadgeInstanceCollection.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        return Response(status=status.HTTP_204_NO_CONTENT)
