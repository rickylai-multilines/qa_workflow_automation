from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = 'orders'

urlpatterns = [
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('orders/', views.OrderListView.as_view(), name='order-list'),
    path('orders/<str:sc_number>/', views.OrderDetailView.as_view(), name='order-detail'),
    path('products/', views.ProductListView.as_view(), name='product-list'),
    path('products/detail/<path:product_id>/', views.ProductDetailView.as_view(), name='product-detail'),
    path('sc-product-list/', views.SCProductListView.as_view(), name='sc-product-list'),
    path('product-image/<str:product_id>/', views.product_image, name='product-image'),
    path('task/<int:task_id>/update/', views.UpdateTaskStatusView.as_view(), name='update-task'),
    path('preferences/', views.UserPreferencesView.as_view(), name='preferences'),
    path('workflow/<slug:slug>/', views.WorkflowListView.as_view(), name='workflow-list'),
    path('workflow/entry/<int:entry_id>/', views.WorkflowEntryEditView.as_view(), name='workflow-edit'),
    path('wip/', views.WipDashboardView.as_view(), name='wip-dashboard'),
    path('wip/order/<int:order_id>/', views.WipOrderEditView.as_view(), name='wip-edit'),
    path('wip/task/<int:task_id>/', views.WipTaskEditView.as_view(), name='wip-task-edit'),
    path('wip/manage/', views.WipAdminView.as_view(), name='wip-admin'),
]
