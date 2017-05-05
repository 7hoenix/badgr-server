import base64
import json
import os
import os.path
from django.apps import apps
import png
import shutil
import urllib

from django.core import mail
from django.core.cache import cache
from django.core.files.images import get_image_dimensions
from django.core.urlresolvers import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import modify_settings, override_settings

from openbadges_bakery import unbake
from rest_framework.test import APIRequestFactory, APITestCase, force_authenticate

from badgeuser.models import BadgeUser, CachedEmailAddress
from issuer.api import IssuerList
from issuer.models import Issuer, BadgeClass, BadgeInstance, IssuerStaff
from issuer.serializers_v1 import BadgeInstanceSerializer
from mainsite import TOP_DIR

from mainsite.utils import OriginSetting
from mainsite.tests import CachingTestCase
from mainsite.models import BadgrApp

factory = APIRequestFactory()

example_issuer_props = {
    'name': 'Awesome Issuer',
    'description': 'An issuer of awe-inspiring credentials',
    'url': 'http://example.com',
    'email': 'contact@example.org'
}


class IssuerTestBase(APITestCase, CachingTestCase):
    def setUp(self):
        self.test_user, _ = BadgeUser.objects.get_or_create(email='test@example.com')
        self.test_user.user_permissions.add(Permission.objects.get(codename="add_issuer"))
        CachedEmailAddress.objects.get_or_create(user=self.test_user, email='test@example.com', verified=True, primary=True)

        self.test_user_2, _ = BadgeUser.objects.get_or_create(email='test2@example.com')
        CachedEmailAddress.objects.get_or_create(user=self.test_user_2, email='test2@example.com', verified=True, primary=True)

        self.test_user_3, _ = BadgeUser.objects.get_or_create(email='test3@example.com')
        CachedEmailAddress.objects.get_or_create(user=self.test_user_3, email='test3@example.com', verified=True, primary=True)
        
        self.badgr_app, _ = BadgrApp.objects.get_or_create(
            email_confirmation_redirect="http://localhost:3001/login/",
            # updated_by=[ "root" ],
            created_at="2016-02-10T17:25:58Z",
            is_active=True,
            updated_at="2016-02-10T17:25:58Z",
            # created_by=["root"],
            cors="localhost:3001",
            forgot_password_redirect="http://localhost:3001/change-password/"
        )

        self.issuer_1, _ = Issuer.objects.get_or_create(
            name="Test Issuer",
            created_at="2015-04-08T15:08:58Z",
            created_by=self.test_user,
            old_json="{\"description\":\"Issuer of Experimental Credentials\",\"url\":\"http://example.org\",\"image\":\"http://localhost:8000/public/issuers/test-issuer/image\",\"id\":\"http://localhost:8000/public/issuers/test-issuer\",\"@context\":\"https://w3id.org/openbadges/v1\",\"type\":\"Issuer\",\"email\":\"exampleIssuer@example.org\",\"name\":\"Test Issuer\"}",
            image="uploads/issuers/guinea_pig_testing_badge.png",
            slug="test-issuer"
        )

        IssuerStaff.objects.get_or_create(
            issuer=self.issuer_1,
            user=self.test_user,
            role=IssuerStaff.ROLE_OWNER
        )

        self.issuer_2, _ = Issuer.objects.get_or_create(
            name="Test Issuer 2",
            created_at="2015-04-08T15:18:16Z",
            created_by=self.test_user,
            old_json="{\"description\":\"Issuer of Experimental Credentials\",\"url\":\"http://example.org\",\"image\":\"http://localhost:8000/public/issuers/test-issuer/image\",\"id\":\"http://localhost:8000/public/issuers/testing-badge\",\"@context\":\"https://w3id.org/openbadges/v1\",\"type\":\"Issuer\",\"email\":\"exampleIssuer@example.org\",\"name\":\"Test Issuer\"}",
            image="uploads/issuers/guinea_pig_testing_badge_dlQWRUl.png",
            slug="test-issuer-2"
        )

        IssuerStaff.objects.get_or_create(
            issuer=self.issuer_2,
            user=self.test_user,
            role=IssuerStaff.ROLE_OWNER
        )

        self.issuer_3, _ = Issuer.objects.get_or_create(
            name="Edited Test Issuer",
            created_at="2015-04-08T15:18:16Z",
            created_by=self.test_user,
            old_json="{\"description\":\"Edited Test Issuer\",\"url\":\"http://example.org\",\"image\":\"http://localhost:8000/public/issuers/test-issuer/image\",\"id\":\"http://localhost:8000/public/issuers/testing-badge\",\"@context\":\"https://w3id.org/openbadges/v1\",\"type\":\"Issuer\",\"email\":\"exampleIssuer@example.org\",\"name\":\"Test Issuer\"}",
            image="uploads/issuers/guinea_pig_testing_badge_dlQWRUl.png",
            slug="edited-test-issuer"
        )

        IssuerStaff.objects.get_or_create(
            issuer=self.issuer_3,
            user=self.test_user,
            role=IssuerStaff.ROLE_OWNER
        )

        IssuerStaff.objects.get_or_create(
            issuer=self.issuer_3,
            user=self.test_user_2,
            role=IssuerStaff.ROLE_EDITOR
        )

        self.badgeclass_1, _ = BadgeClass.objects.get_or_create(
            name="Badge of Testing",
            created_at="2015-04-08T15:20:25Z",
            created_by=self.test_user,
            old_json="{\"description\":\"An experimental badge only awarded to brave people and non-existent test entities.\",\"image\":\"http://localhost:8000/public/badges/badge-of-testing/image\",\"criteria\":\"http://localhost:8000/public/badges/badge-of-awesome/criteria\",\"@context\":\"https://w3id.org/openbadges/v1\",\"issuer\":\"http://localhost:8000/public/issuers/test-issuer\",\"type\":\"BadgeClass\",\"id\":\"http://localhost:8000/public/badges/badge-of-testing\",\"name\":\"Badge of Awesome\"}",
            image="uploads/badges/guinea_pig_testing_badge.png",
            criteria_text="Be cool, dawg.",
            slug="badge-of-testing",
            issuer=self.issuer_2
        )

        self.badgeclass_2, _ = BadgeClass.objects.get_or_create(
            name="Second Badge of Testing",
            created_at="2015-04-08T15:20:25Z",
            created_by=self.test_user,
            old_json="{\"description\":\"An experimental badge only awarded to brave people and non-existent test entities.\",\"image\":\"http://localhost:8000/public/badges/badge-of-testing/image\",\"criteria\":\"http://localhost:8000/public/badges/badge-of-awesome/criteria\",\"@context\":\"https://w3id.org/openbadges/v1\",\"issuer\":\"http://localhost:8000/public/issuers/test-issuer\",\"type\":\"BadgeClass\",\"id\":\"http://localhost:8000/public/badges/badge-of-testing\",\"name\":\"Badge of Awesome\"}",
            image="uploads/badges/guinea_pig_testing_badge.png",
            criteria_text="Be cool, dawg.",
            slug="second-badge-of-testing",
            issuer=self.issuer_2
        )

        self.badgeclass_3, _ = BadgeClass.objects.get_or_create(
            name="Badge of Edited Testing",
            created_at="2015-04-08T15:20:25Z",
            created_by=self.test_user,
            old_json="{\"description\":\"An experimental badge only awarded to brave people and non-existent test entities.\",\"image\":\"http://localhost:8000/public/badges/badge-of-edited-testing/image\",\"criteria\":\"http://localhost:8000/public/badges/badge-of-edited-testing/criteria\",\"@context\":\"https://w3id.org/openbadges/v1\",\"issuer\":\"http://localhost:8000/public/issuers/edited-test-issuer\",\"type\":\"BadgeClass\",\"id\":\"http://localhost:8000/public/badges/badge-of-edited-testing\",\"name\":\"Badge of Edited Testing\"}",
            image="uploads/badges/guinea_pig_testing_badge.png",
            criteria_text="Be cool, dawg.",
            slug="badge-of-edited-testing",
            issuer=self.issuer_3
        )

        self.badgeclass_4, _ = BadgeClass.objects.get_or_create(
            name="Badge of Never Issued",
            created_at="2015-04-08T15:20:25Z",
            created_by=self.test_user,
            old_json="{\"description\":\"An experimental badge that will never have any instances.\",\"image\":\"http://localhost:8000/public/badges/badge-of-edited-testing/image\",\"criteria\":\"http://localhost:8000/public/badges/badge-of-never-issued/criteria\",\"@context\":\"https://w3id.org/openbadges/v1\",\"issuer\":\"http://localhost:8000/public/issuers/test-issuer\",\"type\":\"BadgeClass\",\"id\":\"http://localhost:8000/public/badges/badge-of-never-issued\",\"name\":\"Badge of Awesome\"}",
            image="uploads/badges/guinea_pig_testing_badge.png",
            criteria_text="Be cool, dawg.",
            slug="badge-of-never-issued",
            issuer=self.issuer_3
        )

        self.badgeclass_5, _ = BadgeClass.objects.get_or_create(
            name="Badge of SVG Testing",
            created_at="2015-04-08T15:20:25Z",
            created_by=self.test_user,
            old_json="{\"description\":\"An experimental badge only awarded to brave people and non-existent test entities.\",\"image\":\"http://localhost:8000/public/badges/badge-of-svg-testing/image\",\"criteria\":\"http://localhost:8000/public/badges/badge-of-svg-testing/criteria\",\"@context\":\"https://w3id.org/openbadges/v1\",\"issuer\":\"http://localhost:8000/public/issuers/test-issuer\",\"type\":\"BadgeClass\",\"id\":\"http://localhost:8000/public/badges/badge-of-svg-testing\",\"name\":\"Badge of SVG Testing\"}",
            image="uploads/badges/test_badgeclass.svg",
            criteria_text="Be cool, dawg.",
            slug="badge-of-svg-testing",
            issuer=self.issuer_2
        )

        self.badgeinstance_1, _ = BadgeInstance.objects.get_or_create(
            revocation_reason=None,
            revoked=False,
            created_at="2015-04-08T15:59:03Z",
            created_by=self.test_user,
            slug="92219015-18a6-4538-8b6d-2b228e47b8aa",
            old_json="{\"issuedOn\":\"2015-04-08T08:59:03.679218\",\"verify\":{\"url\":\"http://localhost:8000/public/assertions/92219015-18a6-4538-8b6d-2b228e47b8aa\",\"type\":\"hosted\"},\"image\":\"http://localhost:8000/public/assertions/92219015-18a6-4538-8b6d-2b228e47b8aa/image\",\"recipient\":{\"type\":\"email\",\"salt\":\"9944f83b-c1df-420d-b2d9-5f2d8968ca1c\",\"hashed\":true,\"identity\":\"sha256$a44b0fc1b8fc717bd6a5222c0f5573163f8647a9cada578b821904012257ea2d\"},\"type\":\"Assertion\",\"@context\":\"https://w3id.org/openbadges/v1\",\"badge\":\"http://localhost:8000/public/badges/badge-of-awesome\",\"id\":\"http://localhost:8000/public/assertions/92219015-18a6-4538-8b6d-2b228e47b8aa\"}",
            badgeclass=self.badgeclass_1,
            image="issued/badges/49213a69dc3213270e95c2ac3c1fbd01.png",
            recipient_identifier="test@example.com",
            issuer=self.issuer_2
        )

        self.badgeinstance_1, _ = BadgeInstance.objects.get_or_create(
            revocation_reason=None,
            revoked=False,
            created_at="2015-04-08T16:59:03Z",
            created_by=self.test_user,
            slug="92219015-18a6-4538-8b6d-2b228e47b8ab",
            old_json="{\"issuedOn\":\"2015-04-08T09:59:03.679218\",\"verify\":{\"url\":\"http://localhost:8000/public/assertions/92219015-18a6-4538-8b6d-2b228e47b8ab\",\"type\":\"hosted\"},\"image\":\"http://localhost:8000/public/assertions/92219015-18a6-4538-8b6d-2b228e47b8ab/image\",\"recipient\":{\"type\":\"email\",\"salt\":\"9944f83b-c1df-420d-b2d9-5f2d8968ca1c\",\"hashed\":true,\"identity\":\"sha256$f90bfa9a05bad084790a0276d3d3d58fe925378f92b8a94dfe72e6b3c9d53cdf\"},\"type\":\"Assertion\",\"@context\":\"https://w3id.org/openbadges/v1\",\"badge\":\"http://localhost:8000/public/badges/badge-of-awesome\",\"id\":\"http://localhost:8000/public/assertions/92219015-18a6-4538-8b6d-2b228e47b8aa\"}",
            badgeclass=self.badgeclass_1,
            image="issued/badges/49213a69dc3213270e95c2ac3c1fbd01.png",
            recipient_identifier="test2@example.com",
            issuer=self.issuer_2
        )

