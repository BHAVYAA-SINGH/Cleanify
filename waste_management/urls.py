

from django.urls import path
from . import views

urlpatterns = [
    path('requestee/dashboard/', views.requestee_dashboard, name='requestee_dashboard'),
    path('requestee/request/new/', views.create_request_view, name='create_request'),
    path('requestee/request/<int:request_id>/review/', views.approve_request_view, name='approve_request'),

    path('worker/dashboard/', views.worker_dashboard, name='worker_dashboard'),
    path('worker/task/<int:request_id>/complete/', views.complete_task_view, name='complete_task'), 

    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/request/<int:request_id>/manual_assign/', views.admin_manual_assign_view, name='admin_manual_assign'),
]
