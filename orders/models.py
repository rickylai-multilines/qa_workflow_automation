from datetime import date

from django.contrib.auth.models import User
from django.db import models
from django.utils.text import slugify


class Order(models.Model):
    """Main order model - stores order information with CRD."""

    order_number = models.CharField(max_length=100, unique=True, db_index=True)
    customer = models.CharField(max_length=200)
    supplier = models.CharField(max_length=200)
    cargo_ready_date = models.DateField(db_index=True)

    gm_order_no = models.CharField(max_length=100, blank=True)
    bm_item_no = models.CharField(max_length=100, blank=True)
    product_description = models.TextField()
    order_qty = models.IntegerField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['cargo_ready_date']),
        ]

    def __str__(self) -> str:
        return f"{self.order_number} - {self.customer}"

    @property
    def completion_percentage(self) -> int:
        """Calculate order completion percentage."""
        total_tasks = self.tasks.count()
        if total_tasks == 0:
            return 0
        completed = self.tasks.filter(status='completed').count()
        return int((completed / total_tasks) * 100)

    @property
    def has_overdue_tasks(self) -> bool:
        """Check if order has any overdue tasks."""
        return self.tasks.filter(
            status__in=['pending', 'in_progress'],
            planned_date__lt=date.today(),
        ).exists()

    @property
    def next_milestone_days(self):
        """Days until next task deadline."""
        next_task = self.tasks.filter(
            status__in=['pending', 'in_progress'],
        ).order_by('planned_date').first()
        if next_task:
            return (next_task.planned_date - date.today()).days
        return None


class WorkflowTemplate(models.Model):
    """Customizable workflow template for different order types."""

    name = models.CharField(max_length=200)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


class WorkflowStage(models.Model):
    """Individual stages within a workflow."""

    template = models.ForeignKey(
        WorkflowTemplate,
        on_delete=models.CASCADE,
        related_name='stages',
    )
    stage_name = models.CharField(max_length=200)
    stage_order = models.IntegerField()
    days_before_crd = models.IntegerField(
        default=60,
        help_text="Number of days before CRD this task should be completed",
    )
    is_optional = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['stage_order']
        unique_together = ('template', 'stage_order')
        indexes = [
            models.Index(fields=['template', 'stage_order']),
        ]

    def __str__(self) -> str:
        return f"{self.template.name} - {self.stage_name}"


class OrderTask(models.Model):
    """Task for each order stage - tracks workflow progress."""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('skipped', 'Skipped'),
    ]

    ALERT_STATUS_CHOICES = [
        ('normal', 'Normal'),
        ('warning', 'Warning (7 days)'),
        ('critical', 'Critical (Overdue)'),
    ]

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='tasks',
    )
    stage = models.ForeignKey(
        WorkflowStage,
        on_delete=models.SET_NULL,
        null=True,
    )

    planned_date = models.DateField(db_index=True)
    actual_date = models.DateField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True,
    )
    alert_status = models.CharField(
        max_length=20,
        choices=ALERT_STATUS_CHOICES,
        default='normal',
        db_index=True,
    )

    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks',
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_alert_sent = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['planned_date']
        indexes = [
            models.Index(fields=['order', 'status']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['alert_status']),
            models.Index(fields=['planned_date']),
        ]

    def __str__(self) -> str:
        stage_name = self.stage.stage_name if self.stage else "Unassigned Stage"
        return f"{self.order.order_number} - {stage_name}"

    def days_until_due(self) -> int:
        """Calculate days remaining until planned date."""
        return (self.planned_date - date.today()).days

    def is_overdue(self) -> bool:
        """Check if task is overdue."""
        return self.status != 'completed' and date.today() > self.planned_date

    def should_alert(self) -> bool:
        """Determine if alert should be sent."""
        if self.status in ['completed', 'skipped']:
            return False

        days_left = self.days_until_due()

        if self.is_overdue():
            return True
        if 0 <= days_left <= 7:
            return True

        return False

    def update_alert_status(self) -> None:
        """Update alert status based on current situation."""
        if self.status in ['completed', 'skipped']:
            self.alert_status = 'normal'
        elif self.is_overdue():
            self.alert_status = 'critical'
        elif 0 <= self.days_until_due() <= 7:
            self.alert_status = 'warning'
        else:
            self.alert_status = 'normal'

        self.save(update_fields=['alert_status', 'updated_at'])


