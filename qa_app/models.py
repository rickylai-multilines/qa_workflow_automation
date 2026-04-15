"""
QA Workflow Models
Based on the updated project plan
"""
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator


class Product(models.Model):
    """Core Product model tracking all QA information"""
    
    # Identity Fields
    bmuk_item_no = models.CharField(max_length=50, unique=True, db_index=True, verbose_name="BMUK Item No.")
    mtl_ref_no = models.CharField(max_length=50, unique=True, db_index=True, verbose_name="MTL Ref NO.")
    prism_code = models.CharField(max_length=50, blank=True, verbose_name="PRISM Code")
    
    # Product Details
    sub_category = models.CharField(max_length=100, verbose_name="Sub Category")
    description = models.TextField(verbose_name="Description")
    product_specification = models.TextField(blank=True, verbose_name="Product Specification")
    care_information = models.TextField(blank=True, verbose_name="Care Information")
    product_image = models.ImageField(upload_to='product_images/', blank=True, null=True, verbose_name="Product Image")
    
    # Classification
    product_category = models.CharField(max_length=100, verbose_name="Product Category / Age Grade")
    material_type = models.CharField(
        max_length=50,
        choices=[
            ('plastic', 'Plastic'),
            ('fabric', 'Fabric'),
            ('cosmetic', 'Cosmetic'),
            ('wood', 'Wood'),
            ('slime', 'Slime'),
            ('paper', 'Paper'),
            ('paint', 'Paint'),
            ('crayon', 'Crayon'),
            ('dough', 'Dough'),
            ('other', 'Other'),
        ],
        verbose_name="Material Type"
    )
    new_repeat_status = models.CharField(
        max_length=100,
        choices=[
            ('repeat', 'Repeat from direct supplier'),
            ('new_item', 'New item# or Direct Import'),
            ('new_supplier', 'Change supplier/manufacturer'),
        ],
        verbose_name="New/Repeat Status"
    )
    
    # Supplier Info
    supplier_code = models.CharField(max_length=50, verbose_name="Supplier Code")
    supplier_name = models.CharField(max_length=200, verbose_name="Supplier Name")
    factory_item_no = models.CharField(max_length=50, blank=True, verbose_name="Factory Item No.")
    bm_fr_item_no = models.CharField(max_length=50, blank=True, verbose_name="BM FR Item No.")
    fob_port = models.CharField(max_length=100, verbose_name="FOB Port")
    
    # Team Assignment
    assigned_user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='owned_qa_products',
        verbose_name="QA In-charge"
    )
    merchandiser_name = models.CharField(max_length=200, verbose_name="Merchandiser")
    
    # Dates
    merchant_enquiry_date = models.DateField(verbose_name="Merchant Enquiry Date")
    shipdate_crd = models.DateField(verbose_name="Shipdate CRD")
    
    # ERP Integration
    order_number = models.CharField(max_length=50, blank=True, db_index=True, verbose_name="Order Number")
    shipment_id = models.CharField(max_length=50, blank=True, verbose_name="Shipment ID")
    
    # Test Requirements (denormalized for easier display)
    test_requirements = models.TextField(blank=True, verbose_name="Test Requirements")
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('draft', 'Draft'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
            ('on_hold', 'On Hold'),
            ('rejected', 'Rejected'),
        ],
        default='draft'
    )
    
    created_date = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.PROTECT, 
        related_name='created_qa_products',
        null=True
    )
    
    class Meta:
        ordering = ['-merchant_enquiry_date']
        indexes = [
            models.Index(fields=['status', 'merchant_enquiry_date']),
            models.Index(fields=['assigned_user', 'status']),
            models.Index(fields=['order_number']),
            models.Index(fields=['mtl_ref_no']),
            models.Index(fields=['bmuk_item_no']),
        ]
        verbose_name = "Product"
        verbose_name_plural = "Products"
    
    def __str__(self):
        return f"{self.bmuk_item_no} - {self.description[:50]}"
    
    def get_current_stage(self):
        """Get the current active stage"""
        stages = self.qa_stages.filter(status='in_progress').order_by('stage_type')
        if stages.exists():
            return stages.first()
        # Return the last completed stage
        completed = self.qa_stages.filter(status='completed').order_by('-completion_date')
        if completed.exists():
            return completed.first()
        # Return the first not started stage
        not_started = self.qa_stages.filter(status='not_started').order_by('stage_type')
        if not_started.exists():
            return not_started.first()
        return None


