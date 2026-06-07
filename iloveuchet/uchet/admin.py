from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Bids, Components, Types, Devices, Categories, Offices, Departments, Roles


class BidsAdmin(admin.ModelAdmin):
    list_display = ('id', 'problem_text', 'employee_bid', 'status', 'time_create', 'time_update')
    list_display_links = ('id', 'problem_text')
    search_fields = ('problem_text', 'employee__lastname', 'employee__firstname', 'employee__middlename')
    list_filter = ('status', 'time_create', 'time_update')

    def employee_bid(self, obj):
        return f"{obj.employee.lastname} {obj.employee.firstname} {obj.employee.middlename or ''}"

    employee_bid.short_description = 'Сотрудник'


class ComponentsAdmin(admin.ModelAdmin):
    list_display = ('model', 'type', 'counts')
    list_display_links = ('model',)
    search_fields = ('model',)
    list_filter = ('type',)


class TypesAdmin(admin.ModelAdmin):
    list_display = ('name', 'cat_type')
    list_display_links = ('name',)
    search_fields = ('name',)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('categories')

    def cat_type(self, obj):
        return ", ".join([c.name for c in obj.categories.all()])

    cat_type.short_description = 'Категории оборудования'


class DevicesAdmin(admin.ModelAdmin):
    list_display = ('number', 'category', 'office')
    list_display_links = ('number',)
    search_fields = ('number',)
    list_filter = ('category', 'office__department')


class CategoriesAdmin(admin.ModelAdmin):
    list_display = ('name', 'type_cat')
    list_display_links = ('name',)
    search_fields = ('name',)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('types')

    def type_cat(self, obj):
        return ", ".join([t.name for t in obj.types.all()])

    type_cat.short_description = 'Типы комплектующих'


class OfficesAdmin(admin.ModelAdmin):
    list_display = ('number', 'department')
    list_display_links = ('number',)
    search_fields = ('number',)
    list_filter = ('department',)


class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name',)
    list_display_links = ('name',)


class CustomUserAdmin(UserAdmin):
    list_display = ('contacts', 'lastname', 'firstname', 'middlename', 'role', 'department', 'is_staff')
    search_fields = ('contacts', 'lastname', 'firstname', 'middlename')
    list_filter = ('is_staff', 'is_superuser', 'role', 'department')

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