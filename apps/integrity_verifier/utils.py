import json
import re

from bakery import unbake


def get_instance_url_from_assertion(assertion):
    """
    With a python dict as input, return the URL from where it may appear
    in different versions of the Open Badges specification
    """
    options = [
        assertion.get('id'),
        assertion.get('@id'),
        assertion.get('verify', {}).get('url')
    ]
    # Return the first non-None item in options or None.
    return next(iter([item for item in options if item is not None]), None)


def get_instance_url_from_jwt(signed_assertion):
    raise NotImplementedError("Parsing JWT tokens not implemented.")


def get_instance_url_from_unknown_string(badge_input):
    try:
        assertion = json.loads(badge_input)
    except ValueError:
        earl = re.compile(r'^https?')
        if earl.match(badge_input):
            return badge_input

        jwt_regex = re.compile(r'^\w+\.\w+\.\w+$')
        if jwt_regex.match(badge_input):
            return get_instance_url_from_jwt(badge_input)
    else:
        return get_instance_url_from_assertion(assertion)


def get_instance_url_from_image(imageFile):
    """ unbake an open file, and return the assertion URL contained within """
    image_contents = unbake(imageFile)

    return get_instance_url_from_unknown_string(image_contents)