class ProductStage(models.Model):
    """QA Testing Stages for Products"""
    
    STAGE_CHOICES = [
        ('R', 'Report/Test Plan'),
        ('A', 'Artwork Review'),
        ('F', 'Factory Sample'),
        ('M', 'Mockup/Red Sample'),
        ('G', 'Gold Seal/Shipment Sample'),
    ]
    
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('on_hold', 'On Hold'),
        ('rejected', 'Rejected'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='qa_stages')
    stage_type = models.CharField(max_length=1, choices=STAGE_CHOICES, verbose_name="Stage Type")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')
    
    start_date = models.DateTimeField(null=True, blank=True, verbose_name="Start Date")
    completion_date = models.DateField(null=True, blank=True, verbose_name="Completion Date")
    
    notes = models.TextField(blank=True, verbose_name="Notes")  # For "Artwork Status", inspection notes, etc.
    
    class Meta:
        unique_together = ('product', 'stage_type')
        ordering = ['product', 'stage_type']
        verbose_name = "Product Stage"
        verbose_name_plural = "Product Stages"
    
    def __str__(self):
        return f"{self.product.bmuk_item_no} - {self.get_stage_type_display()}"
    
    @property
    def stage_order(self):
        """Return numeric order for stage (R=1, A=2, F=3, M=4, G=5)"""
        order_map = {'R': 1, 'A': 2, 'F': 3, 'M': 4, 'G': 5}
        return order_map.get(self.stage_type, 0)


class ComplianceDocument(models.Model):
    """Compliance Documents and Test Reports"""
    
    DOC_TYPE_CHOICES = [
        ('test_report', 'Test Report'),
        ('doi', 'Declaration of Innocence (DOI)'),
        ('csa', 'Chemical Safety Assessment (CSA)'),
        ('bom', 'Bill of Materials (BOM)'),
        ('doc', 'Declaration of Compliance (DOC)'),
        ('svhc', 'REACH SVHC Certificate'),
        ('other', 'Other Document'),
    ]
    
    TEST_RESULT_CHOICES = [
        ('ok', 'OK'),
        ('failed', 'Failed'),
        ('pending', 'Pending'),
        ('na', 'N/A'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='compliance_documents')
    document_type = models.CharField(max_length=20, choices=DOC_TYPE_CHOICES, verbose_name="Document Type")
    
    # For Test Reports
    test_name = models.CharField(max_length=200, blank=True, verbose_name="Test Name")  # e.g., "BSEN 71", "Cadmium"
    its_reference = models.CharField(max_length=50, blank=True, verbose_name="ITS Reference")  # Test lab reference
    test_result = models.CharField(
        max_length=20,
        choices=TEST_RESULT_CHOICES,
        blank=True,
        verbose_name="Test Result"
    )
    
    # Key Dates
    test_date = models.DateField(blank=True, null=True, verbose_name="Test Date")
    last_update_date = models.DateField(verbose_name="Last Update Date")  # Date document was issued/updated
    expiry_date = models.DateField(blank=True, null=True, verbose_name="Expiry Date")
    
    # File Storage
    document_file = models.FileField(
        upload_to='compliance_documents/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx', 'xls', 'xlsx', 'jpg', 'png'])],
        verbose_name="Document File"
    )
    uploaded_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name="Uploaded By")
    uploaded_date = models.DateTimeField(auto_now_add=True, verbose_name="Uploaded Date")
    
    # Notes
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    class Meta:
        ordering = ['-last_update_date']
        verbose_name = "Compliance Document"
        verbose_name_plural = "Compliance Documents"
    
    def __str__(self):
        doc_name = self.test_name if self.test_name else self.get_document_type_display()
        return f"{self.product.bmuk_item_no} - {doc_name}"


