from django.contrib.admin import ModelAdmin
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect

from django_object_actions import DjangoObjectActions

from mainsite.admin import badgr_admin

from .models import Issuer, BadgeClass, BadgeInstance


class IssuerAdmin(DjangoObjectActions, ModelAdmin):
    readonly_fields = ('created_at', 'created_by')
    list_display = ('img', 'name', 'slug', 'created_by', 'created_at')
    list_display_links = ('img', 'name')
    list_filter = ('created_at',)
    search_fields = ('name', 'slug')
    fieldsets = (
        ('Metadata', {'fields': ('created_by', 'created_at', 'owner'), 'classes': ("collapse",)}),
        (None, {'fields': ('image', 'name', 'slug')}),
        ('JSON', {'fields': ('json',)}),
    )
    change_actions = ['redirect_badgeclasses']

    def img(self, obj):
        try:
            return u'<img src="{}" width="32"/>'.format(obj.image.url)
        except ValueError:
            return obj.image
    img.short_description = 'Image'
    img.allow_tags = True

    def redirect_badgeclasses(self, request, obj):
        return HttpResponseRedirect(
            reverse('admin:issuer_badgeclass_changelist') + '?issuer__id={}'.format(obj.id)
        )
    redirect_badgeclasses.label = "BadgeClasses"
    redirect_badgeclasses.short_description = "See this issuer's defined BadgeClasses"

badgr_admin.register(Issuer, IssuerAdmin)


class BadgeClassAdmin(DjangoObjectActions, ModelAdmin):
    readonly_fields = ('created_at', 'created_by')
    list_display = ('badge_image', 'name', 'slug', 'issuer_link', 'recipient_count')
    list_display_links = ('badge_image', 'name',)
    list_filter = ('created_at',)
    search_fields = ('name', 'slug', 'issuer__name',)
    fieldsets = (
        ('Metadata', {'fields': ('created_by', 'created_at',), 'classes': ("collapse",)}),
        (None, {'fields': ('image', 'name', 'slug', 'issuer')}),
        ('Criteria', {'fields': ('criteria_text',)}),
        ('JSON', {'fields': ('json',)}),
    )
    change_actions = ['redirect_issuer', 'redirect_instances']

    def badge_image(self, obj):
        return u'<img src="{}" width="32"/>'.format(obj.image.url)
    badge_image.short_description = 'Badge'
    badge_image.allow_tags = True

    def issuer_link(self, obj):
        return '<a href="{}">{}</a>'.format(reverse("admin:issuer_issuer_change", args=(obj.issuer.id,)), obj.issuer.name)
    issuer_link.allow_tags=True

    def redirect_instances(self, request, obj):
        return HttpResponseRedirect(
            reverse('admin:issuer_badgeinstance_changelist') + '?badgeclass__id={}'.format(obj.id)
        )
    redirect_instances.label = "Instances"
    redirect_instances.short_description = "See awarded instances of this BadgeClass"

    def redirect_issuer(self, request, obj):
        return HttpResponseRedirect(
            reverse('admin:issuer_issuer_change', args=(obj.issuer.id,))
        )
    redirect_issuer.label = "Issuer"
    redirect_issuer.short_description = "See this Issuer"

badgr_admin.register(BadgeClass, BadgeClassAdmin)


class BadgeInstanceAdmin(DjangoObjectActions, ModelAdmin):
    readonly_fields = ('created_at', 'created_by', 'image', 'slug')
    list_display = ('badge_image', 'recipient_identifier', 'slug', 'badgeclass', 'issuer')
    list_display_links = ('badge_image', 'recipient_identifier', )
    list_filter = ('created_at',)
    search_fields = ('recipient_identifier', 'slug', 'badgeclass__name', 'issuer__name')
    fieldsets = (
        ('Metadata', {'fields': ('created_by', 'created_at','acceptance'), 'classes': ("collapse",)}),
        (None, {'fields': ('image', 'slug', 'recipient_identifier', 'badgeclass', 'issuer')}),
        ('Revocation', {'fields': ('revoked', 'revocation_reason')}),
        ('JSON', {'fields': ('json',)}),
    )
    change_actions = ['redirect_issuer', 'redirect_badgeclass']

    def badge_image(self, obj):
        try:
            return u'<img src="{}" width="32"/>'.format(obj.image.url)
        except ValueError:
            return obj.image
    badge_image.short_description = 'Badge'
    badge_image.allow_tags = True

    def has_add_permission(self, request):
        return False

    def redirect_badgeclass(self, request, obj):
        return HttpResponseRedirect(
            reverse('admin:issuer_badgeclass_change', args=(obj.badgeclass.id,))
        )
    redirect_badgeclass.label = "BadgeClass"
    redirect_badgeclass.short_description = "See this BadgeClass"

    def redirect_issuer(self, request, obj):
        return HttpResponseRedirect(
            reverse('admin:issuer_issuer_change', args=(obj.issuer.id,))
        )
    redirect_issuer.label = "Issuer"
    redirect_issuer.short_description = "See this Issuer"

badgr_admin.register(BadgeInstance, BadgeInstanceAdmin)
