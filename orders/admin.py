from django.contrib import admin

from .models import (
    Order,
    WorkflowTemplate,
    WorkflowStage,
    OrderTask,
    UserDashboardPreference,
    SOMain,
    SODetail,
    Product,
    PaymentTerm,
    Customer,
    FoxUser,
    Supplier,
    Department,
    UserProfile,
    WorkflowGridTemplate,
    WorkflowGridColumn,
    WorkflowGridEntry,
    WipTypeDefinition,
    WipCheckpointDefinition,
    WipOrder,
    WipTask,
)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'customer', 'cargo_ready_date', 'created_at')
    list_filter = ('created_at', 'cargo_ready_date', 'supplier')
    search_fields = ('order_number', 'customer', 'supplier')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'customer', 'supplier', 'cargo_ready_date'),
        }),
        ('Item Details', {
            'fields': ('gm_order_no', 'bm_item_no', 'product_description', 'order_qty'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


class WorkflowTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_by', 'is_default', 'is_active')
    list_filter = ('is_active', 'is_default', 'created_at')
    search_fields = ('name',)


@admin.register(WorkflowStage)
class WorkflowStageAdmin(admin.ModelAdmin):
    list_display = ('template', 'stage_name', 'stage_order', 'days_before_crd')
    list_filter = ('template', 'is_optional')
    ordering = ('template', 'stage_order')


@admin.register(OrderTask)
class OrderTaskAdmin(admin.ModelAdmin):
    list_display = ('order', 'stage', 'planned_date', 'status', 'alert_status', 'assigned_to')
    list_filter = ('status', 'alert_status', 'planned_date', 'created_at')
    search_fields = ('order__order_number', 'assigned_to__username')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Task Information', {
            'fields': ('order', 'stage', 'assigned_to'),
        }),
        ('Dates', {
            'fields': ('planned_date', 'actual_date'),
        }),
        ('Status', {
            'fields': ('status', 'alert_status'),
        }),
        ('Notes', {
            'fields': ('notes',),
        }),
        ('Tracking', {
            'fields': ('created_at', 'updated_at', 'last_alert_sent'),
            'classes': ('collapse',),
        }),
    )


@admin.register(UserDashboardPreference)
class UserDashboardPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'daily_email_enabled', 'daily_email_time')
    list_filter = ('daily_email_enabled', 'send_warning_alerts', 'send_critical_alerts')
    search_fields = ('user__username', 'user__email')


@admin.register(SOMain)
class SOMainAdmin(admin.ModelAdmin):
    list_display = ('sc_number', 'sc_date', 'salesman', 'cu_code', 'crd')
    search_fields = ('sc_number', 'cu_code', 'salesman', 'cust_order')
    list_filter = ('company', 'department_no')


@admin.register(SODetail)
class SODetailAdmin(admin.ModelAdmin):
    list_display = ('sc_number', 'po_number', 'product_id', 'qty', 'unit_price', 'mod_time', 'mod_by')
    search_fields = ('sc_number', 'po_number', 'product_id', 'barcode', 'cust_item_code')
    list_filter = ('supplier_id', 'customer_id', 'posted')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('product_id', 'product_name', 'supplier_id', 'unit_price', 'inactive')
    search_fields = ('product_id', 'product_name', 'barcode', 'customer_item_code', 'supplier_item_code')
    list_filter = ('supplier_id', 'brand', 'inactive')


@admin.register(PaymentTerm)
class PaymentTermAdmin(admin.ModelAdmin):
    list_display = ('term_code', 'description', 'due_day', 'discount', 'status')
    search_fields = ('term_code', 'description', 'status')
    list_filter = ('status',)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('customer_id', 'customer_code', 'customer_name', 'salesman', 'status')
    search_fields = ('customer_id', 'customer_code', 'customer_name', 'email', 'tel')
    list_filter = ('status', 'trade_term')


@admin.register(FoxUser)
class FoxUserAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'user_name', 'department_id', 'mod_time')
    search_fields = ('user_id', 'user_name', 'department_id')
    list_filter = ('department_id',)


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('supplier_code', 'supplier_name', 'status', 'contact_person', 'tel', 'country')
    search_fields = ('supplier_code', 'supplier_name', 'status', 'contact_person', 'email')
    list_filter = ('status', 'country')


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')
    search_fields = ('code', 'name')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'department', 'is_supervisor')
    list_filter = ('department', 'is_supervisor')
    search_fields = ('user__username', 'user__email')


@admin.register(WorkflowGridTemplate)
class WorkflowGridTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active')
    search_fields = ('name', 'slug')


@admin.register(WorkflowGridColumn)
class WorkflowGridColumnAdmin(admin.ModelAdmin):
    list_display = ('template', 'order', 'label', 'group_label', 'data_type')
    list_filter = ('template', 'data_type')
    search_fields = ('label', 'group_label')
    ordering = ('template', 'order')


@admin.register(WorkflowGridEntry)
class WorkflowGridEntryAdmin(admin.ModelAdmin):
    list_display = ('template', 'order_detail', 'assigned_user', 'department', 'updated_at')
    list_filter = ('template', 'department')
    search_fields = ('order_detail__sc_number', 'order_detail__product_id')


try:
    admin.site.register(WorkflowTemplate, WorkflowTemplateAdmin)
except admin.sites.AlreadyRegistered:
    pass


@admin.register(WipTypeDefinition)
class WipTypeDefinitionAdmin(admin.ModelAdmin):
    list_display = ('name', 'department', 'lead_time_min', 'lead_time_max', 'is_active')
    list_filter = ('department', 'is_active')
    search_fields = ('name',)


@admin.register(WipCheckpointDefinition)
class WipCheckpointDefinitionAdmin(admin.ModelAdmin):
    list_display = ('wip_type', 'order', 'label', 'rule_type', 'offset_days')
    list_filter = ('wip_type', 'rule_type')
    ordering = ('wip_type', 'order')


@admin.register(WipOrder)
class WipOrderAdmin(admin.ModelAdmin):
    list_display = ('sodetail', 'department', 'assigned_user', 'wip_type', 'lead_time_days', 'status')
    list_filter = ('department', 'status')
    search_fields = ('sodetail__sc_number', 'sodetail__product_id')
    list_select_related = ('sodetail', 'somain', 'department', 'assigned_user', 'wip_type')
    raw_id_fields = ('somain', 'sodetail', 'assigned_user')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('somain', 'sodetail', 'department', 'assigned_user', 'wip_type')


@admin.register(WipTask)
class WipTaskAdmin(admin.ModelAdmin):
    list_display = (
        'wip_order',
        'checkpoint',
        'planned_date',
        'action_date',
        'kpi_days',
        'status',
        'inspection_by',
        'inspection_result',
    )
    list_filter = ('status', 'inspection_by', 'inspection_result')
    list_select_related = ('wip_order', 'wip_order__sodetail', 'checkpoint')
    raw_id_fields = ('wip_order', 'checkpoint')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            'wip_order',
            'wip_order__sodetail',
            'wip_order__somain',
            'wip_order__department',
            'wip_order__assigned_user',
            'wip_order__wip_type',
            'checkpoint',
            'checkpoint__wip_type',
        )
