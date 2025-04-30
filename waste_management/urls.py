# waste_management/urls.py

from django.urls import path
from . import views

# Define app_name for namespacing if desired (optional but good practice)
# app_name = 'waste_management'

urlpatterns = [
    # Requestee URLs
    path('requestee/dashboard/', views.requestee_dashboard, name='requestee_dashboard'),
    path('requestee/request/new/', views.create_request_view, name='create_request'),
    path('requestee/request/<int:request_id>/review/', views.approve_request_view, name='approve_request'), # Changed URL slightly

    # Worker URLs
    path('worker/dashboard/', views.worker_dashboard, name='worker_dashboard'),
    path('worker/task/<int:request_id>/complete/', views.complete_task_view, name='complete_task'), # Changed URL slightly

    # Admin URLs
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/request/<int:request_id>/manual_assign/', views.admin_manual_assign_view, name='admin_manual_assign'), # URL for override

    # Note: Authentication URLs are handled at the project level (cleanify_v2/urls.py)
    # Note: Static page URLs (landing, about, contact) are at the project level
    # Note: Dashboard redirect is at the project level
]