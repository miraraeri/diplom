from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.text import Truncator

from .models import User, Bids, Components, Types, Devices, Categories, Offices, Departments, Roles


class BidsAdmin(admin.ModelAdmin):
    list_display = ('id', 'short_problem_text', 'employee_bid', 'status', 'time_create', 'time_update', 'accepted_by',
                    'accepted_at', 'completed_by', 'completed_at')
    list_display_links = ('id', 'short_problem_text')
    search_fields = ('short_problem_text', 'employee__lastname', 'employee__firstname', 'employee__middlename',
                     'accepted_by__lastname', 'accepted_by__firstname', 'accepted_by__middlename',
                     'completed_by__lastname', 'completed_by__firstname', 'completed_by__middlename')
    list_filter = ('status', 'time_create', 'time_update', 'accepted_at', 'completed_at')
    list_per_page = 15

    def employee_bid(self, obj):
        return f"{obj.employee.lastname} {obj.employee.firstname} {obj.employee.middlename or ''}"

    employee_bid.short_description = 'Сотрудник'

    def short_problem_text(self, obj):
        return Truncator(obj.problem_text).chars(30)

    short_problem_text.short_description = 'Описание проблемы'


class ComponentsAdmin(admin.ModelAdmin):
    list_display = ('model', 'type', 'counts')
    list_display_links = ('model',)
    search_fields = ('model',)
    list_filter = ('type',)
    list_per_page = 15


class TypesAdmin(admin.ModelAdmin):
    list_display = ('name',)
    list_display_links = ('name',)
    search_fields = ('name',)
    list_per_page = 15


class DevicesAdmin(admin.ModelAdmin):
    list_display = ('number', 'category', 'office')
    list_display_links = ('number',)
    search_fields = ('number',)
    list_filter = ('category', 'office__department')
    list_per_page = 15


class CategoriesAdmin(admin.ModelAdmin):
    list_display = ('name',)
    list_display_links = ('name',)
    search_fields = ('name',)
    list_per_page = 15


class OfficesAdmin(admin.ModelAdmin):
    list_display = ('number', 'department')
    list_display_links = ('number',)
    search_fields = ('number',)
    list_filter = ('department',)
    list_per_page = 15


class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name',)
    list_display_links = ('name',)
    list_per_page = 15


class CustomUserAdmin(UserAdmin):
    list_display = ('contacts', 'lastname', 'firstname', 'middlename', 'role', 'department', 'is_staff')
    search_fields = ('contacts', 'lastname', 'firstname', 'middlename')
    list_filter = ('is_staff', 'is_superuser', 'role', 'department')
    list_per_page = 15

    fieldsets = (
        (None, {'fields': ('contacts', 'password')}),
        ('Личная информация', {'fields': ('lastname', 'firstname', 'middlename', 'role', 'department')}),
        ('Права доступа', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Важные даты', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
            'contacts', 'password1', 'password2', 'lastname', 'firstname', 'middlename', 'role', 'department'),
        }),
    )
    USERNAME_FIELD = 'contacts'
    REQUIRED_FIELDS = ['lastname', 'firstname', 'role', 'department']


admin.site.register(User, CustomUserAdmin)
admin.site.register(Bids, BidsAdmin)
admin.site.register(Components, ComponentsAdmin)
admin.site.register(Types, TypesAdmin)
admin.site.register(Devices, DevicesAdmin)
admin.site.register(Categories, CategoriesAdmin)
admin.site.register(Offices, OfficesAdmin)
admin.site.register(Departments, DepartmentAdmin)
admin.site.site_title = 'Администрирование iloveuchet'
admin.site.site_header = 'Админ-панель сайта iloveuchet'
admin.site.index_title = ''