class UserDashboardPreference(models.Model):
    """User preferences for dashboard and notifications."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='dashboard_preference',
    )

    daily_email_enabled = models.BooleanField(default=True)
    daily_email_time = models.TimeField(default='09:00')
    send_warning_alerts = models.BooleanField(default=True)
    send_critical_alerts = models.BooleanField(default=True)

    show_completed_tasks = models.BooleanField(default=False)
    default_view = models.CharField(
        max_length=20,
        choices=[
            ('my_tasks', 'My Tasks'),
            ('all_orders', 'All Orders'),
            ('team', 'Team View'),
        ],
        default='my_tasks',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.user.username} - Dashboard Preferences"


class Department(models.Model):
    """Department for access control."""

    code = models.CharField(max_length=10, unique=True, db_column='DepartmentId')
    name = models.CharField(max_length=100, null=True, blank=True, db_column='DepartmentName')

    class Meta:
        db_table = 'Department'

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class UserProfile(models.Model):
    """User profile with department and role."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='orders_profile')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    is_supervisor = models.BooleanField(default=False)

    def __str__(self) -> str:
        role = "Supervisor" if self.is_supervisor else "User"
        return f"{self.user.username} ({role})"


class SOMain(models.Model):
    """PostgreSQL copy of FoxPro SOMAST (sales order header)."""

    sc_number = models.CharField(max_length=20, unique=True, db_column='SCNumber')
    sc_status = models.CharField(max_length=20, null=True, blank=True, db_column='SCStatus')
    created_by = models.CharField(max_length=20, null=True, blank=True, db_column='CreatedBy')
    sc_date = models.DateTimeField(null=True, blank=True, db_column='SCDate')
    salesman = models.CharField(max_length=50, null=True, blank=True, db_column='Salesman')
    cu_code = models.CharField(max_length=20, null=True, blank=True, db_column='CuCode')
    ship_via = models.CharField(max_length=60, null=True, blank=True, db_column='ShipVia')
    crd = models.DateTimeField(null=True, blank=True, db_column='CRD')
    port_of_load = models.CharField(max_length=20, null=True, blank=True, db_column='PortofLoad')
    origin = models.CharField(max_length=20, null=True, blank=True, db_column='Origin')
    ship_to = models.CharField(max_length=20, null=True, blank=True, db_column='ShipTo')
    port_of_disch = models.CharField(max_length=60, null=True, blank=True, db_column='PortofDisch')
    cust_order = models.CharField(max_length=60, null=True, blank=True, db_column='CustOrder')
    order_date = models.DateTimeField(null=True, blank=True, db_column='OrderDate')
    payment_term_code = models.CharField(max_length=20, null=True, blank=True, db_column='PaymrntTermCode')
    net_total_amt = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True, db_column='NetTotalAmt')
    doc_net_total_amt = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True, db_column='DocNetTotalAmt')
    gross_total_amt = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True, db_column='GrossTotalAmt')
    remark = models.TextField(null=True, blank=True, db_column='Remark')
    last_po_no = models.CharField(max_length=20, null=True, blank=True, db_column='LastPONo')
    container_qty = models.CharField(max_length=40, null=True, blank=True, db_column='ContainerQty')
    container_size = models.CharField(max_length=40, null=True, blank=True, db_column='ContainerSize')
    mod_time = models.DateTimeField(null=True, blank=True, db_column='ModTime')
    posted = models.BooleanField(null=True, blank=True, db_column='Posted')
    department_no = models.CharField(max_length=10, null=True, blank=True, db_column='DepartmentNo')
    trade_term = models.CharField(max_length=20, null=True, blank=True, db_column='TradeTerm')
    company = models.CharField(max_length=20, null=True, blank=True, db_column='Company')
    total_qty = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True, db_column='TotalQty')
    total_cbm = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True, db_column='TotalCBM')
    total_gross_wt = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True, db_column='TotalGrossWt')
    user_id = models.CharField(max_length=20, null=True, blank=True, db_column='UserID')

    class Meta:
        db_table = 'SOMAIN'
        indexes = [
            models.Index(fields=['sc_number']),
            models.Index(fields=['sc_date']),
            models.Index(fields=['crd']),
        ]

    def __str__(self) -> str:
        return self.sc_number