@override_settings(
    CELERY_ALWAYS_EAGER=True,
    SESSION_ENGINE='django.contrib.sessions.backends.cache',
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
            'LOCATION': os.path.join(TOP_DIR, 'test.cache'),
        }
    }
)
class IssuerTests(IssuerTestBase):
    def test_create_issuer_unauthenticated(self):
        view = IssuerList.as_view()

        request = factory.post(
            '/v1/issuer/issuers',
            json.dumps(example_issuer_props),
            content_type='application/json'
        )

        response = view(request)
        self.assertEqual(response.status_code, 401)

    def test_create_issuer_authenticated(self):
        self.client.force_authenticate(user=self.test_user)
        response = self.client.post('/v1/issuer/issuers', example_issuer_props)

        self.assertEqual(response.status_code, 201)

        # assert that name, description, url, etc are set properly in response badge object
        badge_object = response.data.get('json')
        self.assertEqual(badge_object['url'], example_issuer_props['url'])
        self.assertEqual(badge_object['name'], example_issuer_props['name'])
        self.assertEqual(badge_object['description'], example_issuer_props['description'])
        self.assertEqual(badge_object['email'], example_issuer_props['email'])
        self.assertIsNotNone(badge_object.get('id'))
        self.assertIsNotNone(badge_object.get('@context'))

        # assert that the issuer was published to and fetched from the cache
        with self.assertNumQueries(0):
            slug = response.data.get('slug')
            response = self.client.get('/v1/issuer/issuers/{}'.format(slug))
            self.assertEqual(response.status_code, 200)

    def test_create_issuer_authenticated_unconfirmed_email(self):
        first_user_data = user_data = {
            'first_name': 'NEW Test',
            'last_name': 'User',
            'email': 'unclaimed1@example.com',
            'password': '123456'
        }
        response = self.client.post('/v1/user/profile', user_data)

        first_user = get_user_model().objects.get(first_name='NEW Test')

        self.client.force_authenticate(user=first_user)
        response = self.client.post('/v1/issuer/issuers', example_issuer_props)

        self.assertEqual(response.status_code, 403)

    def test_create_issuer_image_500x300_resizes_to_400x400(self):
        view = IssuerList.as_view()

        with open(os.path.join(os.path.dirname(__file__), 'testfiles',
                               '500x300.png'), 'r') as badge_image:
                issuer_fields_with_image = {
                    'name': 'Awesome Issuer',
                    'description': 'An issuer of awe-inspiring credentials',
                    'url': 'http://example.com',
                    'email': 'contact@example.org',
                    'image': badge_image,
                }

                request = factory.post('/v1/issuer/issuers',
                                       issuer_fields_with_image,
                                       format='multipart')

                force_authenticate(request,
                                   user=self.test_user)
                response = view(request)
                self.assertEqual(response.status_code, 201)

                issuer_object = response.data.get('json')
                entity_id = issuer_object['id'].split('/')[-1]
                new_issuer = Issuer.objects.get(entity_id=entity_id)

                image_width, image_height = \
                    get_image_dimensions(new_issuer.image.file)
                self.assertEqual(image_width, 400)
                self.assertEqual(image_height, 400)

    def test_create_issuer_image_450x450_resizes_to_400x400(self):
        view = IssuerList.as_view()

        with open(
            os.path.join(os.path.dirname(__file__), 'testfiles', '450x450.png'),
            'r') as badge_image:

                issuer_fields_with_image = {
                    'name': 'Awesome Issuer',
                    'description': 'An issuer of awe-inspiring credentials',
                    'url': 'http://example.com',
                    'email': 'contact@example.org',
                    'image': badge_image,
                }

                request = factory.post('/v1/issuer/issuers',
                                       issuer_fields_with_image,
                                       format='multipart')

                force_authenticate(request,
                                   user=self.test_user)
                response = view(request)
                self.assertEqual(response.status_code, 201)

                issuer_object = response.data.get('json')
                entity_id = issuer_object['id'].split('/')[-1]
                new_issuer = Issuer.objects.get(entity_id=entity_id)

                image_width, image_height = \
                    get_image_dimensions(new_issuer.image.file)
                self.assertEqual(image_width, 400)
                self.assertEqual(image_height, 400)

    def test_create_issuer_image_300x300_stays_300x300(self):
        view = IssuerList.as_view()

        with open(
            os.path.join(os.path.dirname(__file__), 'testfiles', '300x300.png'),
            'r') as badge_image:

                issuer_fields_with_image = {
                    'name': 'Awesome Issuer',
                    'description': 'An issuer of awe-inspiring credentials',
                    'url': 'http://example.com',
                    'email': 'contact@example.org',
                    'image': badge_image,
                }

                request = factory.post('/v1/issuer/issuers',
                                       issuer_fields_with_image,
                                       format='multipart')

                force_authenticate(request, user=self.test_user)
                response = view(request)
                self.assertEqual(response.status_code, 201)

                issuer_object = response.data.get('json')
                entity_id = issuer_object['id'].split('/')[-1]
                new_issuer = Issuer.objects.get(entity_id=entity_id)

                image_width, image_height = \
                    get_image_dimensions(new_issuer.image.file)
                self.assertEqual(image_width, 300)
                self.assertEqual(image_height, 300)

    def test_update_issuer(self):
        self.client.force_authenticate(user=self.test_user)

        original_issuer_props = {
            'name': 'Test Issuer Name',
            'description': 'Test issuer description',
            'url': 'http://example.com/1',
            'email': 'example1@example.org'
        }

        response = self.client.post('/v1/issuer/issuers', original_issuer_props)
        response_slug = response.data.get('slug')

        updated_issuer_props = {
            'name': 'Test Issuer Name 2',
            'description': 'Test issuer description 2',
            'url': 'http://example.com/2',
            'email': 'example2@example.org'
        }

        response = self.client.put('/v1/issuer/issuers/{}'.format(response_slug), updated_issuer_props)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.data['url'], updated_issuer_props['url'])
        self.assertEqual(response.data['name'], updated_issuer_props['name'])
        self.assertEqual(response.data['description'], updated_issuer_props['description'])
        self.assertEqual(response.data['email'], updated_issuer_props['email'])

    def test_private_issuer_detail_get(self):
        # GET on single badge should work if user has privileges
        # Eventually, implement PUT for updates (if permitted)
        pass

    def test_get_empty_issuer_editors_set(self):
        self.client.force_authenticate(user=self.test_user)
        response = self.client.get('/v1/issuer/issuers/test-issuer/staff')

        self.assertEqual(response.status_code, 200)

    def test_add_user_to_issuer_editors_set(self):
        """ Authenticated user (pk=1) owns test-issuer. Add user (username=test3) as an editor. """
        self.client.force_authenticate(user=self.test_user)

        post_response = self.client.post(
            '/v1/issuer/issuers/test-issuer/staff',
            {'action': 'add', 'username': self.test_user_3.username, 'editor': True}
        )

        self.assertEqual(post_response.status_code, 200)
        self.assertEqual(len(post_response.data), 2)  # Assert that there is now one editor

    def test_add_user_to_issuer_editors_set_by_email(self):
        """ Authenticated user (pk=1) owns test-issuer. Add user (username=test3) as an editor. """
        self.client.force_authenticate(user=self.test_user)

        user_to_update = get_user_model().objects.get(email='test3@example.com')
        user_issuers = user_to_update.cached_issuers()

        post_response = self.client.post(
            '/v1/issuer/issuers/test-issuer/staff',
            {'action': 'add', 'email': 'test3@example.com', 'editor': True}
        )

        self.assertEqual(post_response.status_code, 200)
        self.assertEqual(len(post_response.data), 2)  # Assert that there is now one editor
        self.assertTrue(len(user_issuers) < len(user_to_update.cached_issuers()))

    def test_add_user_to_issuer_editors_set_too_many_methods(self):
        """ Authenticated user (pk=1) owns test-issuer. Add user (username=test3) as an editor. """
        self.client.force_authenticate(user=self.test_user)

        post_response = self.client.post(
            '/v1/issuer/issuers/test-issuer/staff',
            {'action': 'add', 'email': 'test3@example.com', 'username': 'test3', 'editor': True}
        )

        self.assertEqual(post_response.status_code, 400)

    def test_add_user_to_issuer_editors_set_missing_identifier(self):
        """ Authenticated user (pk=1) owns test-issuer. Add user (username=test3) as an editor. """
        self.client.force_authenticate(user=self.test_user)

        post_response = self.client.post(
            '/v1/issuer/issuers/test-issuer/staff',
            {'action': 'add', 'editor': True}
        )

        self.assertEqual(post_response.status_code, 404)
        self.assertEqual(post_response.data, 'User not found. Neither email address or username was provided.')


    def test_bad_action_issuer_editors_set(self):
        self.client.force_authenticate(user=self.test_user)
        post_response = self.client.post(
            '/v1/issuer/issuers/test-issuer/staff',
            {'action': 'DO THE HOKEY POKEY', 'username': 'test2', 'editor': True}
        )

        self.assertEqual(post_response.status_code, 400)

    def test_add_nonexistent_user_to_issuer_editors_set(self):
        self.client.force_authenticate(user=self.test_user)
        response = self.client.post(
            '/v1/issuer/issuers/test-issuer/staff',
            {'action': 'add', 'username': 'taylor_swift', 'editor': True}
        )

        self.assertContains(response, "User taylor_swift not found.", status_code=404)

    def test_add_user_to_nonexistent_issuer_editors_set(self):
        self.client.force_authenticate(user=self.test_user)
        response = self.client.post(
            '/v1/issuer/issuers/test-nonexistent-issuer/staff',
            {'action': 'add', 'username': 'test2', 'editor': True}
        )

        self.assertContains(response, "Issuer test-nonexistent-issuer not found", status_code=404)

    def test_add_remove_user_with_issuer_staff_set(self):
        test_issuer = Issuer.objects.get(slug='test-issuer')
        self.assertEqual(len(test_issuer.staff.all()), 1)

        self.client.force_authenticate(user=self.test_user)
        post_response = self.client.post(
            '/v1/issuer/issuers/test-issuer/staff',
            {'action': 'add', 'username': self.test_user_2.username}
        )

        self.assertEqual(post_response.status_code, 200)
        self.assertEqual(len(test_issuer.staff.all()), 2)

        second_response = self.client.post(
            '/v1/issuer/issuers/test-issuer/staff',
            {'action': 'remove', 'username': self.test_user_2.username}
        )

        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(len(test_issuer.staff.all()), 1)

    def test_delete_issuer_successfully(self):
        self.client.force_authenticate(user=self.test_user)
        test_issuer = Issuer(name='issuer who can be deleted', slug='issuer-deletable')
        test_issuer.save()
        IssuerStaff(issuer=test_issuer, user=self.test_user, role=IssuerStaff.ROLE_OWNER).save()

        response = self.client.delete('/v1/issuer/issuers/issuer-deletable', {})
        self.assertEqual(response.status_code, 200)

    def test_delete_issuer_with_unissued_badgeclass_successfully(self):
        self.client.force_authenticate(user=self.test_user)
        test_issuer = Issuer(name='issuer who can be deleted', slug="issuer-deletable")
        test_issuer.save()
        IssuerStaff(issuer=test_issuer, user=self.test_user, role=IssuerStaff.ROLE_OWNER).save()
        test_badgeclass = BadgeClass(name="Deletable Badge", issuer=test_issuer)

        test_badgeclass.save()

        response = self.client.delete('/v1/issuer/issuers/issuer-deletable', {})
        self.assertEqual(response.status_code, 200)

    def test_cant_delete_issuer_with_issued_badge(self):
        self.client.force_authenticate(user=self.test_user)
        response = self.client.delete('/v1/issuer/issuers/test-issuer-2', {})
        self.assertEqual(response.status_code, 400)

    def test_new_issuer_updates_cached_user_issuers(self):
        self.client.force_authenticate(user=self.test_user)
        badgelist = self.client.get('/v1/issuer/all-badges')

        example_issuer_props = {
            'name': 'Fresh Issuer',
            'description': "Fresh Issuer",
            'url': 'http://freshissuer.com',
            'email': 'prince@freshissuer.com',
        }

        response = self.client.post(
            '/v1/issuer/issuers',
            example_issuer_props
        )
        self.assertEqual(response.status_code, 201)

        with open(
            os.path.join(os.path.dirname(__file__), 'testfiles', 'guinea_pig_testing_badge.png'), 'r'
        ) as badge_image:

            example_badgeclass_props = {
                'name': 'Badge of Freshness',
                'description': "Fresh Badge",
                'image': badge_image,
                'criteria': 'http://wikipedia.org/Freshness',
            }

            response = self.client.post(
                '/v1/issuer/issuers/fresh-issuer/badges',
                example_badgeclass_props
            )
            self.assertEqual(response.status_code, 201)

        new_badgelist = self.client.get('/v1/issuer/all-badges')

        self.assertEqual(len(new_badgelist.data), len(badgelist.data) + 1)

