from django.test import TestCase
import sys
import json
import os
from jsonschema import Draft4Validator
import pngutils

import utils
from badgeanalysis.models import OpenBadge
from badgeanalysis.badge_objects import Assertion, BadgeClass, IssuerOrg, Extension, BadgeObject, badge_object_class


# Some test assertions of different sorts
junky_assertion = {
    "uid": "100",
    "issuedOn": 1395112143,
    "recipient": "sha256$c56e0383f16d3bd4705c11e4eff7002ca27540b2ba0b32d7b389377f9e4d68e2",
    "evidence": "http://someevidence.org",
    "verify": {
        "url": "http://badges.schoolofdata.org/badge/data-to-diagrams/instance/100",
        "type": "hosted"
    },
    "badge": {
        "issuer": {
            "url": "http://schoolofdata.org",
            "image": "http://assets.okfn.org/p/schoolofdata/img/logo.png",
            "name": "School of Data",
            "email": "michael.bauer@okfn.org",
            "contact": "michael.bauer@okfn.org",
            "revocationList": "http://badges.schoolofdata.org/revocation",
            "description": "School of Data works to empower civil society organizations, journalists and citizens with the skills they need to use data effectively-evidence is power!",
            "_location": "http://badges.schoolofdata.org/issuer/school-of-data",
            "origin": "http://schoolofdata.org"
        },
        "description": "You have completed the Data to Diagrams module on the School of Data",
        "image": "http://p2pu.schoolofdata.org/badges/School_Of_Data_Badges/Badges/Badge_Data_to_Diagrams.png",
        "criteria": "http://badges.schoolofdata.org/badge/data-to-diagrams/criteria",
        "name": "Data to Diagrams",
        "_location": "http://badges.schoolofdata.org/badge/data-to-diagrams"
    },
    "_originalRecipient": {
        "identity": "sha256$c56e0383f16d3bd4705c11e4eff7002ca27540b2ba0b32d7b389377f9e4d68e2",
        "type": "email",
        "hashed": True
    },
    "issued_on": 1395112143
}
valid_1_0_assertion = {
    "uid": "2f900c7c-f473-4bff-8173-71b57472a97f",
    "recipient": {
        "identity": "sha256$1665bc8985e802067453647c1676b07a1834c327bfea24c67f3dbb721eb84d22",
        "type": "email",
        "hashed": True,
        "salt": "UYMA1ybJ4UfqHJO4r3x7LjpGE0LEog"
    },
    "badge": "http://openbadges.oregonbadgealliance.org/api/badges/53d727a11f04f3a84a99b002",
    "verify": {
        "type": "hosted",
        "url": "http://openbadges.oregonbadgealliance.org/api/assertions/53d944bf1400005600451205"
    },
    "issuedOn": 1406747839,
    "image": "http://openbadges.oregonbadgealliance.org/api/assertions/53d944bf1400005600451205/image"
}

# Construct a docloader function that will return preloaded responses for predetermined URLs
# Load in a dict of urls and the response bodies you want them to deliver: 
# response_list = {'http://google.com': 'Hacked by the lizard overlords, hahaha!'}
def mock_docloader_factory(response_list):
    def mock_docloader(url):
        return response_list[url]
    return mock_docloader


class BadgeUtilsTests(TestCase):
    def test_does_is_json_process_dicts(self):
        """
        Make sure we can determine that a dict is not json
        """
        someDict = {'key': True}
        self.assertFalse(utils.is_json(someDict))

    def test_try_json_load_good(self):
        self.assertEqual(utils.try_json_load('{ "key": 42 }'), {'key': 42})

    def test_try_json_load_already_obj(self):
        self.assertEqual(utils.try_json_load({'key': 42}), {'key': 42})

    def test_try_json_load_junk(self):
        self.assertEqual(utils.try_json_load("{ holey guacamole batman"), "{ holey guacamole batman")
        self.assertEqual(utils.try_json_load(23311233), 23311233)

    def test_schemable_things_should_be_schemable(self):
        """
        Make sure that is_json will return true for a real chunk of json or a string URL
        """
        self.assertTrue(utils.is_schemable("http://someurl.com/badge"))
        self.assertTrue(utils.is_schemable('{"obj": "value", "another": ["value"]}'))

    def test_does_is_json_spit_out_problems_for_unexpected_types(self):
        """
        Make sure that is_json doesn't cause no problems if we throw some other junk at it.
        """

        try:
            utils.is_json(list(("1", 2, "three")))
            utils.is_json(set(["a", "bee", "C"]))
            utils.is_json(tuple(("strings", "planes", "automobiles")))
        except:
            error = str(sys.exc_info()[0])
        else:
            error = None
        finally:
            self.assertEqual(error, None)