class SODetail(models.Model):
    """PostgreSQL copy of FoxPro SODTL (sales order detail)."""

    sc_number = models.CharField(max_length=20, db_column='SCNumber')
    po_number = models.CharField(max_length=20, null=True, blank=True, db_column='PONumber')
    product_id = models.CharField(max_length=50, null=True, blank=True, db_column='ProductId')
    barcode = models.CharField(max_length=50, null=True, blank=True, db_column='Barcode')
    cust_item_code = models.CharField(max_length=50, null=True, blank=True, db_column='CustItemCode')
    qty = models.IntegerField(null=True, blank=True, db_column='Qty')
    carton_unit = models.CharField(max_length=20, null=True, blank=True, db_column='CartonUnit')
    unit_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True, db_column='UnitPrice')
    supplier_id = models.CharField(max_length=20, null=True, blank=True, db_column='SupplierId')
    customer_id = models.CharField(max_length=20, null=True, blank=True, db_column='CustomerId')
    product_name = models.CharField(max_length=100, null=True, blank=True, db_column='ProductName')
    seq = models.DecimalField(max_digits=10, decimal_places=5, null=True, blank=True, db_column='Seq')
    item_description = models.TextField(null=True, blank=True, db_column='ItemDescription')
    mod_time = models.DateTimeField(null=True, blank=True, db_column='ModTime')
    mod_by = models.CharField(max_length=20, null=True, blank=True, db_column='ModBy')
    marks = models.TextField(null=True, blank=True, db_column='Marks')
    supplier_item_code = models.CharField(max_length=30, null=True, blank=True, db_column='SupplierItemCode')
    bmi_item_code = models.CharField(max_length=30, null=True, blank=True, db_column='BMIItemCode')
    french_item_code = models.CharField(max_length=30, null=True, blank=True, db_column='FrenchItemCode')
    last_mod_time = models.DateTimeField(null=True, blank=True, db_column='LastModTime')
    net_wt = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True, db_column='NetWt')
    gross_wt = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True, db_column='GrossWt')
    posted = models.BooleanField(null=True, blank=True, db_column='Posted')
    qty_per_carton = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True, db_column='QtyPerCarton')
    carton_pack_unit = models.CharField(max_length=20, null=True, blank=True, db_column='CartonPackUnit')
    length = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True, db_column='Length')
    hight = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True, db_column='Hight')
    width = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True, db_column='Width')
    measure_unit = models.CharField(max_length=20, null=True, blank=True, db_column='MeasureUnit')
    packing = models.CharField(max_length=120, null=True, blank=True, db_column='Packing')
    cbm = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True, db_column='Cbm')
    cuf = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True, db_column='Cuf')
    no_of_carton = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True, db_column='NoOfCarton')
    haos_code = models.CharField(max_length=20, null=True, blank=True, db_column='HAOSCode')
    brand = models.CharField(max_length=50, null=True, blank=True, db_column='Brand')

    class Meta:
        db_table = 'SODETAIL'
        indexes = [
            models.Index(fields=['sc_number']),
            models.Index(fields=['po_number']),
            models.Index(fields=['product_id']),
        ]
        unique_together = ('sc_number', 'po_number', 'product_id')

    def __str__(self) -> str:
        return f"{self.sc_number} - {self.product_id}"


