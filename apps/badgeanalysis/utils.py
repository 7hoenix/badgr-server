"""
Utilities to deal with understanding badges from an unspecified issuer
"""
import json
from jsonschema import validate, Draft4Validator, FormatChecker
from jsonschema.exceptions import FormatError, ValidationError
import os
import re
import collections
from models import InfoObject
from pyld import jsonld


SCHEMA_META= {
	'plainurl': {
		'schemaFile': 'plainuri.json',
		'schemaUrl': 'http://openbadges.org/standard/0.5/schema/v0.5-plainuri',
		'defaultType': 'assertion',
		'context': 'http://openbadges.org/standard/context/0.5',
		'contextFile': '0.5'
			
	},
	'v0_5': {
		'schemaFile': 'OBI-v0.5-assertion.json',
		'schemaUrl': 'http://openbadges.org/standard/0.5/schema/v0.5-assertion',
		'defaultType': 'assertion',
		'context': 'http://openbadges.org/standard/context/0.5',
		'contextFile': '0.5'
		
	},
	'v1_0strict': {
		'schemaFile': 'OBI-v1.0-linked-badgeclass.json',
		'schemaUrl': 'http://openbadges.org/standard/1.0/schema/v1.0-assertion-linked-badgeclass',
		'defaultType': 'assertion',
		'context': 'http://openbadges.org/standard/1.0/context',
		'contextFile': '1.0'
	},
	'backpack_error_1_0': {
		'schemaFile': 'backpack-error-from-valid-1.0.json',
		'schemaUrl': 'http://openbadges.org/standard/0.5/schema/v0.5-1.0-mashed-up',
		'defaultType': 'assertion',
		'context': 'http://openbadges.org/standard/0.5/context/',
		'contextFile': '0.5'
	},
	'v1_1': {
		'schemaFile': 'OBI-v1.1-assertion',
		'schemaUrl': 'http://openabadges.org/standard/1.1/schema/1.1-assertion',
		'defaultType': 'assertion',
		'context': 'http://openbadges.org/standard/1.1/context',
		'contextFile': '1.1'
	}
}
schemaFiles = {}

SCHEMA_TREE = {
	'test': 'plainurl',
	'noMatch': {
		'test': 'backpack_error_1_0',
		'noMatch': { 
			'test': 'v1_0strict',
			'noMatch': {
				'test': 'v0_5'
			}
		}
	}
}

def schema_filename(schemaKey):
	return SCHEMA_META[schemaKey]['schemaFile']
def schema_type(schemaKey):
	return SCHEMA_META[schemaKey]['type']
def schema_context(schemaKey):
	return SCHEMA_META[schemaKey]['context']
def schema_contextFile(schemaKey):
	return SCHEMA_META[schemaKey]['contextFile']

def load_schema_from_filesystem(schemaKey):
	"""
	Loads a schema from the file system based on the filename specified in SCHEMA_META
	"""
	if not schemaKey in schemaFiles:
		schemaFiles[schemaKey] = json.loads(open(os.path.join(os.path.dirname(__file__),'schema',schema_filename(schemaKey)),'r').read())
	return schemaFiles[schemaKey]

def load_context_from_filesystem(schemaKey):
	"""
	Loads a context from the file system based on the filename specified in SCHEMA_META
	"""
	return json.loads(open(os.path.join(os.path.dirname(__file__),'context',schema_contextFile(schemaKey)),'r').read())
	 

def of_badgeObject_type(guess, typeString):
	reggie = re.compile(re.compile('%s'%guess), flags=re.I)
	return reggie.search(typeString)

def identify_badgeObject_type(typeString):
	"""
	A method that determines if an IRI or shorthand type is a version of 'assertion', 'badgeclass', or 'issuer'
	"""
	possibilities = ['assertion','badgeclass','issuer']
	for guess in possibilities:
		if of_badgeObject_type(guess, typeString):
			return guess

def verify_recipient(identifier, hash_string, salt):
	"""
	Check if a badge recipient is indeed the expected recipient (email address)
	"""
	if hash_string.startswith('sha256$'):
		return hash_string == 'sha256$' + hashlib.sha256(email+salt).hexdigest()
	elif hash_string.startswith('md5$'):
		return hash_string == 'md5$' + hashlib.md5(email+salt).hexdigest()


def is_json(string):
	if isinstance(string, dict):
		return False
	try:
		json_result = json.loads(string)
	except ValueError, e:
		return False
	except TypeError, e:
		return False
	else: 
		return True

def try_json_load(input):
	if isinstance(input, dict) or isinstance(input, (int, long, float, complex)):
		return input
	if isinstance(input, str):
		try:
			json_result = json.loads(input)
		except ValueError as e:
			return input
		except TypeError as e:
			return input
		else:
			return json_result

"""
Utilities for matching badge objects with schema
""" 
def is_schemable(input):
	if is_json(input) or isinstance(input, list) or isinstance(input, str):
		return True
	else:
		return False


def test_against_schema_tree(badgeObject, testTree=SCHEMA_TREE):
	if 'test' in testTree:
		schemaKey = testTree['test']
	else: 
		raise LookupError("Schema Tree malformed, could not find a test reference when needed. " + str(testTree))
		return None

	if test_against_schema(badgeObject, schemaKey):
		if 'match' in testTree:
			return test_against_schema_tree(badgeObject, testTree['match'])
		else: 
			return schemaKey
	elif 'noMatch' in testTree:
		return test_against_schema_tree(badgeObject, testTree['noMatch'])
	else:
		return None

