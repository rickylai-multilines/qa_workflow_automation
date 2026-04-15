"""
Django Admin configuration for QA Workflow models
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import Product, ProductStage, ComplianceDocument, TestRequirement, ERPOrder, ERPShipment


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'bmuk_item_no', 
        'mtl_ref_no', 
        'description_short', 
        'material_type', 
        'status', 
        'assigned_user',
        'merchant_enquiry_date',
        'current_stage_display'
    ]
    list_filter = [
        'status', 
        'material_type', 
        'product_category', 
        'new_repeat_status',
        'assigned_user',
        'merchant_enquiry_date'
    ]
    search_fields = [
        'bmuk_item_no', 
        'mtl_ref_no', 
        'description', 
        'supplier_name',
        'supplier_code',
        'order_number'
    ]
    readonly_fields = ['created_date', 'created_by']
    fieldsets = (
        ('Identity', {
            'fields': ('bmuk_item_no', 'mtl_ref_no', 'prism_code', 'product_image')
        }),
        ('Product Details', {
            'fields': (
                'sub_category', 
                'description', 
                'product_specification', 
                'care_information'
            )
        }),
        ('Classification', {
            'fields': (
                'product_category', 
                'material_type', 
                'new_repeat_status'
            )
        }),
        ('Supplier Information', {
            'fields': (
                'supplier_code', 
                'supplier_name', 
                'factory_item_no', 
                'bm_fr_item_no',
                'fob_port'
            )
        }),
        ('Team Assignment', {
            'fields': ('assigned_user', 'merchandiser_name')
        }),
        ('Timeline', {
            'fields': ('merchant_enquiry_date', 'shipdate_crd')
        }),
        ('ERP Integration', {
            'fields': ('order_number', 'shipment_id')
        }),
        ('Test Requirements', {
            'fields': ('test_requirements',)
        }),
        ('Status', {
            'fields': ('status', 'created_date', 'created_by')
        }),
    )
    
    def description_short(self, obj):
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
    description_short.short_description = 'Description'
    
    def current_stage_display(self, obj):
        stage = obj.get_current_stage()
        if stage:
            status_colors = {
                'not_started': 'gray',
                'in_progress': 'orange',
                'completed': 'green',
                'on_hold': 'red',
                'rejected': 'darkred'
            }
            color = status_colors.get(stage.status, 'black')
            return format_html(
                '<span style="color: {};">{}</span>',
                color,
                f"{stage.get_stage_type_display()} - {stage.get_status_display()}"
            )
        return '-'
    current_stage_display.short_description = 'Current Stage'
    
    def save_model(self, request, obj, form, change):
        if not change:  # New object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


class ProductStageInline(admin.TabularInline):
    model = ProductStage
    extra = 0
    readonly_fields = ['start_date']
    fields = ['stage_type', 'status', 'start_date', 'completion_date', 'notes']


class ComplianceDocumentInline(admin.TabularInline):
    model = ComplianceDocument
    extra = 0
    readonly_fields = ['uploaded_date', 'uploaded_by']
    fields = [
        'document_type', 
        'test_name', 
        'its_reference', 
        'test_result',
        'last_update_date',
        'document_file',
        'uploaded_by',
        'uploaded_date'
    ]


class TestRequirementInline(admin.TabularInline):
    model = TestRequirement
    extra = 0
    fields = [
        'test_name', 
        'test_status', 
        'its_reference_number', 
        'test_date',
        'required_for_stage',
        'compliance_notes'
    ]


@admin.register(ProductStage)
class ProductStageAdmin(admin.ModelAdmin):
    list_display = [
        'product', 
        'stage_type', 
        'status', 
        'start_date', 
        'completion_date'
    ]
    list_filter = ['stage_type', 'status', 'completion_date']
    search_fields = ['product__bmuk_item_no', 'product__description', 'notes']
    readonly_fields = ['start_date']
    
    fieldsets = (
        ('Product & Stage', {
            'fields': ('product', 'stage_type')
        }),
        ('Status & Dates', {
            'fields': ('status', 'start_date', 'completion_date')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
    )


@admin.register(ComplianceDocument)
class ComplianceDocumentAdmin(admin.ModelAdmin):
    list_display = [
        'product', 
        'document_type', 
        'test_name', 
        'its_reference',
        'test_result',
        'last_update_date',
        'uploaded_by'
    ]
    list_filter = [
        'document_type', 
        'test_result', 
        'last_update_date',
        'uploaded_by'
    ]
    search_fields = [
        'product__bmuk_item_no', 
        'its_reference', 
        'test_name'
    ]
    readonly_fields = ['uploaded_date', 'uploaded_by']
    
    fieldsets = (
        ('Product & Document', {
            'fields': ('product', 'document_type')
        }),
        ('Test Information', {
            'fields': (
                'test_name', 
                'its_reference', 
                'test_result',
                'test_date'
            )
        }),
        ('Dates', {
            'fields': ('last_update_date', 'expiry_date')
        }),
        ('File', {
            'fields': ('document_file', 'uploaded_by', 'uploaded_date')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # New object
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(TestRequirement)
class TestRequirementAdmin(admin.ModelAdmin):
    list_display = [
        'product', 
        'test_name', 
        'test_status', 
        'its_reference_number',
        'test_date',
        'required_for_stage'
    ]
    list_filter = [
        'test_name', 
        'test_status', 
        'required_for_stage'
    ]
    search_fields = [
        'product__bmuk_item_no', 
        'its_reference_number',
        'requirement_description'
    ]


@admin.register(ERPOrder)
class ERPOrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'product', 'crd', 'etd', 'eta', 'last_synced']
    list_filter = ['last_synced']
    search_fields = ['order_number', 'product__bmuk_item_no']


@admin.register(ERPShipment)
class ERPShipmentAdmin(admin.ModelAdmin):
    list_display = ['shipment_id', 'order', 'shipment_status', 'last_synced']
    list_filter = ['shipment_status', 'last_synced']
    search_fields = ['shipment_id', 'order__order_number']


# Update ProductAdmin to include inlines
ProductAdmin.inlines = [ProductStageInline, ComplianceDocumentInline, TestRequirementInline]