class Product(models.Model):
    """PostgreSQL copy of FoxPro PRODUCTS."""

    product_id = models.CharField(max_length=30, unique=True, db_column='ProductId')
    barcode = models.TextField(null=True, blank=True, db_column='Barcode')
    customer_item_code = models.CharField(max_length=30, null=True, blank=True, db_column='CustomerItemCode')
    supplier_item_code = models.CharField(max_length=30, null=True, blank=True, db_column='SupplierItemCode')
    department_no = models.CharField(max_length=10, null=True, blank=True, db_column='DepartmentNo')
    packing = models.CharField(max_length=100, null=True, blank=True, db_column='Packing')
    material = models.CharField(max_length=100, null=True, blank=True, db_column='Material')
    brand = models.CharField(max_length=100, null=True, blank=True, db_column='Brand')
    supplier_id = models.CharField(max_length=10, null=True, blank=True, db_column='SupplierId')
    copy_from_product_id = models.CharField(max_length=50, null=True, blank=True, db_column='CopyFromProductId')
    french_item_code = models.CharField(max_length=30, null=True, blank=True, db_column='FrenchItemCode')
    german_item_code = models.CharField(max_length=30, null=True, blank=True, db_column='GermanItemCode')
    product_name = models.CharField(max_length=100, null=True, blank=True, db_column='ProductName')
    unit_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True, db_column='UnitPrice')
    unit_price1 = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True, db_column='UnitPrice1')
    unit_price2 = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True, db_column='UnitPrice2')
    unit_cost = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True, db_column='UnitCost')
    qty_per_carton = models.IntegerField(null=True, blank=True, db_column='QtyPerCarton')
    carton_unit = models.CharField(max_length=10, null=True, blank=True, db_column='CartonUnit')
    per_carton_unit = models.CharField(max_length=10, null=True, blank=True, db_column='PerCartonUnit')
    per_carton_qty = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True, db_column='PerCartonQty')
    length = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True, db_column='Length')
    hight = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True, db_column='Hight')
    width = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True, db_column='Width')
    measure_unit = models.CharField(max_length=10, null=True, blank=True, db_column='MeasureUnit')
    cuft = models.DecimalField(max_digits=14, decimal_places=6, null=True, blank=True, db_column='CUFT')
    cbm = models.DecimalField(max_digits=14, decimal_places=6, null=True, blank=True, db_column='CBM')
    net_wt = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True, db_column='NetWt')
    gross_wt = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True, db_column='GrossWt')
    main_category_id = models.CharField(max_length=100, null=True, blank=True, db_column='MainCategoryId')
    sub_category_id = models.CharField(max_length=10, null=True, blank=True, db_column='SubCategoryId')
    hs_code = models.CharField(max_length=20, null=True, blank=True, db_column='HSCode')
    inactive = models.BooleanField(null=True, blank=True, db_column='Inactive')
    description = models.TextField(null=True, blank=True, db_column='Description')
    create_time = models.DateTimeField(null=True, blank=True, db_column='CreateTime')
    create_by = models.CharField(max_length=20, null=True, blank=True, db_column='CreateBy')
    mod_time = models.DateTimeField(null=True, blank=True, db_column='ModTime')
    mod_by = models.CharField(max_length=20, null=True, blank=True, db_column='ModBy')
    image = models.CharField(max_length=100, null=True, blank=True, db_column='Image')
    unit_price_term = models.CharField(max_length=30, null=True, blank=True, db_column='UnitPriceTerm')
    unit_price_term1 = models.CharField(max_length=30, null=True, blank=True, db_column='UnitPriceTerm1')
    unit_price_term2 = models.CharField(max_length=30, null=True, blank=True, db_column='UnitPriceTerm2')
    unit_cost_term = models.CharField(max_length=30, null=True, blank=True, db_column='UnitCostTerm')
    lab_test_till_date = models.DateTimeField(null=True, blank=True, db_column='LabTestTillDate')

    class Meta:
        db_table = 'PRODUCTS'
        indexes = [
            models.Index(fields=['product_id']),
            models.Index(fields=['supplier_id']),
            models.Index(fields=['product_name']),
        ]

    def __str__(self) -> str:
        return self.product_id


