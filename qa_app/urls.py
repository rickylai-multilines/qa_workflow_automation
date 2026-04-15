"""
URL configuration for qa_app
"""
from django.urls import path
from . import views

app_name = 'qa_app'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('products/', views.product_list, name='product_list'),
]

