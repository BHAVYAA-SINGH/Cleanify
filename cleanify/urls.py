# cleanify_v2/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
# Import views from app for static pages and auth
from waste_management import views as waste_views

urlpatterns = [
 
    path('admin/', admin.site.urls), 

    
    path('', waste_views.landing_page, name='landing_page'),
    path('about/', waste_views.about_page, name='about_page'),
    path('contact/', waste_views.contact_page, name='contact_page'),

  
    path('signup/', waste_views.signup_view, name='signup'),
    path('login/', waste_views.login_view, name='login'),
    path('logout/', waste_views.logout_view, name='logout'),

  
    path('dashboard-hub/', waste_views.dashboard_redirect_view, name='dashboard_redirect'),

    
    path('app/', include('waste_management.urls')), 

]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)  

