"""
Accounts admin.
Staff access stays on Django's is_staff flag. Public capabilities are listed separately.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import AccountCapability, User


class AccountCapabilityInline(admin.TabularInline):
    model = AccountCapability
    extra = 0


@admin.register(User)
class KaamDoUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('KaamDo account', {'fields': ('phone_number', 'active_mode')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('KaamDo account', {'fields': ('phone_number', 'active_mode')}),
    )
    inlines = [AccountCapabilityInline]
    list_display = ('username', 'phone_number', 'active_mode', 'email', 'is_staff')
    search_fields = UserAdmin.search_fields + ('phone_number',)
    list_filter = UserAdmin.list_filter + ('active_mode',)