class ProductMainCategory(models.Model):
    """Lookup table for product main category names (Product_Main_CAT)."""

    main_category_id = models.CharField(max_length=100, db_column='MainCategoryID', primary_key=True)
    main_category_name = models.CharField(max_length=255, null=True, blank=True, db_column='MainCategoryName')

    class Meta:
        db_table = 'Product_Main_CAT'
        managed = False

    def __str__(self) -> str:
        return self.main_category_name or self.main_category_id


class ProductSubCategory(models.Model):
    """Lookup table for product sub category names (Product_Sub_Cat)."""

    sub_category_id = models.CharField(max_length=100, db_column='SubCategoryID', primary_key=True)
    sub_category_name = models.CharField(max_length=255, null=True, blank=True, db_column='SubCategoryName')

    class Meta:
        db_table = 'Product_Sub_Cat'
        managed = False

    def __str__(self) -> str:
        return self.sub_category_name or self.sub_category_id


class PaymentTerm(models.Model):
    """PostgreSQL copy of FoxPro TERMS."""

    term_code = models.CharField(max_length=10, unique=True, null=True, blank=True, db_column='PaymentTermCode')
    description = models.CharField(max_length=100, null=True, blank=True, db_column='Description')
    due_day = models.DecimalField(max_digits=3, decimal_places=0, null=True, blank=True, db_column='DueDay')
    discount = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, db_column='Discount')
    created_time = models.DateTimeField(null=True, blank=True, db_column='CreatedTime')
    created_by = models.CharField(max_length=20, null=True, blank=True, db_column='CreatedBy')
    mod_time = models.DateTimeField(null=True, blank=True, db_column='ModTime')
    mod_by = models.CharField(max_length=20, null=True, blank=True, db_column='ModBy')
    status = models.CharField(max_length=10, null=True, blank=True, db_column='Status')

    class Meta:
        db_table = 'PaymentTerm'
        indexes = [
            models.Index(fields=['term_code']),
            models.Index(fields=['status']),
        ]

    def __str__(self) -> str:
        return self.term_code or "PaymentTerm"