class TestRequirement(models.Model):
    """Specific test requirements per product/material"""
    
    TEST_NAME_CHOICES = [
        ('bsen71_1', 'BSEN 71-1'),
        ('bsen71_2', 'BSEN 71-2'),
        ('bsen71_3', 'BSEN 71-3'),
        ('cadmium', 'Total Cadmium (REACH Entry 23)'),
        ('phthalates', 'Phthalates (REACH Entry 51 & 52)'),
        ('pahs', 'PAHs (REACH Entry 50)'),
        ('sccp', 'SCCP (POPs regulation)'),
        ('reach_svhc', 'REACH SVHC'),
        ('csa', 'CSA/Risk Assessment'),
        ('other', 'Other Test'),
    ]
    
    STAGE_REQUIREMENT_CHOICES = [
        ('R', 'Report/Test Plan'),
        ('A', 'Artwork Review'),
        ('F', 'Factory Sample'),
        ('M', 'Mockup/Red Sample'),
        ('G', 'Gold Seal/Shipment Sample'),
    ]
    
    TEST_STATUS_CHOICES = [
        ('ok', 'OK'),
        ('awaiting', 'Awaiting'),
        ('pending', 'Pending'),
        ('failed', 'Failed'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='test_requirement_items')
    test_name = models.CharField(max_length=50, choices=TEST_NAME_CHOICES, verbose_name="Test Name")
    requirement_description = models.TextField(blank=True, verbose_name="Requirement Description")
    test_status = models.CharField(
        max_length=20, 
        choices=TEST_STATUS_CHOICES, 
        default='pending',
        verbose_name="Test Status"
    )
    its_reference_number = models.CharField(max_length=50, blank=True, verbose_name="ITS Reference Number")
    test_date = models.DateField(blank=True, null=True, verbose_name="Test Date")
    required_for_stage = models.CharField(
        max_length=1, 
        choices=STAGE_REQUIREMENT_CHOICES, 
        blank=True,
        verbose_name="Required For Stage"
    )
    compliance_notes = models.TextField(blank=True, verbose_name="Compliance Notes")
    
    class Meta:
        ordering = ['product', 'test_name']
        verbose_name = "Test Requirement"
        verbose_name_plural = "Test Requirements"
    
    def __str__(self):
        return f"{self.product.bmuk_item_no} - {self.get_test_name_display()}"


# ERP Integration Models (for FoxPro sync)
class ERPOrder(models.Model):
    """ERP Order data synced from FoxPro"""
    order_number = models.CharField(max_length=50, unique=True, db_index=True)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, related_name='erp_orders')
    crd = models.DateField(null=True, blank=True, verbose_name="CRD")
    etd = models.DateField(null=True, blank=True, verbose_name="ETD")
    eta = models.DateField(null=True, blank=True, verbose_name="ETA")
    last_synced = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "ERP Order"
        verbose_name_plural = "ERP Orders"
    
    def __str__(self):
        return f"Order {self.order_number}"


class ERPShipment(models.Model):
    """ERP Shipment data synced from FoxPro"""
    shipment_id = models.CharField(max_length=50, unique=True, db_index=True)
    order = models.ForeignKey(ERPOrder, on_delete=models.CASCADE, related_name='shipments')
    shipment_status = models.CharField(max_length=50, blank=True)
    last_synced = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "ERP Shipment"
        verbose_name_plural = "ERP Shipments"
    
    def __str__(self):
        return f"Shipment {self.shipment_id}"

