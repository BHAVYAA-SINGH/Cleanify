
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin 
from django.contrib.auth.models import User, Group

from .models import UserProfile, WasteRequest 

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False 
    verbose_name_plural = 'User Profile Details'
    fk_name = 'user' 

    fields = ('role', 'category', 'is_busy', 'average_rating')
 
    readonly_fields = ('average_rating',)

    def get_formset(self, request, obj=None, **kwargs):
        """
        Customize the fields displayed in the inline based on the UserProfile's role.
        """
        formset = super().get_formset(request, obj, **kwargs)
      
        if obj and hasattr(obj, 'profile'):
            profile = obj.profile
            if profile.role != 'Worker':
               
                pass
        return formset

    def get_readonly_fields(self, request, obj=None):
        """
        Make 'category' and 'is_busy' readonly if the role is not 'Worker'.
        'average_rating' is always readonly.
        """
        readonly = ['average_rating']
        if obj and hasattr(obj, 'profile') and obj.profile.role != 'Worker':
            readonly.extend(['category', 'is_busy'])
        return readonly



class CustomUserAdmin(BaseUserAdmin):
  
    inlines = (UserProfileInline,)
    
    list_display = (
        'username', 'email', 'first_name', 'last_name', 'is_staff',
        'get_user_role', 'get_worker_category', 'get_worker_is_busy', 'get_worker_average_rating'
    )
    list_select_related = ('profile',)
    list_filter = BaseUserAdmin.list_filter + ('profile__role', 'profile__category') 
   
    def get_user_role(self, instance):
        if hasattr(instance, 'profile'):
            return instance.profile.get_role_display() 
        return None
    get_user_role.short_description = 'Role' 

    def get_worker_category(self, instance):
        if hasattr(instance, 'profile') and instance.profile.role == 'Worker':
            return instance.profile.get_category_display()
        return "---" 
    get_worker_category.short_description = 'Worker Category'

    def get_worker_is_busy(self, instance):
        if hasattr(instance, 'profile') and instance.profile.role == 'Worker':
            return instance.profile.is_busy
        return "---"
    get_worker_is_busy.short_description = 'Is Busy?'
    get_worker_is_busy.boolean = True

    def get_worker_average_rating(self, instance):
        if hasattr(instance, 'profile') and instance.profile.role == 'Worker' and instance.profile.average_rating is not None:
            return f"{instance.profile.average_rating:.2f}"
        return "---"
    get_worker_average_rating.short_description = 'Avg. Rating'

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
 
        user_instance = form.instance
        if hasattr(user_instance, 'profile') and user_instance.profile.role == 'Worker':
            user_instance.profile.update_busy_status()
            user_instance.profile.update_average_rating() 



@admin.register(WasteRequest) 
class WasteRequestAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'requestee_link', 'category', 'location', 'status',
        'assigned_worker_link', 'worker_rating_display', 'is_approved_by_student',
        'created_at', 'updated_at'
    )
    list_filter = ('status', 'category', 'is_approved_by_student', 'created_at', 'worker_rating')
    search_fields = (
        'location', 'description', 'requestee__username',
        'assigned_worker__username', 'category'
    )
  
    readonly_fields = (
        'created_at', 'updated_at', 'assigned_at', 'approved_at',

    )

    list_display_links = ('id', 'location')
    list_per_page = 25 
    ordering = ('-created_at',) 

    def requestee_link(self, obj):
        from django.urls import reverse
        from django.utils.html import format_html
        if obj.requestee:
            link = reverse("admin:auth_user_change", args=[obj.requestee.id])
            return format_html('<a href="{}">{}</a>', link, obj.requestee.username)
        return "-"
    requestee_link.short_description = 'Requestee'
    requestee_link.admin_order_field = 'requestee__username'


    def assigned_worker_link(self, obj):
        from django.urls import reverse
        from django.utils.html import format_html
        if obj.assigned_worker:
            link = reverse("admin:auth_user_change", args=[obj.assigned_worker.id])
            return format_html('<a href="{}">{}</a>', link, obj.assigned_worker.username)
        return "-"
    assigned_worker_link.short_description = 'Assigned Worker'
    assigned_worker_link.admin_order_field = 'assigned_worker__username'

    def worker_rating_display(self, obj):
        return obj.get_worker_rating_display() if obj.worker_rating else "Not Rated"
    worker_rating_display.short_description = 'Rating Given'
    worker_rating_display.admin_order_field = 'worker_rating'

try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass
admin.site.register(User, CustomUserAdmin)
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'category', 'is_busy', 'average_rating')
    list_filter = ('role', 'category', 'is_busy')
    search_fields = ('user__username', 'category')
    readonly_fields = ('average_rating',) 

    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.role == 'Worker':
            obj.update_busy_status()
            obj.update_average_rating()