class BadgeSchemaTests(TestCase):
    # def test_check_schema(self):
    #   """
    #   Make sure some schema that we're using doesn't make the validator choke. This tests them all but the
    #   error message spit out when there's a problem doesn't quickly tell you which schema had a problem.
    #   """

    #   schemaList = ['plainuri.json','backpack-error-from-valid-1.0.json','OBI-v0.5-assertion.json','OBI-v1.0-linked-badgeclass.json']
    #   for schema in schemaList:
    #       self.assertEqual(Draft4Validator.check_schema(json.loads(open(os.path.join(os.path.dirname(__file__),'schema',schema),'r').read())), None)

    def test_against_schema_true_urlstring(self):
        """
        Make sure that a url string returns a pass against the plainurl is_schema.
        """
        # self.assertTrue(test_against_schema('http://url.com/badgeUrl', 'plainurl'))
        # self.assertFalse(test_against_schema("a stinkin' turnip", 'plainurl'))
        # self.assertFalse(test_against_schema("", 'plainurl'))

    def test_against_schema_tree_urlstring(self):
        """
        Make sure that the url string is properly matched against the plainurl schema
        """
        # self.assertEqual(test_against_schema_tree("http://url.com/badgeUrl"), 'plainurl')

    def test_against_schema_backpack_error_assertion(self):
        """
        Make sure a junky ol' backpack-mangled badge gets matched with the proper schema
        """

        # self.assertTrue(test_against_schema(junky_assertion, 'backpack_error_1_0'))
        # self.assertFalse(test_against_schema(junky_assertion, 'v1_0strict'))

    def test_junky_tree(self):
        """
        Make sure a junky ol' backpack-mangled badge gets matched with the proper is_schemable
        """

        # self.assertEqual(test_against_schema_tree(junky_assertion), 'backpack_error_1_0')

    def test_valid_1_0_tree(self):
        """
        Make sure a valid 1.0 assertion makes its way through the tree
        """
        # self.assertEqual(test_against_schema_tree(valid_1_0_assertion), 'v1_0strict')

    def test_schema_context(self):
        # self.assertEqual( schema_context('v1_0strict'), 'http://standard.openbadges.org/1.0/context' )
        pass


class BadgeContextTests(TestCase):
    def test_has_context(self):
        self.assertTrue(utils.has_context({"@context": "http://someurl.com/context", "someprop": 42}))
        self.assertFalse(utils.has_context({"howdy": "stranger"}))

    def test_has_context_handle_nonObjects(self):
        """
        This test isn't working right, but it's supposed to make sure has_context doesn't choke on things.
        """
        exceptage = None
        try:
            self.assertFalse(utils.has_context("Hahaha, I'm a string."))
            self.assertFalse(utils.has_context([{"@context": "http://someurl.com/context"}]))
        except AssertionError as e:
            exceptage = e
        finally:
            self.assertEqual(exceptage, None)

simpleOneOne = {
    "@context": "http://standard.openbadges.org/1.1/context",
    "@type": "assertion",
    "@id": "http://example.org/assertion25",
    "uid": 25,
    "recipient": {
        "identity": "testuser@example.org",
        "hashed": False
    },
    "badge": "http://example.org/badge1"
}
simpleOneOneBC = {
    "@context": "http://standard.openbadges.org/1.1/context",
    "@type": "badgeclass",
    "@id": "http://example.org/badge1",
    "name": "Badge of Awesome",
    "description": "Awesomest badge for awesome people.",
    "image": "http://placekitten.com/300/300",
    "criteria": "http://example.org/badge1criteria",
    "issuer": "http://example.org/issuer"
}
simpleOneOneIssuer = {
    "@context": "http://standard.openbadges.org/1.1/context",
    "@type": "issuerorg",
    "@id": "http://example.org/issuer",
    "name": "Issuer of Awesome",
    "url": "http://example.org"
}
def oneone_docloader():
    response_list = {
        'http://example.org/assertion25': simpleOneOne,
        'http://example.org/badge1': simpleOneOneBC,
        'http://example.org/issuer': simpleOneOneIssuer
    }
    return mock_docloader_factory(response_list)

oneOneArrayType = {
    "@context": "http://standard.openbadges.org/1.1/context",
    "@type": ["assertion", "http://othertype.com/type"],
    "@id": "http://example.org/assertion25",
    "uid": 25
}

oneOneNonUrlID = {
    "@context": "http://standard.openbadges.org/1.1/context",
    "@type": "assertion",
    "@id": "assertion25",
    "uid": 25
}
simpleOneOneNoId = {
    "@context": "http://standard.openbadges.org/1.1/context",
    "@type": "assertion",
    "verify": {"type": "hosted", "url": "http://example.org/assertion25"},
    "uid": 25
}