def test_against_schema(badgeObject, schemaKey):
	"""
	Reads the specified schema based on the filename registered for schemaKey, and processes it into an object with json.loads()
	Then validates the badge object against it.
	"""
	v = test_for_errors_against_schema(badgeObject, schemaKey)
	if isinstance(v,ValidationError):
		return False
	else:
		return True

def test_for_errors_against_schema(badgeObject, schemaKey):
	currentSchema = load_schema_from_filesystem(schemaKey)
	try:
		validate(badgeObject, currentSchema, Draft4Validator, format_checker=FormatChecker())
	except ValidationError as e:
		return e
	else: 
		return None


"""
Utilities for JSON-LD + badge objects
"""

def has_context(badgeObject):
	context = None
	try:
		context = badgeObject.get('@context')
	except AttributeError:
		return False
	finally:
		if context:
			return True
		return False

def custom_context_docloader(url):
	for schemaSet in SCHEMA_META:
		if url == SCHEMA_META[schemaSet].context:
			doc = {
                'contextUrl': None,
                'documentUrl': None,
                'document': load_context_from_filesystem(schemaSet)
            }
			return doc

	#fall back to default document loader
	return jsonld.load_document(url)


"""
Main badge analysis procedure
"""
# an orphan method probably not needed anymore.
def redumps_object_input(badgeInput):
	if isinstance(badgeInput, dict): 
		badgeObject = json.dumps(badgeObject)
	else: 
		badgeObject = badgeInput

	if is_json(badgeObject):
		schemaMatch = test_against_schema_tree(SCHEMA_TREE,badgeObject)
	return None


def start_analysis(badgeObject, infoObject=None):
	"""
	Takes what's extracted from a badge image (or potentially other badge objects), 
	ensures they're loaded up as python dictionaries and sets up an InfoObject
	to contain generated metadata about the badge.
	"""
	# Step 1: Try to get this in native dictionary format
	badgeObject = try_json_load(badgeObject)

	if not isinstance(badgeObject, dict):
		raise NotImplementedError("Testing for signed badges not implemented.")
		# Step1B: If it's still not JSON, see if it's a signed badge
		# TODO
		return

	infoObject = InfoObject(badgeObject)

	# Step 2: Gather JSON-LD information: context, type
	if has_context(badgeObject):
		context = badgeObject.get('@context')

		# Determine if the existing context has a suitable main OBI context within it. (This will return true for strings, objects and arrays)
		if isinstance(context, collections.Iterable):
			for contextElement in context:
				infoObject.setContext(contextElement)

		if '@type' in badgeObject:
			#TODO this is likely not going to be the full expanded IRI, likely a namespaced fragment
			infoObject.setType(badgeObject['@type'])
		else:
			#TODO schema currying for badge Classes that declared context but not type? Seems rare.
			infoObject.setType('assertion')

	else:
		matchingSchemaKey = test_against_schema_tree(badgeObject)

		if matchingSchemaKey == None:
			raise TypeError("Could not determine type of badge object with known schema set")
			return

		# TODO: Implement case for 'plainurl' to fetch assertion then start_analysis(fetched_assertion)
		else:
			infoObject.setContext( SCHEMA_META[matchingSchemaKey]['context'] )
			infoObject.setType( SCHEMA_META[matchingSchemaKey]['defaultType'] )

	# Step 3: Gather linked resources
	buildFullBadgeObject(infoObject)


def buildFullBadgeObject(infoObject):

	# Step 1: Set up a shell to drop badge objects into
	infoObject.initFullBadgeObject()

	# Step 2: Drop the input badge object into the right spot in that shell.
	if not infoObject.inputObjectType:
		#protect against missing default
		infoObject.inputObjectType = 'assertion'
	shortType = identify_badgeObject_type(infoObject.inputObjectType)
	#TODO What if shortType is None?
	infoObject.fullBadgeObject[shortType] = infoObject.inputObject

	# Step 3: Start pulling in linked components
	linked_components_missing(infoObject)


def linked_components_missing(infoObject):
	fullObject = infoObject.fullBadgeObject
	#TODO: refactor. This is kind of clunky. Will it hold up if the input isn't an assertion?
	try:
		if isinstance(fullObject['assertion'], dict):
			if isinstance(fullObject['assertion']['badge'], str):
				fullObject['badge'] = fetch_linked_component(fullObject['assertion']['badge'])
			elif isinstance(fullObject['assertion']['badge'], dict):
				fullObject['badge'] = fullObject['assertion']['badge']

		if isinstance(fullObject['badge'], dict):
			if isinstance(fullObject['badge']['issuer'], str):
				fullObject['issuer'] = fetch_linked_component(fullObject['badge']['issuer'])
			elif isinstance(fullObject['badge']['issuer'], dict):
				fullObject['issuer'] = fullObject['badge']['issuer']
	except Exception as e:
		#TODO Add errors to infoObject instead
		raise e
	validate_object(infoObject)

def fetch_linked_component(url):
	try:
		result = jsonld.load_document(url)
		result = result.document
	except jsonld.JsonLdError as e:
		raise IOError("error loading document " + url, cause=e)
		return None
	else: 
		 return result


def validate_object(infoObject):
	# TODO: NOW
	pass