@override_settings(
    CELERY_ALWAYS_EAGER=True,
    SESSION_ENGINE='django.contrib.sessions.backends.cache',
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
            'LOCATION': os.path.join(TOP_DIR, 'test.cache'),
        }
    }
)
class BadgeClassTests(IssuerTestBase):
    def test_create_badgeclass_for_issuer_authenticated(self):
        with open(
            os.path.join(os.path.dirname(__file__), 'testfiles', 'guinea_pig_testing_badge.png'), 'r'
        ) as badge_image:

            example_badgeclass_props = {
                'name': 'Badge of Awesome',
                'description': "An awesome badge only awarded to awesome people or non-existent test entities",
                'image': badge_image,
                'criteria': 'http://wikipedia.org/Awesome',
            }

            self.client.force_authenticate(user=self.test_user)
            response = self.client.post(
                '/v1/issuer/issuers/test-issuer/badges',
                example_badgeclass_props
            )
            self.assertEqual(response.status_code, 201)

            # assert that the BadgeClass was published to and fetched from the cache
            # we expect to generate one query where the object permissions are checked in BadgeClassDetail.get
            with self.assertNumQueries(1):
                slug = response.data.get('slug')
                response = self.client.get('/v1/issuer/issuers/test-issuer/badges/{}'.format(slug))
                self.assertEqual(response.status_code, 200)

    def test_create_badgeclass_with_svg(self):
        with open(
                os.path.join(TOP_DIR, 'apps', 'issuer', 'testfiles', 'test_badgeclass.svg'), 'r'
        ) as badge_image:

            example_badgeclass_props = {
                'name': 'Badge of Awesome',
                'description': "An awesome badge only awarded to awesome people or non-existent test entities",
                'image': badge_image,
                'criteria': 'http://wikipedia.org/Awesome',
            }

            self.client.force_authenticate(user=self.test_user)
            response = self.client.post(
                '/v1/issuer/issuers/test-issuer/badges',
                example_badgeclass_props
            )
            self.assertEqual(response.status_code, 201)

            # assert that the BadgeClass was published to and fetched from the cache
            # we expect to generate one query where the object permissions are checked in BadgeClassDetail.get
            with self.assertNumQueries(1):
                slug = response.data.get('slug')
                response = self.client.get('/v1/issuer/issuers/test-issuer/badges/{}'.format(slug))
                self.assertEqual(response.status_code, 200)

    def test_create_badgeclass_scrubs_svg(self):
        with open(
            os.path.join(TOP_DIR, 'apps', 'issuer', 'testfiles', 'hacked-svg-with-embedded-script-tags.svg'), 'r'
        ) as attack_badge_image:

            badgeclass_props = {
                'name': 'javascript SVG badge',
                'description': 'badge whose svg source attempts to execute code',
                'image': attack_badge_image,
                'criteria': 'http://svgs.should.not.be.user.input'
            }
            self.client.force_authenticate(user=self.test_user)
            response = self.client.post('/v1/issuer/issuers/test-issuer/badges', badgeclass_props)
            self.assertEqual(response.status_code, 201)

            # make sure code was stripped
            bc = BadgeClass.objects.get(slug=response.data.get('slug'))
            image_content = bc.image.file.readlines()
            self.assertNotIn('onload', image_content)
            self.assertNotIn('<script>', image_content)

    def test_create_criteriatext_badgeclass_for_issuer_authenticated(self):
        """
        Ensure that when criteria text is submitted instead of a URL, the criteria address
        embedded in the badge is to the view that will display that criteria text
        (rather than the text itself or something...)
        """
        with open(
            os.path.join(os.path.dirname(__file__), 'testfiles', 'guinea_pig_testing_badge.png'), 'r'
        ) as badge_image:

            badgeclass_props = {
                'name': 'Badge of Awesome',
                'description': "An awesome badge only awarded to awesome people or non-existent test entities",
                'image': badge_image,
                'criteria': 'The earner of this badge must be truly, truly awesome.',
            }

            self.client.force_authenticate(user=self.test_user)
            response = self.client.post(
                '/v1/issuer/issuers/test-issuer/badges',
                badgeclass_props
            )
            self.assertEqual(response.status_code, 201)
            self.assertRegexpMatches(response.data.get(
                'json', {}).get('criteria'),
                r'badge-of-awesome/criteria$'
            )

    def test_create_criteriatext_badgeclass_description_required(self):
        """
        Ensure that the API properly rejects badgeclass creation requests that do not include a description.
        """
        with open(
            os.path.join(os.path.dirname(__file__), 'testfiles', 'guinea_pig_testing_badge.png'), 'r'
        ) as badge_image:

            badgeclass_props = {
                'name': 'Badge of Awesome',
                'image': badge_image,
                'criteria': 'The earner of this badge must be truly, truly awesome.',
            }

            self.client.force_authenticate(user=self.test_user)
            response = self.client.post(
                '/v1/issuer/issuers/test-issuer/badges',
                badgeclass_props
            )
            self.assertEqual(response.status_code, 400)

    def test_create_badgeclass_for_issuer_unauthenticated(self):
        response = self.client.post('/v1/issuer/issuers/test-issuer/badges', {})
        self.assertEqual(response.status_code, 401)

    def test_badgeclass_list_authenticated(self):
        """
        Ensure that a logged-in user can get a list of their BadgeClasses
        """
        self.client.force_authenticate(user=self.test_user)
        response = self.client.get('/v1/issuer/issuers/test-issuer-2/badges')

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)  # Ensure we receive a list of badgeclasses
        self.assertEqual(len(response.data), 3)  # Ensure that we receive the 3 badgeclasses in fixture as expected

    def test_unauthenticated_cant_get_badgeclass_list(self):
        """
        Ensure that logged-out user can't GET the private API endpoint for badgeclass list
        """
        response = self.client.get('/v1/issuer/issuers/test-issuer-2/badges')
        self.assertEqual(response.status_code, 401)

    def test_delete_unissued_badgeclass(self):
        self.assertTrue(BadgeClass.objects.filter(slug='badge-of-never-issued').exists())
        self.client.force_authenticate(user=self.test_user)
        response = self.client.delete('/v1/issuer/issuers/test-issuer/badges/badge-of-never-issued')
        self.assertEqual(response.status_code, 200)

        self.assertFalse(BadgeClass.objects.filter(slug='badge-of-never-issued').exists())

    def test_delete_already_issued_badgeclass(self):
        """
        A user should not be able to delete a badge class if it has been test_delete_already_issued_badgeclass
        """
        self.client.force_authenticate(user=self.test_user)
        response = self.client.delete('/v1/issuer/issuers/test-issuer/badges/badge-of-testing')
        self.assertEqual(response.status_code, 400)

        self.assertTrue(BadgeClass.objects.filter(slug='badge-of-testing').exists())

    def test_create_badgeclass_with_underscore_slug(self):
        """
        Tests that a manually-defined slug that includes underscores does not
        trigger an error when defining a new BadgeClass
        """
        with open(
            os.path.join(os.path.dirname(__file__), 'testfiles', 'guinea_pig_testing_badge.png'), 'r'
        ) as badge_image:

            badgeclass_props = {
                'name': 'Badge of Slugs',
                'slug': 'badge_of_slugs_99',
                'description': "Recognizes slimy learners with a penchant for lettuce",
                'image': badge_image,
                'criteria': 'The earner of this badge must slither through a garden and return home before morning.',
            }

            self.client.force_authenticate(user=self.test_user)
            response = self.client.post(
                '/v1/issuer/issuers/test-issuer/badges',
                badgeclass_props
            )
            self.assertEqual(response.status_code, 201)
            self.assertRegexpMatches(response.data.get(
                'json', {}).get('criteria'),
                r'badge_of_slugs_99/criteria$'
            )

    def test_create_badgeclass_with_svg_image(self):
        with open(
            os.path.join(os.path.dirname(__file__), 'testfiles', 'test_badgeclass.svg'), 'r'
        ) as badge_image:

            example_badgeclass_props = {
                'name': 'Badge of Awesome',
                'description': "An awesome badge only awarded to awesome people or non-existent test entities",
                'image': badge_image,
                'criteria': 'http://wikipedia.org/Awesome',
            }

            self.client.force_authenticate(user=self.test_user)
            response = self.client.post(
                '/v1/issuer/issuers/test-issuer/badges',
                example_badgeclass_props
            )
            self.assertEqual(response.status_code, 201)

    def test_dont_create_badgeclass_with_invalid_markdown(self):
        with open(
                os.path.join(os.path.dirname(__file__), 'testfiles', 'guinea_pig_testing_badge.png'), 'r'
        ) as badge_image:

            badgeclass_props = {
                'name': 'Badge of Slugs',
                'slug': 'badge_of_slugs_99',
                'description': "Recognizes slimy learners with a penchant for lettuce",
                'image': badge_image,
            }

            self.client.force_authenticate(user=self.test_user)

            # should not create badge that has images in markdown
            badgeclass_props['criteria'] = 'This is invalid ![foo](image-url) markdown'
            response = self.client.post(
                '/v1/issuer/issuers/test-issuer/badges',
                badgeclass_props
            )
            self.assertEqual(response.status_code, 400)

    def test_create_badgeclass_with_valid_markdown(self):
        with open(
                os.path.join(os.path.dirname(__file__), 'testfiles', 'guinea_pig_testing_badge.png'), 'r'
        ) as badge_image:

            badgeclass_props = {
                'name': 'Badge of Slugs',
                'slug': 'badge_of_slugs_99',
                'description': "Recognizes slimy learners with a penchant for lettuce",
                'image': badge_image,
            }

            self.client.force_authenticate(user=self.test_user)

            # valid markdown should be saved but html tags stripped
            badgeclass_props['criteria'] = 'This is *valid* markdown <p>mixed with raw</p> <script>document.write("and abusive html")</script>'
            response = self.client.post(
                '/v1/issuer/issuers/test-issuer/badges',
                badgeclass_props
            )
            self.assertEqual(response.status_code, 201)
            self.assertIsNotNone(response.data)
            new_badgeclass = response.data
            self.assertEqual(new_badgeclass.get('criteria_text', None), 'This is *valid* markdown mixed with raw document.write("and abusive html")')

            # verify that public page renders markdown as html
            response = self.client.get('/public/badges/{}'.format(new_badgeclass.get('slug')), HTTP_ACCEPT='*/*')
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "<p>This is <em>valid</em> markdown")

    def test_new_badgeclass_updates_cached_issuer(self):
        number_of_badgeclasses = len(list(self.test_user.cached_badgeclasses()))

        with open(
            os.path.join(os.path.dirname(__file__), 'testfiles', 'guinea_pig_testing_badge.png'), 'r'
        ) as badge_image:

            example_badgeclass_props = {
                'name': 'Badge of Freshness',
                'description': "Fresh Badge",
                'image': badge_image,
                'criteria': 'http://wikipedia.org/Freshness',
            }

            self.client.force_authenticate(user=self.test_user)
            response = self.client.post(
                '/v1/issuer/issuers/test-issuer/badges',
                example_badgeclass_props
            )
            self.assertEqual(response.status_code, 201)

            self.assertEqual(len(list(self.test_user.cached_badgeclasses())), number_of_badgeclasses + 1)


    def test_new_badgeclass_updates_cached_user_badgeclasses(self):
        self.client.force_authenticate(user=self.test_user)
        badgelist = self.client.get('/v1/issuer/all-badges')

        with open(
            os.path.join(os.path.dirname(__file__), 'testfiles', 'guinea_pig_testing_badge.png'), 'r'
        ) as badge_image:

            example_badgeclass_props = {
                'name': 'Badge of Freshness',
                'description': "Fresh Badge",
                'image': badge_image,
                'criteria': 'http://wikipedia.org/Freshness',
            }

            response = self.client.post(
                '/v1/issuer/issuers/test-issuer/badges',
                example_badgeclass_props
            )
            self.assertEqual(response.status_code, 201)

        new_badgelist = self.client.get('/v1/issuer/all-badges')

        self.assertEqual(len(new_badgelist.data), len(badgelist.data) + 1)

    def _base64_data_uri_encode(self, file, mime):
        encoded = base64.b64encode(file.read())
        return "data:{};base64,{}".format(mime, encoded)

    def test_badgeclass_put_image_data_uri(self):
        self.client.force_authenticate(user=self.test_user)

        badgeclass_props = {
            'name': 'Badge of Awesome',
            'description': 'An awesome badge only awarded to awesome people or non-existent test entities',
            'criteria': 'http://wikipedia.org/Awesome',
        }

        with open(
            os.path.join(os.path.dirname(__file__), 'testfiles', '300x300.png'), 'r'
        ) as badge_image:
            post_response = self.client.post(
                '/v1/issuer/issuers/test-issuer/badges',
                dict(badgeclass_props, image=badge_image),
            )
            self.assertEqual(post_response.status_code, 201)
            slug = post_response.data.get('slug')

        with open(
            os.path.join(os.path.dirname(__file__), 'testfiles', '450x450.png'), 'r'
        ) as new_badge_image:
            put_response = self.client.put(
                '/v1/issuer/issuers/test-issuer/badges/{}'.format(slug),
                dict(badgeclass_props, image=self._base64_data_uri_encode(new_badge_image, 'image/png'))
            )
            self.assertEqual(put_response.status_code, 200)

            new_badgeclass = BadgeClass.objects.get(slug=slug)
            image_width, image_height = get_image_dimensions(new_badgeclass.image.file)

            # File should be changed to new 450x450 image
            self.assertEqual(image_width, 450)
            self.assertEqual(image_height, 450)

    def test_badgeclass_put_image_non_data_uri(self):
        self.client.force_authenticate(user=self.test_user)

        badgeclass_props = {
            'name': 'Badge of Awesome',
            'description': 'An awesome badge only awarded to awesome people or non-existent test entities',
            'criteria': 'http://wikipedia.org/Awesome',
        }

        with open(
            os.path.join(os.path.dirname(__file__), 'testfiles', '300x300.png'), 'r'
        ) as badge_image:
            post_response = self.client.post(
                '/v1/issuer/issuers/test-issuer/badges',
                dict(badgeclass_props, image=badge_image),
            )
            self.assertEqual(post_response.status_code, 201)
            slug = post_response.data.get('slug')

        put_response = self.client.put(
            '/v1/issuer/issuers/test-issuer/badges/{}'.format(slug),
            dict(badgeclass_props, image='http://example.com/example.png')
        )
        self.assertEqual(put_response.status_code, 200)

        new_badgeclass = BadgeClass.objects.get(slug=slug)
        image_width, image_height = get_image_dimensions(new_badgeclass.image.file)

        # File should be original 300x300 image
        self.assertEqual(image_width, 300)
        self.assertEqual(image_height, 300)

    def test_badgeclass_put_image_multipart(self):
        self.client.force_authenticate(user=self.test_user)

        badgeclass_props = {
            'name': 'Badge of Awesome',
            'description': 'An awesome badge only awarded to awesome people or non-existent test entities',
            'criteria': 'http://wikipedia.org/Awesome',
        }

        with open(
            os.path.join(os.path.dirname(__file__), 'testfiles', '300x300.png'), 'r'
        ) as badge_image:
            post_response = self.client.post(
                '/v1/issuer/issuers/test-issuer/badges',
                dict(badgeclass_props, image=badge_image),
            )
            self.assertEqual(post_response.status_code, 201)
            slug = post_response.data.get('slug')

        with open(
            os.path.join(os.path.dirname(__file__), 'testfiles', '450x450.png'), 'r'
        ) as new_badge_image:
            put_response = self.client.put(
                '/v1/issuer/issuers/test-issuer/badges/{}'.format(slug),
                dict(badgeclass_props, image=new_badge_image),
                format='multipart'
            )
            self.assertEqual(put_response.status_code, 200)

            new_badgeclass = BadgeClass.objects.get(slug=slug)
            image_width, image_height = get_image_dimensions(new_badgeclass.image.file)

            # File should be changed to new 450x450 image
            self.assertEqual(image_width, 450)
            self.assertEqual(image_height, 450)


    def test_badgeclass_post_get_put_roundtrip(self):
        with open(
            os.path.join(os.path.dirname(__file__), 'testfiles', 'guinea_pig_testing_badge.png'), 'r'
        ) as badge_image:

            example_badgeclass_props = {
                'name': 'Badge of Awesome',
                'description': "An awesome badge only awarded to awesome people or non-existent test entities",
                'image': badge_image,
                'criteria': 'http://wikipedia.org/Awesome',
            }

            self.client.force_authenticate(user=self.test_user)
            post_response = self.client.post(
                '/v1/issuer/issuers/test-issuer/badges',
                example_badgeclass_props,
                format='multipart'
            )
        self.assertEqual(post_response.status_code, 201)

        slug = post_response.data.get('slug')
        get_response = self.client.get('/v1/issuer/issuers/test-issuer/badges/{}'.format(slug))
        self.assertEqual(get_response.status_code, 200)

        put_response = self.client.put('/v1/issuer/issuers/test-issuer/badges/{}'.format(slug), get_response.data)
        self.assertEqual(put_response.status_code, 200)

        self.assertEqual(get_response.data, put_response.data)