class Customer(models.Model):
    """PostgreSQL copy of FoxPro CUSTOMER."""

    customer_id = models.CharField(max_length=20, unique=True, null=True, blank=True, db_column='CustomerId')
    customer_code = models.CharField(max_length=10, null=True, blank=True, db_column='CustomerCode')
    salesman = models.CharField(max_length=10, null=True, blank=True, db_column='Salesman')
    customer_name = models.CharField(max_length=60, null=True, blank=True, db_column='CustomerName')
    contact_person = models.CharField(max_length=30, null=True, blank=True, db_column='ContactPerson')
    address1 = models.CharField(max_length=60, null=True, blank=True, db_column='Address1')
    address2 = models.CharField(max_length=60, null=True, blank=True, db_column='Address2')
    address3 = models.CharField(max_length=60, null=True, blank=True, db_column='Address3')
    address4 = models.CharField(max_length=60, null=True, blank=True, db_column='Address4')
    country = models.CharField(max_length=10, null=True, blank=True, db_column='Country')
    city = models.CharField(max_length=40, null=True, blank=True, db_column='City')
    region = models.CharField(max_length=40, null=True, blank=True, db_column='Region')
    postal_code = models.CharField(max_length=10, null=True, blank=True, db_column='PostalCode')
    tel = models.CharField(max_length=40, null=True, blank=True, db_column='Tel')
    tel1 = models.CharField(max_length=40, null=True, blank=True, db_column='Tel1')
    tel2 = models.CharField(max_length=40, null=True, blank=True, db_column='Tel2')
    contact_person1 = models.CharField(max_length=40, null=True, blank=True, db_column='ContactPerson1')
    contact_person2 = models.CharField(max_length=40, null=True, blank=True, db_column='ContactPerson2')
    fax = models.CharField(max_length=40, null=True, blank=True, db_column='Fax')
    mobile = models.CharField(max_length=40, null=True, blank=True, db_column='Mobile')
    email = models.CharField(max_length=80, null=True, blank=True, db_column='Email')
    payment_term = models.CharField(max_length=10, null=True, blank=True, db_column='PaymentTerm')
    status = models.CharField(max_length=10, null=True, blank=True, db_column='Status')
    ship_to = models.CharField(max_length=10, null=True, blank=True, db_column='ShipTo')
    trade_term = models.CharField(max_length=30, null=True, blank=True, db_column='TradeTerm')
    created_time = models.DateTimeField(null=True, blank=True, db_column='CreatedTime')
    created_by = models.CharField(max_length=30, null=True, blank=True, db_column='CreatedBy')
    mod_time = models.DateTimeField(null=True, blank=True, db_column='ModTime')
    mod_by = models.CharField(max_length=30, null=True, blank=True, db_column='ModBy')
    port_of_loading = models.CharField(max_length=10, null=True, blank=True, db_column='PortofLoading')
    po_remark = models.TextField(null=True, blank=True, db_column='PORemark')

    class Meta:
        db_table = 'Customer'
        indexes = [
            models.Index(fields=['customer_id']),
            models.Index(fields=['customer_code']),
            models.Index(fields=['customer_name']),
        ]

    def __str__(self) -> str:
        return self.customer_id or "Customer"


class FoxUser(models.Model):
    """PostgreSQL copy of FoxPro USERS."""

    user_id = models.CharField(max_length=20, unique=True, db_column='UserID')
    user_name = models.CharField(max_length=50, null=True, blank=True, db_column='UserName')
    password = models.CharField(max_length=20, null=True, blank=True, db_column='Password')
    mod_time = models.DateTimeField(null=True, blank=True, db_column='ModTime')
    mod_by = models.CharField(max_length=30, null=True, blank=True, db_column='ModBy')
    department_id = models.CharField(max_length=20, null=True, blank=True, db_column='DepartmentId')
    department_user_level = models.CharField(max_length=20, null=True, blank=True, db_column='DepartmentUserLevel')

    class Meta:
        db_table = 'User'
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['department_id']),
        ]

    def __str__(self) -> str:
        return self.user_id


