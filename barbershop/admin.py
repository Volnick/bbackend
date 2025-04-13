from django.contrib import admin

# Register your models here.
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    ordering = ['email']  # ✅ oder ein anderes existierendes Feld wie 'first_name'
    list_display = ['email', "username", 'first_name', 'last_name', 'is_staff']

    fieldsets = UserAdmin.fieldsets + (
        ("Zusätzliche Felder", {"fields": ("telefonnummer",)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Zusätzliche Felder", {"fields": ("telefonnummer",)}),
    )

admin.site.register(CustomUser, CustomUserAdmin)