@override_settings(
    CELERY_ALWAYS_EAGER=True,
    SESSION_ENGINE='django.contrib.sessions.backends.cache',
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
            'LOCATION': os.path.join(TOP_DIR, 'test.cache'),
        }
    }
)
class AssertionTests(IssuerTestBase):
    def ensure_image_exists(self, badge_object, image_filename='guinea_pig_testing_badge.png'):
        if not os.path.exists(badge_object.image.path):
            shutil.copy2(
                os.path.join(os.path.dirname(__file__), 'testfiles', image_filename),
                badge_object.image.path
            )

    def test_badge_instance_serializer_notification_validation(self):
        data = {
            "email": "test@example.com",
            "create_notification": False
        }

        serializer = BadgeInstanceSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        self.assertEqual(serializer.validated_data.get('create_notification'), data['create_notification'])

    def test_authenticated_owner_issue_badge(self):
        # load test image into media files if it doesn't exist
        self.ensure_image_exists(BadgeClass.objects.get(slug='badge-of-testing'))

        self.client.force_authenticate(user=self.test_user)
        assertion = {
            "email": "test@example.com",
            "create_notification": False
        }
        response = self.client.post('/v1/issuer/issuers/test-issuer-2/badges/badge-of-testing/assertions', assertion)

        self.assertEqual(response.status_code, 201)

        # Assert mail not sent if "create_notification" param included but set to false
        self.assertEqual(len(mail.outbox), 0)

        # assert that the BadgeInstance was published to and fetched from cache
        query_count = 1 if apps.is_installed('badgebook') else 0
        with self.assertNumQueries(query_count):
            slug = response.data.get('slug')
            response = self.client.get('/v1/issuer/issuers/test-issuer-2/badges/badge-of-testing/assertions/{}'.format(slug))
            self.assertEqual(response.status_code, 200)

    def test_issue_badge_with_ob1_evidence(self):
        self.ensure_image_exists(BadgeClass.objects.get(slug='badge-of-testing'))
        self.client.force_authenticate(user=self.test_user)

        evidence_url = "http://fake.evidence.url.test"
        assertion = {
            "email": "test@example.com",
            "create_notification": False,
            "evidence": evidence_url
        }
        response = self.client.post('/v1/issuer/issuers/test-issuer-2/badges/badge-of-testing/assertions', assertion)
        self.assertEqual(response.status_code, 201)

        slug = response.data.get('slug')
        response = self.client.get('/v1/issuer/issuers/test-issuer-2/badges/badge-of-testing/assertions/{}'.format(slug))
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.data.get('json'))
        self.assertEqual(response.data.get('json').get('evidence'), evidence_url)

        # ob2.0 evidence_items also present
        self.assertEqual(response.data.get('evidence_items'), [
            {
                'evidence_url': evidence_url,
                'narrative': None,
            }
        ])

    def test_issue_badge_with_ob2_multiple_evidence(self):
        self.ensure_image_exists(BadgeClass.objects.get(slug='badge-of-testing'))
        self.client.force_authenticate(user=self.test_user)

        evidence_items = [
            {
                'evidence_url': "http://fake.evidence.url.test",
            },
            {
                'evidence_url': "http://second.evidence.url.test",
                "narrative": "some description of how second evidence was collected"
            }
        ]
        assertion_args = {
            "email": "test@example.com",
            "create_notification": False,
            "evidence_items": evidence_items
        }
        response = self.client.post('/v1/issuer/issuers/test-issuer-2/badges/badge-of-testing/assertions', assertion_args, format='json')
        self.assertEqual(response.status_code, 201)

        slug = response.data.get('slug')
        response = self.client.get('/v1/issuer/issuers/test-issuer-2/badges/badge-of-testing/assertions/{}'.format(slug))
        self.assertEqual(response.status_code, 200)
        assertion = response.data

        fetched_evidence_items = assertion.get('evidence_items')
        self.assertEqual(len(fetched_evidence_items), len(evidence_items))
        for i in range(0,len(evidence_items)):
            self.assertEqual(fetched_evidence_items[i].get('url'), evidence_items[i].get('url'))
            self.assertEqual(fetched_evidence_items[i].get('narrative'), evidence_items[i].get('narrative'))

        # ob1.0 evidence url also present
        self.assertIsNotNone(assertion.get('json'))
        assertion_public_url = OriginSetting.HTTP+reverse('badgeinstance_json', kwargs={'slug': slug})
        self.assertEqual(assertion.get('json').get('evidence'), assertion_public_url)

    def test_resized_png_image_baked_properly(self):
        with open(
            os.path.join(os.path.dirname(__file__), 'testfiles', 'guinea_pig_testing_badge.png'), 'r'
        ) as badge_image:

            badgeclass_props = {
                'name': 'Badge of Awesome',
                'description': "An awesome badge only awarded to awesome people or non-existent test entities",
                'image': badge_image,
                'criteria': 'The earner of this badge must be truly, truly awesome.',
            }

            self.client.force_authenticate(user=self.test_user)
            response_bc = self.client.post(
                '/v1/issuer/issuers/test-issuer/badges',
                badgeclass_props
            )

        assertion = {
            "email": "test@example.com"
        }
        self.client.force_authenticate(user=current_user)
        response = self.client.post('/v1/issuer/issuers/test-issuer/badges/badge-of-awesome/assertions', assertion)

        instance = BadgeInstance.objects.get(slug=response.data.get('slug'))

        instance.image.open()
        self.assertIsNotNone(unbake(instance.image))
        instance.image.close()
        instance.image.open()

        reader = png.Reader(file=instance.image)
        for chunk in reader.chunks():
            if chunk[0] == 'IDAT':
                image_data_present = True
            elif chunk[0] == 'iTXt' and chunk[1].startswith('openbadges\x00\x00\x00\x00\x00'):
                badge_data_present = True

        self.assertTrue(image_data_present and badge_data_present)

        # Assert notification not sent if "create_notification" param not included
        self.assertEqual(len(mail.outbox), 0)

    def test_authenticated_editor_can_issue_badge(self):
        # load test image into media files if it doesn't exist
        self.ensure_image_exists(BadgeClass.objects.get(slug='badge-of-testing'))

        # This issuer has user 2 among its editors.
        the_editor = get_user_model().objects.get(pk=2)
        self.client.force_authenticate(user=the_editor)
        response = self.client.post(
            '/v1/issuer/issuers/edited-test-issuer/badges/badge-of-edited-testing/assertions',
            {"email": "test@example.com", "create_notification": True}
        )

        self.assertEqual(response.status_code, 201)

        # Assert that mail is sent if "create_notification" is included and set to True.
        self.assertEqual(len(mail.outbox), 1)

    def test_authenticated_nonowner_user_cant_issue(self):
        self.client.force_authenticate(user=self.test_user_2)
        assertion = {
            "email": "test2@example.com"
        }
        response = self.client.post('/v1/issuer/issuers/test-issuer/badges/badge-of-testing/assertions', assertion)

        self.assertEqual(response.status_code, 404)

    def test_unauthenticated_user_cant_issue(self):
        assertion = {"email": "test@example.com"}
        response = self.client.post('/v1/issuer/issuers/test-issuer/badges', assertion)
        self.assertEqual(response.status_code, 401)

    def test_issue_assertion_with_notify(self):
        self.client.force_authenticate(user=self.test_user)
        assertion = {
            "email": "ottonomy@gmail.com",
            'create_notification': True
        }
        response = self.client.post('/v1/issuer/issuers/test-issuer-2/badges/badge-of-testing/assertions', assertion)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(mail.outbox), 1)

    def test_authenticated_owner_list_assertions(self):
        self.client.force_authenticate(user=self.test_user)
        response = self.client.get('/v1/issuer/issuers/test-issuer-2/badges/badge-of-testing/assertions')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_issuer_instance_list_assertions(self):

        self.client.force_authenticate(user=self.test_user)
        response = self.client.get('/v1/issuer/issuers/test-issuer-2/assertions')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_issuer_instance_list_assertions_with_id(self):

        self.client.force_authenticate(user=self.test_user)
        response = self.client.get('/v1/issuer/issuers/test-issuer-2/assertions?recipient=test@example.com')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_revoke_assertion(self):

        self.client.force_authenticate(user=self.test_user)
        response = self.client.delete(
            '/v1/issuer/issuers/test-issuer/badges/badge-of-testing/assertions/92219015-18a6-4538-8b6d-2b228e47b8aa',
            {'revocation_reason': 'Earner kind of sucked, after all.'}
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.get('/public/assertions/92219015-18a6-4538-8b6d-2b228e47b8aa')
        self.assertEqual(response.status_code, 410)

    def test_revoke_assertion_missing_reason(self):
        self.client.force_authenticate(user=self.test_user)
        response = self.client.delete(
            '/v1/issuer/issuers/test-issuer/badges/badge-of-testing/assertions/92219015-18a6-4538-8b6d-2b228e47b8aa',
            {}
        )

        self.assertEqual(response.status_code, 400)

    def test_issue_svg_badge(self):
        # load test image into media files if it doesn't exist
        self.ensure_image_exists(BadgeClass.objects.get(slug='badge-of-svg-testing'), 'test_badgeclass.svg')

        self.client.force_authenticate(user=self.test_user)
        assertion = {
            "email": "test@example.com"
        }
        response = self.client.post('/v1/issuer/issuers/test-issuer-2/badges/badge-of-svg-testing/assertions', assertion)

        self.assertEqual(response.status_code, 201)

        slug = response.data.get('slug')
        response = self.client.get('/v1/issuer/issuers/test-issuer-2/badges/badge-of-svg-testing/assertions/{}'.format(slug))
        self.assertEqual(response.status_code, 200)

    def test_new_assertion_updates_cached_user_badgeclasses(self):
        self.client.force_authenticate(user=self.test_user)
        badgelist = self.client.get('/v1/issuer/all-badges')
        badge_data = badgelist.data[0]
        number_of_assertions = badge_data['recipient_count']
        # self.ensure_image_exists(badge, 'test_badgeclass.svg') # replace with that badge's filename

        new_assertion_props = {
            'email': 'test3@example.com',
        }

        response = self.client.post('/v1/issuer/issuers/test-issuer-2/badges/badge-of-testing/assertions', new_assertion_props)
        self.assertEqual(response.status_code, 201)

        new_badgelist = self.client.get('/v1/issuer/all-badges')
        new_badge_data = new_badgelist.data[0]
        updated_number_of_assertions = new_badge_data['recipient_count']

        self.assertEqual(updated_number_of_assertions, number_of_assertions + 1)


@override_settings(
    CELERY_ALWAYS_EAGER=True,
    SESSION_ENGINE='django.contrib.sessions.backends.cache',
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
            'LOCATION': os.path.join(TOP_DIR, 'test.cache'),
        }
    }
)
class PublicAPITests(IssuerTestBase):
    """
    Tests the ability of an anonymous user to GET one public badge object
    """
    def setUp(self):
        super(PublicAPITests, self).setUp()

        # ensure records are published to cache
        issuer = Issuer.cached.get(slug='test-issuer')
        issuer.cached_badgeclasses()
        Issuer.cached.get(pk=self.issuer_2.pk)
        BadgeClass.cached.get(slug='badge-of-testing')
        BadgeClass.cached.get(pk=self.badgeclass_1.pk)
        BadgeInstance.cached.get(slug='92219015-18a6-4538-8b6d-2b228e47b8aa')
        pass

    def test_get_issuer_object(self):
        with self.assertNumQueries(0):
            response = self.client.get('/public/issuers/test-issuer')
            self.assertEqual(response.status_code, 200)

    def test_get_issuer_object_that_doesnt_exist(self):
        with self.assertNumQueries(1):
            response = self.client.get('/public/issuers/imaginary-issuer')
            self.assertEqual(response.status_code, 404)

    def test_get_badgeclass_image_with_redirect(self):
        with self.assertNumQueries(0):
            response = self.client.get('/public/badges/badge-of-testing/image')
            self.assertEqual(response.status_code, 302)

    def test_get_assertion_image_with_redirect(self):
        assertion = BadgeInstance.objects.get(slug='92219015-18a6-4538-8b6d-2b228e47b8aa')
        assertion.issuer.cached_badgeclasses()
        assertion.cached_evidence()

        with self.assertNumQueries(0):
            response = self.client.get('/public/assertions/92219015-18a6-4538-8b6d-2b228e47b8aa/image', follow=False)
            self.assertEqual(response.status_code, 302)

    def test_get_assertion_json_explicit(self):
        assertion = BadgeInstance.objects.get(slug='92219015-18a6-4538-8b6d-2b228e47b8aa')
        assertion.issuer.cached_badgeclasses()
        assertion.cached_evidence()

        with self.assertNumQueries(0):
            response = self.client.get('/public/assertions/92219015-18a6-4538-8b6d-2b228e47b8aa',
                                       **{'HTTP_ACCEPT': 'application/json'})
            self.assertEqual(response.status_code, 200)

            # Will raise error if response is not JSON.
            content = json.loads(response.content)

            self.assertEqual(content['type'], 'Assertion')

    def test_get_assertion_json_implicit(self):
        """ Make sure we serve JSON by default if there is a missing Accept header. """

        assertion = BadgeInstance.objects.get(slug='92219015-18a6-4538-8b6d-2b228e47b8aa')
        assertion.issuer.cached_badgeclasses()
        assertion.cached_evidence()

        with self.assertNumQueries(0):
            response = self.client.get('/public/assertions/92219015-18a6-4538-8b6d-2b228e47b8aa')
            self.assertEqual(response.status_code, 200)

            # Will raise error if response is not JSON.
            content = json.loads(response.content)

            self.assertEqual(content['type'], 'Assertion')

    def test_get_assertion_html(self):
        """ Ensure hosted Assertion page returns HTML if */* is requested and that it has OpenGraph metadata properties. """
        assertion = BadgeInstance.objects.get(slug='92219015-18a6-4538-8b6d-2b228e47b8aa')
        assertion.issuer.cached_badgeclasses()
        assertion.cached_evidence()

        with self.assertNumQueries(0):
            response = self.client.get('/public/assertions/92219015-18a6-4538-8b6d-2b228e47b8aa', **{'HTTP_ACCEPT': '*/*'})
            self.assertEqual(response.status_code, 200)

            self.assertContains(response, '<meta property="og:url"')

    def test_get_assertion_html_linkedin(self):
        assertion = BadgeInstance.objects.get(slug='92219015-18a6-4538-8b6d-2b228e47b8aa')
        assertion.issuer.cached_badgeclasses()
        assertion.cached_evidence()

        with self.assertNumQueries(0):
            response = self.client.get('/public/assertions/92219015-18a6-4538-8b6d-2b228e47b8aa',
                                       **{'HTTP_USER_AGENT': 'LinkedInBot/1.0 (compatible; Mozilla/5.0; Jakarta Commons-HttpClient/3.1 +http://www.linkedin.com)'})
            self.assertEqual(response.status_code, 200)

            self.assertContains(response, '<meta property="og:url"')


class FindBadgeClassTests(IssuerTestBase):
    def test_can_find_imported_badge_by_id(self):
        self.client.force_authenticate(user=self.test_user)

        url = "{url}?identifier={id}".format(
            url=reverse('find_badgeclass_by_identifier'),
            id='http://badger.openbadges.org/badge/meta/mozfest-reveler'
        )

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['json'].get('name'), 'MozFest Reveler')

    def test_can_find_issuer_badge_by_id(self):
        self.client.force_authenticate(user=self.test_user)

        url = "{url}?identifier={id}".format(
            url=reverse('find_badgeclass_by_identifier'),
            id=self.badgeinstance_1.jsonld_id
        )

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['json'].get('name'), self.badgeinstance_1.name)

    def test_can_find_issuer_badge_by_slug(self):
        self.client.force_authenticate(user=self.test_user)

        url = "{url}?identifier={slug}".format(
            url=reverse('find_badgeclass_by_identifier'),
            slug='fresh-badge-of-testing'
        )

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['json'].get('name'), 'Fresh Badge of Testing')