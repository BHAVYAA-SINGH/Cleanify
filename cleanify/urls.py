# cleanify_v2/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
# Import views from app for static pages and auth
from waste_management import views as waste_views

urlpatterns = [
    # Admin Site
    path('admin/', admin.site.urls), # Changed admin URL slightly

    # Static Pages handled by app views
    path('', waste_views.landing_page, name='landing_page'),
    path('about/', waste_views.about_page, name='about_page'),
    path('contact/', waste_views.contact_page, name='contact_page'),

    # Authentication URLs handled by app views
    path('signup/', waste_views.signup_view, name='signup'),
    path('login/', waste_views.login_view, name='login'),
    path('logout/', waste_views.logout_view, name='logout'),

    # Dashboard Redirect URL (used after login)
    path('dashboard-hub/', waste_views.dashboard_redirect_view, name='dashboard_redirect'),

    # Include App-Specific URLs (prefixed with 'app/')
    path('app/', include('waste_management.urls')), # Include app urls

]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) # Serve static files via Django in DEBUG

# --- Custom Error Handlers --- (Optional)
# Uncomment these lines and make sure the corresponding views exist in waste_management/views.py
# handler404 = 'waste_management.views.custom_404'
# handler500 = 'waste_management.views.custom_500'
# handler403 = 'waste_management.views.custom_403' # Create this view if needed
# handler400 = 'waste_management.views.custom_400' # Create this view if needed