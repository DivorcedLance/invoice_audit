# config/urls.py
from django.contrib import admin
from django.urls import path
from core.views import dashboard, get_invoice_detail, upload_invoice, get_sample_preview

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', dashboard, name='dashboard'),
    path('upload/', upload_invoice, name='upload'),
    path('preview-sample/', get_sample_preview, name='preview_sample'),
    path('api/invoice/<int:pk>/', get_invoice_detail, name='invoice_detail'),
]