class Supplier(models.Model):
    """PostgreSQL copy of FoxPro SUPPLIER."""

    supplier_code = models.CharField(max_length=20, unique=True, db_column='SupplierCode')
    supplier_name = models.CharField(max_length=100, null=True, blank=True, db_column='SupplierName')
    contact_person = models.CharField(max_length=50, null=True, blank=True, db_column='ContactPerson')
    address1 = models.CharField(max_length=100, null=True, blank=True, db_column='Address1')
    address2 = models.CharField(max_length=100, null=True, blank=True, db_column='Address2')
    address3 = models.CharField(max_length=100, null=True, blank=True, db_column='Address3')
    address4 = models.CharField(max_length=100, null=True, blank=True, db_column='Address4')
    city = models.CharField(max_length=50, null=True, blank=True, db_column='City')
    region = models.CharField(max_length=50, null=True, blank=True, db_column='Region')
    postal_code = models.CharField(max_length=20, null=True, blank=True, db_column='PostalCode')
    country = models.CharField(max_length=10, null=True, blank=True, db_column='Country')
    tel = models.CharField(max_length=50, null=True, blank=True, db_column='Tel')
    fax = models.CharField(max_length=50, null=True, blank=True, db_column='Fax')
    mobile = models.CharField(max_length=50, null=True, blank=True, db_column='Mobile')
    email = models.CharField(max_length=100, null=True, blank=True, db_column='Email')
    contact_tel1 = models.CharField(max_length=50, null=True, blank=True, db_column='ContactTel1')
    contact_tel2 = models.CharField(max_length=50, null=True, blank=True, db_column='ContactTel2')
    contact_tel3 = models.CharField(max_length=50, null=True, blank=True, db_column='ContactTel3')
    contact1 = models.CharField(max_length=50, null=True, blank=True, db_column='Contact1')
    contact2 = models.CharField(max_length=50, null=True, blank=True, db_column='Contact2')
    contact3 = models.CharField(max_length=50, null=True, blank=True, db_column='Contact3')
    payment_term = models.CharField(max_length=10, null=True, blank=True, db_column='PaymentTerm')
    ship_from = models.CharField(max_length=10, null=True, blank=True, db_column='ShipFrom')
    remark = models.TextField(null=True, blank=True, db_column='Remark')
    created_time = models.DateTimeField(null=True, blank=True, db_column='CreatedTime')
    created_by = models.CharField(max_length=50, null=True, blank=True, db_column='CreatedBy')
    mod_time = models.DateTimeField(null=True, blank=True, db_column='ModTime')
    mod_by = models.CharField(max_length=50, null=True, blank=True, db_column='ModBy')
    date1 = models.DateTimeField(null=True, blank=True, db_column='Date1')
    audit_exp_date = models.DateTimeField(null=True, blank=True, db_column='AuditExpDate')
    date3 = models.DateTimeField(null=True, blank=True, db_column='Date3')
    homepage = models.CharField(max_length=100, null=True, blank=True, db_column='Homepage')
    contact_email1 = models.CharField(max_length=100, null=True, blank=True, db_column='ContactEmail1')
    contact_email2 = models.CharField(max_length=100, null=True, blank=True, db_column='ContactEmail2')
    contact_email3 = models.CharField(max_length=100, null=True, blank=True, db_column='ContactEmail3')
    audit_pass_time = models.DateTimeField(null=True, blank=True, db_column='AuditPassTime')
    audit_pass_by = models.CharField(max_length=50, null=True, blank=True, db_column='AuditPassBy')

    class Meta:
        db_table = 'Supplier'
        indexes = [
            models.Index(fields=['supplier_code']),
            models.Index(fields=['supplier_name']),
        ]

    def __str__(self) -> str:
        return self.supplier_code


class WorkflowGridTemplate(models.Model):
    """Workflow grid template for repeat/new orders."""

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=50, unique=True)
    source_file = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name


class WorkflowGridColumn(models.Model):
    """Column definition derived from Excel templates."""

    DATA_TYPE_CHOICES = [
        ('text', 'Text'),
        ('date', 'Date'),
        ('number', 'Number'),
        ('boolean', 'Boolean'),
    ]

    template = models.ForeignKey(WorkflowGridTemplate, on_delete=models.CASCADE, related_name='columns')
    key = models.CharField(max_length=100)
    label = models.CharField(max_length=200)
    group_label = models.CharField(max_length=200, blank=True)
    order = models.IntegerField()
    data_type = models.CharField(max_length=20, choices=DATA_TYPE_CHOICES, default='text')

    class Meta:
        ordering = ['order']
        unique_together = ('template', 'key')

    def __str__(self) -> str:
        return f"{self.template.slug} - {self.label}"

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = slugify(self.label)[:100]
        super().save(*args, **kwargs)


