from django.contrib.admin import ModelAdmin
from mainsite.admin import badgr_admin

from .models import BadgeUser, EmailAddressVariant


class BadgeUserAdmin(ModelAdmin):
    readonly_fields = ('entity_id', 'date_joined', 'last_login', 'username')
    list_display = ('email', 'first_name', 'last_name', 'is_active', 'is_staff', 'entity_id', 'date_joined')
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'date_joined', 'last_login')
    search_fields = ('email', 'first_name', 'last_name', 'username', 'entity_id')
    readonly_fields = ('entity_id',)
    fieldsets = (
        ('Metadata', {'fields': ('entity_id', 'username', 'date_joined',), 'classes': ('collapse',)}),
        (None, {'fields': ('email', 'first_name', 'last_name', )}),
        ('Access', {'fields': ('is_active', 'is_staff', 'is_superuser', 'password')}),
        ('Permissions', {'fields': ('groups', 'user_permissions')}),
    )
    pass

badgr_admin.register(BadgeUser, BadgeUserAdmin)

class EmailAddressVariantAdmin(ModelAdmin):
    search_fields = ('canonical_email', 'email',)
    list_display = ('email', 'canonical_email',)
    raw_id_fields = ('canonical_email',)

badgr_admin.register(EmailAddressVariant, EmailAddressVariantAdmin)