# class OpenBadgeTests(TestCase):
#     def test_validateMainContext(self):
#         context = "http://standard.openbadges.org/1.1/context"
#         a = OpenBadge.validateMainContext(OpenBadge(simpleOneOne), context)
#         self.assertEqual(a, context)

#     def test_simple_OpenBadge_construction_noErrors(self):
#         try:
#             openBadge = OpenBadge(simpleOneOne)
#         except Exception as e:
#             self.assertEqual(e, None)
#         self.assertEqual(openBadge.getProp('assertion', 'uid'), 25)
#         self.assertEqual(openBadge.getProp('assertion', '@type'), 'assertion')

#     def test_oneOneArrayType(self):
#         try:
#             openBadge = OpenBadge(oneOneArrayType)
#         except Exception as e:
#             self.assertEqual(e, None)
#         self.assertEqual(openBadge.getProp('assertion', 'uid'), 25)

#     def test_oneOneNonUrlID(self):
#         #TODO, both implement id validation and then make this test actually pass
#         try:
#             openBadge = OpenBadge(oneOneNonUrlID)
#         except Exception as e:
#             # What is this doing?
#             self.assertFalse(e is None)
#         self.assertEqual(openBadge.getProp('assertion', 'uid'), 25)

#     def test_id_from_verify_url(self):
#         try:
#             openBadge = OpenBadge(simpleOneOne)
#         except Exception as e:
#             self.assertEqual(e, None)
#         self.assertEqual(openBadge.getProp('assertion', '@id'), "http://example.org/assertion25")

#     def test_valid_1_0_construction(self):
#         try:
#             openBadge = OpenBadge(valid_1_0_assertion)
#         except Exception as e:
#             self.assertEqual(e, None)
#         self.assertEqual(openBadge.getProp('assertion', '@type'), 'assertion')
#         self.assertEqual(openBadge.getProp('assertion', '@id'), 'http://openbadges.oregonbadgealliance.org/api/assertions/53d944bf1400005600451205')
#         self.assertEqual(openBadge.getProp('assertion', 'issuedOn'), 1406747839)

#     def test_junky_construction(self):
#         try:
#             openBadge = OpenBadge(junky_assertion)
#         except Exception as e:
#             self.assertEqual(e, None)
#         self.assertEqual(openBadge.getProp('assertion', '@type'), 'assertion')
#         self.assertEqual(openBadge.getProp('assertion', '@id'), 'http://badges.schoolofdata.org/badge/data-to-diagrams/instance/100')
#         self.assertEqual(openBadge.getProp('assertion', 'issuedOn'), 1395112143)

#     def test_getting_prop_by_iri_simpleOneOne(self):
#         try:
#             openBadge = OpenBadge(simpleOneOne)
#         except Exception as e:
#             self.assertEqual(e, None)
#         self.assertEqual(openBadge.getLdProp('assertion', 'http://standard.openbadges.org/definitions#AssertionUid'), 25)
#         self.assertEqual(openBadge.getLdProp('assertion', 'http://standard.openbadges.org/definitions#BadgeClass'), "http://example.org/badge1")


# class ImageExtractionTests(TestCase):
#     def test_basic_image_extract(self):
#         imgFile = open(os.path.join(os.path.dirname(__file__), 'testfiles', '1.png'), 'r')
#         assertion = pngutils.extract(imgFile)
#         self.assertTrue(utils.is_json(assertion))

#         assertion = utils.try_json_load(assertion)
#         self.assertEqual(assertion.get("uid"), "2f900c7c-f473-4bff-8173-71b57472a97f")

#     def test_analyze_image_upload(self):
#         imgFile = open(os.path.join(os.path.dirname(__file__), 'testfiles', '1.png'), 'r')

#         openBadge = utils.analyze_image_upload(imgFile)
#         self.assertEqual(openBadge.getProp("assertion", "uid"), "2f900c7c-f473-4bff-8173-71b57472a97f")


class BadgeObjectsTests(TestCase):

    def test_mock_docloader_factory(self):
        response_list = {'http://google.com': 'Hahahaha, hacked by the lizard overlords.'}
        docloader = mock_docloader_factory(response_list)
        self.assertEqual(docloader('http://google.com'), 'Hahahaha, hacked by the lizard overlords.')

    def test_assertion_processing_oneone(self):
        self.maxDiff = None
        docloader = oneone_docloader()
        badgeMetaObject = badge_object_class('assertion').processBadgeObject({'badgeObject': simpleOneOne}, docloader)
        expected_result = {
            'badgeObject': simpleOneOne,
            'context': 'http://standard.openbadges.org/1.1/context',
            'id': 'http://example.org/assertion25',
            'notes': ['<Badge Validation success (RecipientRequiredValidator): Recipient input not needed, embedded recipient identity is not hashed>'],
            'type': 'assertion'
        }
        self.assertEqual(badgeMetaObject, expected_result)
