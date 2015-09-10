import inspect

from rest_framework.serializers import ValidationError

from composition.utils import badge_email_matches_emails

from .utils import domain


class BadgeCheckBase(object):
    warnings = []

    def __new__(cls, badge_instance, *args, **kwargs):
        if badge_instance.version.startswith('v1'):
            cls = BadgeCheckTests_V1_0
        if badge_instance.version.startswith('v0'):
            cls = BadgeCheckTests_V0_5

        return super(BadgeCheckBase, cls).__new__(cls, badge_instance,
                                                  *args, **kwargs)

    def __init__(self, badge_instance, badge_class, issuer,
                 verified_emails, badge_instance_url=None):
        self.badge_instance = badge_instance
        self.badge_class = badge_class
        self.issuer = issuer
        self.verified_emails = verified_emails
        self.instance_url = badge_instance_url

    def validate(self):
        self.results = []

        checks = inspect.getmembers(
            self, lambda method: inspect.ismethod(method)
            and method.__name__.startswith('check_'))

        for check_name, check_method in checks:
            check_type = check_name in self.warnings and 'warning' or 'error'
            try:
                getattr(self, check_name)()
                self.results.append((check_name, True, check_type, ''))
            except ValidationError as e:
                self.results.append((check_name, False, check_type, e.detail))

        return self.is_valid()

    def is_valid(self):
        if not self.results:
            self.validate()

        for check_name, passed, check_type, message in self.results:
            if check_type == 'error' and not passed:
                return False

        return True


class BadgeCheck(BadgeCheckBase):

    def __init__(self, *args, **kwargs):
        self.matched_email = None
        super(BadgeCheck, self).__init__(*args, **kwargs)

    def validate(self):
        self.matched_email = None
        super(BadgeCheck, self).validate()

    def check_components_have_same_version(self):
        # Validation between components of the MetaSerializer
        same_version_components = (self.badge_class.version ==
                                   self.issuer.version ==
                                   self.badge_instance.version)
        if not same_version_components:
            raise ValidationError(
                "Components assembled with different specification versions.")

    def check_badge_belongs_to_recipient(self):
        # Request.user specific validation
        matched_email = badge_email_matches_emails(self.badge_instance,
                                                   self.verified_emails)
        if not matched_email:
            raise ValidationError(
                "The badge you are trying to import does not belong to one of \
                your verified e-mail addresses.")
        # TODO: Pass this in context not via a ComponentsSerializer attribute
        self.matched_email = matched_email


class BadgeCheckTests_V0_5(BadgeCheck):

    def __init__(self, *args, **kwargs):
        super(BadgeCheckTests_V0_5, self).__init__(*args, **kwargs)
        self.warnings.extend(['check_issuer_and_assertion_domains_differ'])

    def validate(self):
        # Form-specific badge instance validation (reliance on URL input)
        if not self.instance_url:
            raise ValidationError(
                "We cannot verify a v0.5 badge without its hosted URL.")

        super(BadgeCheckTests_V0_5, self).validate()

    def check_issuer_and_assertion_domains_differ(self):
        # Form-specific badge instance validation (reliance on form data)
        if not (domain(self.issuer['origin']) ==
                domain(self.instance_url)):  # TODO: Can come from baked image
            raise ValidationError(
                "The URL of the institution does not match the verifiable \
                host of the assertion.")


class BadgeCheckTests_V1_0(BadgeCheck):

    def check_components_have_same_domain(self):
        resources = filter(None, [self.badge_instance['verify']['url'],
                                  self.badge_instance['badge'],
                                  self.badge_instance.get('url'),
                                  self.badge_instance.get('id')])
        same_domains = len(set([domain(resource)
                                for resource in resources])) == 1
        if not same_domains:
            raise ValidationError(
                "Component resource references don't share the same \
                domain.")
