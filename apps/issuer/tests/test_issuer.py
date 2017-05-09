# encoding: utf-8
from __future__ import unicode_literals

import os.path

import os
from django.core.files.images import get_image_dimensions

from issuer.models import Issuer, BadgeClass
from mainsite.tests.base import BadgrTestCase, SetupIssuerHelper


class IssuerTests(SetupIssuerHelper, BadgrTestCase):
    example_issuer_props = {
        'name': 'Awesome Issuer',
        'description': 'An issuer of awe-inspiring credentials',
        'url': 'http://example.com',
        'email': 'contact@example.org'
    }

    def test_cant_create_issuer_if_unauthenticated(self):
        response = self.client.post('/v1/issuer/issuers', self.example_issuer_props)
        self.assertEqual(response.status_code, 401)

    def test_create_issuer_if_authenticated(self):
        self.setup_user(authenticate=True)

        response = self.client.post('/v1/issuer/issuers', self.example_issuer_props)
        self.assertEqual(response.status_code, 201)

        # assert that name, description, url, etc are set properly in response badge object
        badge_object = response.data.get('json')
        self.assertEqual(badge_object['url'], self.example_issuer_props['url'])
        self.assertEqual(badge_object['name'], self.example_issuer_props['name'])
        self.assertEqual(badge_object['description'], self.example_issuer_props['description'])
        self.assertEqual(badge_object['email'], self.example_issuer_props['email'])
        self.assertIsNotNone(badge_object.get('id'))
        self.assertIsNotNone(badge_object.get('@context'))

        # assert that the issuer was published to and fetched from the cache
        with self.assertNumQueries(0):
            slug = response.data.get('slug')
            response = self.client.get('/v1/issuer/issuers/{}'.format(slug))
            self.assertEqual(response.status_code, 200)

    def test_cant_create_issuer_if_authenticated_with_unconfirmed_email(self):
        self.setup_user(authenticate=True, verified=False)

        response = self.client.post('/v1/issuer/issuers', self.example_issuer_props)
        self.assertEqual(response.status_code, 403)

    def _create_issuer_with_image_and_test_resizing(self, image_path, desired_width=400, desired_height=400):
        self.setup_user(authenticate=True)

        with open(image_path, 'r') as badge_image:
            issuer_fields_with_image = self.example_issuer_props.copy()
            issuer_fields_with_image['image'] = badge_image

            response = self.client.post('/v1/issuer/issuers', issuer_fields_with_image, format='multipart')
            self.assertEqual(response.status_code, 201)

            self.assertIn('slug', response.data)
            issuer_slug = response.data.get('slug')
            new_issuer = Issuer.objects.get(entity_id=issuer_slug)

            image_width, image_height = get_image_dimensions(new_issuer.image.file)
            self.assertEqual(image_width, desired_width)
            self.assertEqual(image_height, desired_height)

    def test_create_issuer_image_500x300_resizes_to_400x400(self):
        image_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'testfiles', '500x300.png')
        self._create_issuer_with_image_and_test_resizing(image_path)

    def test_create_issuer_image_450x450_resizes_to_400x400(self):
        image_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'testfiles', '450x450.png')
        self._create_issuer_with_image_and_test_resizing(image_path)

    def test_create_issuer_image_300x300_stays_300x300(self):
        image_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'testfiles', '300x300.png')
        self._create_issuer_with_image_and_test_resizing(image_path, 300, 300)

    def test_can_update_issuer_if_authenticated(self):
        self.setup_user(authenticate=True)

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

    def test_get_empty_issuer_editors_set(self):
        test_user = self.setup_user(authenticate=True)
        issuer = self.setup_issuer(owner=test_user)

        response = self.client.get('/v1/issuer/issuers/{slug}/staff'.format(slug=issuer.entity_id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)  # Assert that there is just a single owner

    def test_add_user_to_issuer_editors_set_by_email(self):
        test_user = self.setup_user(authenticate=True)
        issuer = self.setup_issuer(owner=test_user)

        other_user = self.setup_user(authenticate=False)

        response = self.client.post('/v1/issuer/issuers/{slug}/staff'.format(slug=issuer.entity_id), {
            'action': 'add',
            'email': other_user.primary_email,
            'editor': True
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)  # Assert that there is now one editor

    def test_add_user_to_issuer_editors_set_too_many_methods(self):
        test_user = self.setup_user(authenticate=True)
        issuer = self.setup_issuer(owner=test_user)

        response = self.client.post('/v1/issuer/issuers/{slug}/staff'.format(slug=issuer.entity_id), {
            'action': 'add',
            'email': 'test3@example.com',
            'username': 'test3',
            'editor': True
        })
        self.assertEqual(response.status_code, 400)

    def test_add_user_to_issuer_editors_set_missing_identifier(self):
        test_user = self.setup_user(authenticate=True)
        issuer = self.setup_issuer(owner=test_user)

        response = self.client.post('/v1/issuer/issuers/{slug}/staff'.format(slug=issuer.entity_id), {
            'action': 'add',
            'editor': True
        })
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data, 'User not found. Neither email address or username was provided.')

    def test_bad_action_issuer_editors_set(self):
        test_user = self.setup_user(authenticate=True)
        issuer = self.setup_issuer(owner=test_user)

        response = self.client.post('/v1/issuer/issuers/{slug}/staff'.format(slug=issuer.entity_id), {
            'action': 'DO THE HOKEY POKEY',
            'username': 'test2',
            'editor': True
        })
        self.assertEqual(response.status_code, 400)

    def test_add_nonexistent_user_to_issuer_editors_set(self):
        test_user = self.setup_user(authenticate=True)
        issuer = self.setup_issuer(owner=test_user)

        erroneous_username = 'wronguser'
        response = self.client.post('/v1/issuer/issuers/{slug}/staff'.format(slug=issuer.entity_id), {
            'action': 'add',
            'username': erroneous_username,
            'editor': True
        })
        self.assertContains(response, "User {} not found.".format(erroneous_username), status_code=404)

    def test_add_user_to_nonexistent_issuer_editors_set(self):
        test_user = self.setup_user(authenticate=True)
        erroneous_issuer_slug = 'wrongissuer'
        response = self.client.post(
            '/v1/issuer/issuers/{slug}/staff'.format(slug=erroneous_issuer_slug),
            {'action': 'add', 'username': 'test2', 'editor': True}
        )
        self.assertEqual(response.status_code, 404)

    def test_add_remove_user_with_issuer_staff_set(self):
        test_user = self.setup_user(authenticate=True)
        test_issuer = self.setup_issuer(owner=test_user)

        other_user = self.setup_user(authenticate=False)

        self.assertEqual(len(test_issuer.staff.all()), 1)

        first_response = self.client.post('/v1/issuer/issuers/{slug}/staff'.format(slug=test_issuer.entity_id), {
            'action': 'add',
            'email': other_user.primary_email
        })
        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(len(test_issuer.staff.all()), 2)

        second_response = self.client.post('/v1/issuer/issuers/{slug}/staff'.format(slug=test_issuer.entity_id), {
            'action': 'remove',
            'email': other_user.primary_email
        })
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(len(test_issuer.staff.all()), 1)

    def test_delete_issuer_successfully(self):
        test_user = self.setup_user(authenticate=True)
        test_issuer = self.setup_issuer(owner=test_user)

        response = self.client.delete('/v1/issuer/issuers/{slug}'.format(slug=test_issuer.entity_id), {})
        self.assertEqual(response.status_code, 200)

    def test_delete_issuer_with_unissued_badgeclass_successfully(self):
        test_user = self.setup_user(authenticate=True)
        test_issuer = self.setup_issuer(owner=test_user)

        test_badgeclass = BadgeClass(name="Deletable Badge", issuer=test_issuer)
        test_badgeclass.save()

        response = self.client.delete('/v1/issuer/issuers/{slug}'.format(slug=test_issuer.entity_id), {})
        self.assertEqual(response.status_code, 200)

    def test_cant_delete_issuer_with_issued_badge(self):
        test_user = self.setup_user(authenticate=True)
        test_issuer = self.setup_issuer(owner=test_user)

        test_badgeclass = self.setup_badgeclass(issuer=test_issuer)
        test_badgeclass.issue(recipient_id='new-bage-recipient@email.test')

        response = self.client.delete('/v1/issuer/issuers/{slug}'.format(slug=test_issuer.entity_id), {})
        self.assertEqual(response.status_code, 400)

    def test_creating_a_new_badgeclass_updates_all_badges(self):
        test_user = self.setup_user(authenticate=True)

        # get list of all badges
        badgelist = self.client.get('/v1/issuer/all-badges')

        # create a new issuer
        response = self.client.post('/v1/issuer/issuers', {
            'name': 'Fresh Issuer',
            'description': "Fresh Issuer",
            'url': 'http://freshissuer.com',
            'email': 'prince@freshissuer.com',
        })
        self.assertEqual(response.status_code, 201)
        self.assertIn('slug', response.data)
        new_issuer_slug = response.data.get('slug')

        # create a new badgeclass on new issuer
        with open(self.get_test_image_path(), 'r') as badge_image:
            response = self.client.post('/v1/issuer/issuers/{slug}/badges'.format(slug=new_issuer_slug), {
                'name': 'Badge of Freshness',
                'description': "Fresh Badge",
                'image': badge_image,
                'criteria': 'http://wikipedia.org/Freshness',
            })
            self.assertEqual(response.status_code, 201)

        # refetch list of badges
        new_badgelist = self.client.get('/v1/issuer/all-badges')

        self.assertEqual(len(new_badgelist.data), len(badgelist.data) + 1)