class WorkflowGridEntry(models.Model):
    """Workflow grid values for each SODetail row."""

    template = models.ForeignKey(WorkflowGridTemplate, on_delete=models.CASCADE, related_name='entries')
    order_detail = models.ForeignKey(SODetail, on_delete=models.CASCADE, related_name='workflow_entries')
    assigned_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    data = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('template', 'order_detail')
        indexes = [
            models.Index(fields=['template', 'department']),
            models.Index(fields=['assigned_user']),
        ]

    def __str__(self) -> str:
        return f"{self.template.slug} - {self.order_detail.sc_number}"


class WipTypeDefinition(models.Model):
    """WIP type definition by lead time per department."""

    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='wip_types')
    name = models.CharField(max_length=200)
    lead_time_min = models.IntegerField()
    lead_time_max = models.IntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('department', 'name')
        indexes = [
            models.Index(fields=['department', 'is_active']),
            models.Index(fields=['lead_time_min', 'lead_time_max']),
        ]

    def __str__(self) -> str:
        return f"{self.department.code} - {self.name}"


class WipCheckpointDefinition(models.Model):
    """Checkpoint definitions for a WIP type."""

    RULE_TYPE_CHOICES = [
        ('crd_offset', 'CRD Offset'),
        ('prev_offset', 'Previous Checkpoint Offset'),
    ]

    wip_type = models.ForeignKey(WipTypeDefinition, on_delete=models.CASCADE, related_name='checkpoints')
    label = models.CharField(max_length=200)
    order = models.IntegerField()
    rule_type = models.CharField(max_length=20, choices=RULE_TYPE_CHOICES)
    offset_days = models.IntegerField()

    class Meta:
        ordering = ['order']
        unique_together = ('wip_type', 'order')

    def __str__(self) -> str:
        return f"{self.wip_type.name} - {self.label}"


class WipOrder(models.Model):
    """WIP order for each order line item."""

    STATUS_CHOICES = [
        ('open', 'Open'),
        ('completed', 'Completed'),
        ('on_hold', 'On Hold'),
    ]

    somain = models.ForeignKey(SOMain, on_delete=models.CASCADE, related_name='wip_orders')
    sodetail = models.ForeignKey(SODetail, on_delete=models.CASCADE, related_name='wip_orders')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    assigned_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    wip_type = models.ForeignKey(WipTypeDefinition, on_delete=models.SET_NULL, null=True, blank=True)
    lead_time_days = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')

    class Meta:
        unique_together = ('somain', 'sodetail')
        indexes = [
            models.Index(fields=['department', 'status']),
            models.Index(fields=['assigned_user']),
        ]

    def __str__(self) -> str:
        return f"{self.sodetail.sc_number} - {self.sodetail.product_id}"


class WipTask(models.Model):
    """WIP tasks derived from checkpoint definitions."""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('overdue', 'Overdue'),
    ]

    wip_order = models.ForeignKey(WipOrder, on_delete=models.CASCADE, related_name='tasks')
    checkpoint = models.ForeignKey(WipCheckpointDefinition, on_delete=models.CASCADE, related_name='tasks')
    planned_date = models.DateField(null=True, blank=True)
    action_date = models.DateField(null=True, blank=True)
    kpi_days = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    inspection_by = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        choices=[
            ('MTL', 'MTL'),
            ('3RD', '3rd'),
            ('SELF', 'Self'),
        ],
    )
    inspection_result = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        choices=[
            ('PASS', 'Pass'),
            ('FAIL', 'Fail'),
        ],
    )

    class Meta:
        unique_together = ('wip_order', 'checkpoint')
        indexes = [
            models.Index(fields=['planned_date']),
            models.Index(fields=['status']),
        ]

    def __str__(self) -> str:
        return f"{self.wip_order} - {self.checkpoint.label}"

    def update_kpi(self) -> None:
        if self.planned_date and self.action_date:
            self.kpi_days = (self.action_date - self.planned_date).days
        else:
            self.kpi_days = None

    def save(self, *args, **kwargs):
        self.update_kpi()
        super().save(*args, **kwargs)
