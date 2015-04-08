from rest_framework import permissions
import rules

SAFE_METHODS = ['GET', 'HEAD', 'OPTIONS']


@rules.predicate
def is_issuer_owner(user, issuer):
    return user == issuer.owner


@rules.predicate
def is_editor(user, badgeclass):
    return badgeclass.issuer.editors.filter(pk=user.pk).exists()


@rules.predicate
def is_staff(user, badgeclass):
    return badgeclass.issuer.staff_set.filter(pk=user.pk).exists()

can_issue_badge = is_issuer_owner | is_staff
can_define_new_badgeclass = is_issuer_owner | is_editor

rules.add_perm('issuer.can_issue_badge', can_issue_badge)
rules.add_perm('issuer.can_define_new_badgeclass', can_define_new_badgeclass)


class IsAuthorizedToIssue(permissions.BasePermission):
    """
    Allows those who have been given permission to issue badges on an Issuer to create
    IssuerAssertions from its IssuerBadgeClasses
    """

    def has_object_permission(self, request, view, obj):
        return request.user.has_perm('issuer.can_issue_badge', obj)


class IsAuthorizedToEdit(permissions.BasePermission):
    """
    Allows those who have been given permission to define badges on an Issuer to create
    BadgeClasses from that Issuer.
    For safe methods, staff level permission is fine; for unsafe methods of these view
    classes, editor privileges may be required.
    """

    def has_object_permission(self, request, view, obj):
        if (request.method in SAFE_METHODS):
            return IsAuthorizedToIssue.has_object_permission(request, view, obj)
        else:
            return request.user.has_perm('issuer.can_define_new_badgeclass', obj)
