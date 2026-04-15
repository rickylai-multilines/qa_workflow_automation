from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView
from django.contrib.auth import get_user_model
from django.db import DatabaseError
from django.db.models import Case, Count, IntegerField, Q, When, Prefetch
from django.conf import settings
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView
from django.urls import reverse, reverse_lazy
from django.core.paginator import Paginator
import re
from pathlib import Path

from .models import (
    Order,
    OrderTask,
    UserDashboardPreference,
    WorkflowGridTemplate,
    WorkflowGridEntry,
    WipOrder,
    WipTypeDefinition,
    WipCheckpointDefinition,
    WipTask,
    SOMain,
    SODetail,
    Customer,
    Department,
    FoxUser,
    PaymentTerm,
    Product,
    ProductMainCategory,
    ProductSubCategory,
    Supplier,
)

UserModel = get_user_model()


class CustomLoginView(LoginView):
    """Login view for the order workflow system."""

    template_name = 'orders/login.html'
    redirect_authenticated_user = True


class DashboardView(LoginRequiredMixin, TemplateView):
    """Main dashboard showing task alerts and summary."""

    template_name = 'orders/dashboard.html'
    login_url = reverse_lazy('orders:login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        prefs, _ = UserDashboardPreference.objects.get_or_create(user=user)

        user_tasks = OrderTask.objects.filter(
            assigned_to=user,
            status__in=['pending', 'in_progress'] if not prefs.show_completed_tasks else ['pending', 'in_progress', 'completed'],
        ).select_related('order', 'stage')

        critical_tasks = user_tasks.filter(alert_status='critical')
        warning_tasks = user_tasks.filter(alert_status='warning')
        normal_tasks = user_tasks.filter(alert_status='normal')

        orders = Order.objects.filter(
            tasks__assigned_to=user,
        ).distinct().annotate(
            task_count=Count('tasks'),
            completed_count=Count(
                Case(When(tasks__status='completed', then=1), output_field=IntegerField()),
            ),
        ).order_by('-updated_at')[:10]

        context.update({
            'critical_tasks': critical_tasks[:10],
            'warning_tasks': warning_tasks[:10],
            'normal_tasks': normal_tasks[:5],
            'recent_orders': orders,
            'user_prefs': prefs,
            'stats': {
                'critical_count': critical_tasks.count(),
                'warning_count': warning_tasks.count(),
                'normal_count': normal_tasks.count(),
                'total_tasks': user_tasks.count(),
                'orders_count': orders.count(),
            },
        })

        return context


class OrderListView(LoginRequiredMixin, View):
    """Order list using SOMAIN/SODETAIL data."""

    login_url = reverse_lazy('orders:login')

    def get(self, request):
        sc_number = request.GET.get('sc_number', '').strip()
        cust_order = request.GET.get('cust_order', '').strip()
        sc_date_from = request.GET.get('sc_date_from', '').strip()
        sc_date_to = request.GET.get('sc_date_to', '').strip()
        order_date_from = request.GET.get('order_date_from', '').strip()
        order_date_to = request.GET.get('order_date_to', '').strip()
        crd_from = request.GET.get('crd_from', '').strip()
        crd_to = request.GET.get('crd_to', '').strip()
        department = request.GET.get('department', '').strip()
        status = request.GET.get('status', '').strip()
        global_q = request.GET.get('q', '').strip()
        sort = request.GET.get('sort', 'sc_number').strip()
        sort_dir = request.GET.get('dir', 'asc').strip().lower()

        base_qs = SOMain.objects.all()
        fox_user = FoxUser.objects.filter(user_id=request.user.username).first()
        if fox_user:
            level = (fox_user.department_user_level or 'NORMAL').upper()
            if level == 'ADMIN':
                pass
            elif level == 'SUPERVISOR':
                if fox_user.department_id:
                    base_qs = base_qs.filter(department_no=fox_user.department_id)
                else:
                    base_qs = base_qs.none()
            else:
                base_qs = base_qs.filter(user_id=fox_user.user_id)
        else:
            base_qs = base_qs.none()

        somain_qs = base_qs
        if sc_number:
            somain_qs = somain_qs.filter(sc_number__icontains=sc_number)
        if cust_order:
            somain_qs = somain_qs.filter(cust_order__icontains=cust_order)
        if department:
            somain_qs = somain_qs.filter(department_no=department)
        if status:
            somain_qs = somain_qs.filter(sc_status=status)

        if order_date_from:
            try:
                somain_qs = somain_qs.filter(order_date__date__gte=order_date_from)
            except ValueError:
                pass
        if order_date_to:
            try:
                somain_qs = somain_qs.filter(order_date__date__lte=order_date_to)
            except ValueError:
                pass
        if sc_date_from:
            try:
                somain_qs = somain_qs.filter(sc_date__date__gte=sc_date_from)
            except ValueError:
                pass
        if sc_date_to:
            try:
                somain_qs = somain_qs.filter(sc_date__date__lte=sc_date_to)
            except ValueError:
                pass
        if crd_from:
            try:
                somain_qs = somain_qs.filter(crd__date__gte=crd_from)
            except ValueError:
                pass
        if crd_to:
            try:
                somain_qs = somain_qs.filter(crd__date__lte=crd_to)
            except ValueError:
                pass

        if global_q:
            detail_sc_numbers = (
                SODetail.objects.filter(
                    Q(sc_number__icontains=global_q)
                    | Q(product_id__icontains=global_q)
                    | Q(cust_item_code__icontains=global_q)
                    | Q(supplier_id__icontains=global_q)
                    | Q(product_name__icontains=global_q)
                    | Q(item_description__icontains=global_q)
                    | Q(supplier_item_code__icontains=global_q)
                    | Q(bmi_item_code__icontains=global_q)
                    | Q(french_item_code__icontains=global_q)
                    | Q(brand__icontains=global_q)
                )
                .values_list('sc_number', flat=True)
                .distinct()
            )
            somain_qs = somain_qs.filter(
                Q(sc_number__icontains=global_q)
                | Q(created_by__icontains=global_q)
                | Q(cust_order__icontains=global_q)
                | Q(user_id__icontains=global_q)
                | Q(cu_code__icontains=global_q)
                | Q(sc_number__in=detail_sc_numbers)
            )

        sortable_fields = {
            'company': 'company',
            'sc_number': 'sc_number',
            'sc_status': 'sc_status',
            'cu_code': 'cu_code',
            'cust_order': 'cust_order',
            'sc_date': 'sc_date',
            'crd': 'crd',
            'department_no': 'department_no',
            'user_id': 'user_id',
            'port_of_load': 'port_of_load',
            'port_of_disch': 'port_of_disch',
            'doc_net_total_amt': 'doc_net_total_amt',
        }
        sort_field = sortable_fields.get(sort, 'sc_number')
        if sort_dir not in {'asc', 'desc'}:
            sort_dir = 'asc'
        order_by = sort_field if sort_dir == 'asc' else f"-{sort_field}"
        somain_qs = somain_qs.order_by(order_by)
        paginator = Paginator(somain_qs, 50)
        page_obj = paginator.get_page(request.GET.get('page'))

        cu_codes = list(
            {
                order.cu_code
                for order in page_obj.object_list
                if order.cu_code
            },
        )
        customer_map = {
            customer.customer_id: customer.customer_name
            for customer in Customer.objects.filter(customer_id__in=cu_codes)
        }
        department_codes = list(
            {
                order.department_no
                for order in page_obj.object_list
                if order.department_no
            },
        )
        department_map = {
            department.code: department.name
            for department in Department.objects.filter(code__in=department_codes)
        }
        user_ids = list(
            {
                order.user_id
                for order in page_obj.object_list
                if order.user_id
            },
        )
        merchandiser_map = {
            user.user_id: user.user_name
            for user in FoxUser.objects.filter(user_id__in=user_ids)
        }

        status_counts = base_qs.values('sc_status').annotate(total=Count('sc_status'))
        status_map = {item['sc_status'] or 'Unknown': item['total'] for item in status_counts}
        departments = list(Department.objects.order_by('name', 'code'))

        # WIP flag: which SC numbers already have WIP orders
        sc_numbers_page = [order.sc_number for order in page_obj.object_list]
        wip_sc_numbers = set(
            WipOrder.objects.filter(somain__sc_number__in=sc_numbers_page)
            .values_list('somain__sc_number', flat=True)
        )

        show_advanced = request.GET.get('advanced') == '1' or any([
            sc_number,
            cust_order,
            sc_date_from,
            sc_date_to,
            order_date_from,
            order_date_to,
            crd_from,
            crd_to,
            department,
        ])

        context = {
            'orders': page_obj.object_list,
            'page_obj': page_obj,
            'status_map': status_map,
            'departments': departments,
            'customer_map': customer_map,
            'department_map': department_map,
            'merchandiser_map': merchandiser_map,
            'wip_sc_numbers': wip_sc_numbers,
            'show_advanced': show_advanced,
            'sort': sort,
            'sort_dir': sort_dir,
            'filters': {
                'sc_number': sc_number,
                'cust_order': cust_order,
                'sc_date_from': sc_date_from,
                'sc_date_to': sc_date_to,
                'order_date_from': order_date_from,
                'order_date_to': order_date_to,
                'crd_from': crd_from,
                'crd_to': crd_to,
                'department': department,
                'status': status,
                'q': global_q,
            },
        }
        return render(request, 'orders/order_list.html', context)


class SCProductListView(LoginRequiredMixin, View):
    """SC Product List: all order line items with search, displayed like order detail items."""

    login_url = reverse_lazy('orders:login')

    def get(self, request):
        sc_number = request.GET.get('sc_number', '').strip()
        cust_order = request.GET.get('cust_order', '').strip()
        sc_date_from = request.GET.get('sc_date_from', '').strip()
        sc_date_to = request.GET.get('sc_date_to', '').strip()
        order_date_from = request.GET.get('order_date_from', '').strip()
        order_date_to = request.GET.get('order_date_to', '').strip()
        crd_from = request.GET.get('crd_from', '').strip()
        crd_to = request.GET.get('crd_to', '').strip()
        department = request.GET.get('department', '').strip()
        status = request.GET.get('status', '').strip()
        global_q = request.GET.get('q', '').strip()

        base_qs = SOMain.objects.all()
        fox_user = FoxUser.objects.filter(user_id=request.user.username).first()
        if fox_user:
            level = (fox_user.department_user_level or 'NORMAL').upper()
            if level == 'ADMIN':
                pass
            elif level == 'SUPERVISOR':
                if fox_user.department_id:
                    base_qs = base_qs.filter(department_no=fox_user.department_id)
                else:
                    base_qs = base_qs.none()
            else:
                base_qs = base_qs.filter(user_id=fox_user.user_id)
        else:
            base_qs = base_qs.none()

        somain_qs = base_qs
        if sc_number:
            somain_qs = somain_qs.filter(sc_number__icontains=sc_number)
        if cust_order:
            somain_qs = somain_qs.filter(cust_order__icontains=cust_order)
        if department:
            somain_qs = somain_qs.filter(department_no=department)
        if status:
            somain_qs = somain_qs.filter(sc_status=status)
        if order_date_from:
            try:
                somain_qs = somain_qs.filter(order_date__date__gte=order_date_from)
            except ValueError:
                pass
        if order_date_to:
            try:
                somain_qs = somain_qs.filter(order_date__date__lte=order_date_to)
            except ValueError:
                pass
        if sc_date_from:
            try:
                somain_qs = somain_qs.filter(sc_date__date__gte=sc_date_from)
            except ValueError:
                pass
        if sc_date_to:
            try:
                somain_qs = somain_qs.filter(sc_date__date__lte=sc_date_to)
            except ValueError:
                pass
        if crd_from:
            try:
                somain_qs = somain_qs.filter(crd__date__gte=crd_from)
            except ValueError:
                pass
        if crd_to:
            try:
                somain_qs = somain_qs.filter(crd__date__lte=crd_to)
            except ValueError:
                pass
        if global_q:
            detail_q = Q(
                Q(sc_number__icontains=global_q)
                | Q(product_id__icontains=global_q)
                | Q(product_name__icontains=global_q)
                | Q(cust_item_code__icontains=global_q)
                | Q(supplier_item_code__icontains=global_q)
                | Q(supplier_id__icontains=global_q)
                | Q(brand__icontains=global_q)
                | Q(bmi_item_code__icontains=global_q)
                | Q(french_item_code__icontains=global_q)
            )
            detail_sc_numbers = SODetail.objects.filter(detail_q).values_list('sc_number', flat=True).distinct()
            somain_qs = somain_qs.filter(
                Q(sc_number__icontains=global_q)
                | Q(cust_order__icontains=global_q)
                | Q(user_id__icontains=global_q)
                | Q(cu_code__icontains=global_q)
                | Q(sc_number__in=detail_sc_numbers)
            )
        sc_numbers = list(somain_qs.values_list('sc_number', flat=True).distinct())
        detail_qs = SODetail.objects.filter(sc_number__in=sc_numbers).order_by('sc_number', 'product_id')
        if global_q:
            detail_qs = detail_qs.filter(
                Q(sc_number__icontains=global_q)
                | Q(product_id__icontains=global_q)
                | Q(product_name__icontains=global_q)
                | Q(cust_item_code__icontains=global_q)
                | Q(supplier_item_code__icontains=global_q)
                | Q(supplier_id__icontains=global_q)
                | Q(brand__icontains=global_q)
                | Q(bmi_item_code__icontains=global_q)
                | Q(french_item_code__icontains=global_q)
            )
        paginator = Paginator(detail_qs, 100)
        page_obj = paginator.get_page(request.GET.get('page'))
        product_ids = list({d.product_id for d in page_obj.object_list if d.product_id})
        product_map = {
            p.product_id: p
            for p in Product.objects.filter(product_id__in=product_ids)
        }
        page_sc_numbers = list({d.sc_number for d in page_obj.object_list})
        somain_map = {s.sc_number: s for s in SOMain.objects.filter(sc_number__in=page_sc_numbers)}
        detail_rows = []
        for detail in page_obj.object_list:
            amount = None
            if detail.qty is not None and detail.unit_price is not None:
                amount = detail.qty * detail.unit_price
            somain = somain_map.get(detail.sc_number)
            detail_rows.append({
                'detail': detail,
                'amount': amount,
                'product': product_map.get(detail.product_id),
                'somain': somain,
            })
        departments = list(Department.objects.order_by('name', 'code'))
        show_advanced = request.GET.get('advanced') == '1' or any([
            sc_number, cust_order, sc_date_from, sc_date_to,
            order_date_from, order_date_to, crd_from, crd_to, department, status,
        ])
        get_copy = request.GET.copy()
        if 'page' in get_copy:
            get_copy.pop('page')
        pagination_query = get_copy.urlencode()
        context = {
            'detail_rows': detail_rows,
            'page_obj': page_obj,
            'departments': departments,
            'show_advanced': show_advanced,
            'pagination_query': pagination_query,
            'filters': {
                'sc_number': sc_number,
                'cust_order': cust_order,
                'sc_date_from': sc_date_from,
                'sc_date_to': sc_date_to,
                'order_date_from': order_date_from,
                'order_date_to': order_date_to,
                'crd_from': crd_from,
                'crd_to': crd_to,
                'department': department,
                'status': status,
                'q': global_q,
            },
        }
        return render(request, 'orders/sc_product_list.html', context)


class ProductListView(LoginRequiredMixin, View):
    """Products list with general search."""

    login_url = reverse_lazy('orders:login')

    def get(self, request):
        global_q = request.GET.get('q', '').strip()

        products_qs = Product.objects.all().order_by('product_id')
        if global_q:
            terms = [line.strip() for line in global_q.splitlines() if line.strip()]
            if not terms:
                terms = [global_q]
            combined_q = Q()
            for term in terms:
                term_q = (
                    Q(product_id__icontains=term)
                    | Q(product_name__icontains=term)
                    | Q(description__icontains=term)
                    | Q(customer_item_code__icontains=term)
                    | Q(french_item_code__icontains=term)
                    | Q(supplier_id__icontains=term)
                    | Q(brand__icontains=term)
                    | Q(copy_from_product_id__icontains=term)
                    | Q(supplier_item_code__icontains=term)
                )
                combined_q |= term_q
            products_qs = products_qs.filter(combined_q)

        paginator = Paginator(products_qs, 100)
        page_obj = paginator.get_page(request.GET.get('page'))

        main_category_ids = list(
            {
                product.main_category_id
                for product in page_obj.object_list
                if product.main_category_id
            }
        )
        main_category_map = {
            category.main_category_id: category.main_category_name
            for category in ProductMainCategory.objects.filter(main_category_id__in=main_category_ids)
        }

        product_rows = []
        for product in page_obj.object_list:
            main_category_name = main_category_map.get(product.main_category_id) or product.main_category_id
            image_url = None
            if product.product_id and _PRODUCT_ID_SAFE_RE.match(product.product_id):
                image_url = reverse_lazy('orders:product-image', kwargs={'product_id': product.product_id})
            product_rows.append({
                'product': product,
                'main_category_name': main_category_name,
                'image_url': image_url,
            })

        context = {
            'product_rows': product_rows,
            'page_obj': page_obj,
            'filters': {
                'q': global_q,
            },
        }
        return render(request, 'orders/product_list.html', context)


class ProductDetailView(LoginRequiredMixin, View):
    """Read-only product detail (FoxPro PRODUCTS mirror)."""

    login_url = reverse_lazy('orders:login')

    def get(self, request, product_id):
        product = get_object_or_404(Product, product_id=product_id)

        main_category_name = ''
        if product.main_category_id:
            main_category_name = (
                ProductMainCategory.objects.filter(main_category_id=product.main_category_id)
                .values_list('main_category_name', flat=True)
                .first()
            ) or product.main_category_id

        sub_category_name = ''
        if product.sub_category_id:
            try:
                sub_category_name = (
                    ProductSubCategory.objects.filter(sub_category_id=product.sub_category_id)
                    .values_list('sub_category_name', flat=True)
                    .first()
                ) or product.sub_category_id
            except DatabaseError:
                sub_category_name = product.sub_category_id

        image_url = None
        if product.product_id and _PRODUCT_ID_SAFE_RE.match(product.product_id):
            image_url = reverse('orders:product-image', kwargs={'product_id': product.product_id})

        supplier_display = product.supplier_id or ''
        if product.supplier_id:
            supplier_name = (
                Supplier.objects.filter(supplier_code=product.supplier_id)
                .values_list('supplier_name', flat=True)
                .first()
            )
            if supplier_name:
                supplier_display = f"{product.supplier_id} - {supplier_name}"

        context = {
            'product': product,
            'main_category_name': main_category_name,
            'sub_category_name': sub_category_name,
            'image_url': image_url,
            'supplier_display': supplier_display,
        }
        return render(request, 'orders/product_detail.html', context)


class OrderDetailView(LoginRequiredMixin, View):
    """Order detail view using SOMAIN/SODETAIL."""

    login_url = reverse_lazy('orders:login')

    def _check_permission(self, request, somain):
        fox_user = FoxUser.objects.filter(user_id=request.user.username).first()
        if fox_user:
            level = (fox_user.department_user_level or 'NORMAL').upper()
            if level == 'ADMIN':
                return True
            elif level == 'SUPERVISOR':
                if not fox_user.department_id or somain.department_no != fox_user.department_id:
                    return False
            else:
                if somain.user_id != fox_user.user_id:
                    return False
        else:
            return False
        return True

    def get(self, request, sc_number):
        somain = get_object_or_404(SOMain, sc_number=sc_number)
        if not self._check_permission(request, somain):
            return redirect('orders:order-list')
        details = SODetail.objects.filter(sc_number=sc_number).order_by('product_id')
        detail_rows = []
        product_ids = list({detail.product_id for detail in details if detail.product_id})
        product_map = {
            product.product_id: product
            for product in Product.objects.filter(product_id__in=product_ids)
        }
        for detail in details:
            amount = None
            if detail.qty is not None and detail.unit_price is not None:
                amount = detail.qty * detail.unit_price
            detail_rows.append({
                'detail': detail,
                'amount': amount,
                'product': product_map.get(detail.product_id),
            })
        total_amount = somain.net_total_amt if somain.net_total_amt is not None else None
        customer_name = None
        if somain.cu_code:
            customer_name = (
                Customer.objects.filter(customer_id=somain.cu_code)
                .values_list('customer_name', flat=True)
                .first()
            )
        department_name = None
        if somain.department_no:
            department_name = (
                Department.objects.filter(code=somain.department_no)
                .values_list('name', flat=True)
                .first()
            )
        payment_term_desc = None
        if somain.payment_term_code:
            payment_term_desc = (
                PaymentTerm.objects.filter(term_code=somain.payment_term_code)
                .values_list('description', flat=True)
                .first()
            )

        wip_exported = WipOrder.objects.filter(somain=somain).exists()

        context = {
            'somain': somain,
            'detail_rows': detail_rows,
            'total_amount': total_amount,
            'customer_name': customer_name,
            'department_name': department_name,
            'payment_term_desc': payment_term_desc,
            'wip_exported': wip_exported,
        }
        return render(request, 'orders/order_detail.html', context)

    def post(self, request, sc_number):
        somain = get_object_or_404(SOMain, sc_number=sc_number)
        if not self._check_permission(request, somain):
            return redirect('orders:order-list')

        action = request.POST.get('action')
        if action == 'export_wip':
            self._export_to_wip(somain)
        return redirect('orders:order-detail', sc_number=sc_number)

    def _export_to_wip(self, somain):
        """Create WIP orders/tasks for this SOMain on demand."""
        # Department from SOMain.department_no
        department = None
        if somain.department_no:
            department, _ = Department.objects.get_or_create(
                code=somain.department_no,
                defaults={'name': somain.department_no},
            )

        # Default assigned user from SOMain.user_id (merchandiser)
        assigned_user = None
        if somain.user_id:
            assigned_user = UserModel.objects.filter(username=somain.user_id).first()

        # Lead time and WIP type
        lead_time = _lead_time_days(somain.sc_date, somain.crd)
        wip_type = _select_wip_type(department, lead_time)

        # For each detail line, create/update a WipOrder and its WipTasks
        details = SODetail.objects.filter(sc_number=somain.sc_number)
        for detail in details:
            wip_order, _ = WipOrder.objects.update_or_create(
                somain=somain,
                sodetail=detail,
                defaults={
                    'department': department,
                    'assigned_user': assigned_user,
                    'wip_type': wip_type,
                    'lead_time_days': lead_time,
                },
            )

            if not wip_type or not somain.crd:
                continue

            checkpoints = list(wip_type.checkpoints.all())
            planned_dates = _compute_planned_dates(somain.crd.date(), checkpoints)

            for cp in checkpoints:
                planned_date = planned_dates.get(cp.id)
                status = 'pending'
                task, task_created = WipTask.objects.get_or_create(
                    wip_order=wip_order,
                    checkpoint=cp,
                    defaults={
                        'planned_date': planned_date,
                        'status': status,
                    },
                )
                if not task_created:
                    task.planned_date = planned_date
                    if task.action_date:
                        task.status = 'completed'
                    elif planned_date and planned_date < date.today():
                        task.status = 'overdue'
                    else:
                        task.status = 'pending'
                    task.save(update_fields=['planned_date', 'status', 'kpi_days'])


# Safe product_id for path: alphanumeric, hyphen, underscore only
_PRODUCT_ID_SAFE_RE = re.compile(r'^[A-Za-z0-9_\-]+$')
_IMAGE_EXTS = ('.jpg', '.jpeg', '.png', '.gif', '.webp')
_CONTENT_TYPES = {
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.webp': 'image/webp',
}


def _safe_image_filename(name):
    """Allow alphanumeric, hyphen, underscore, dot only (for path safety)."""
    if not name:
        return None
    safe = re.sub(r'[^A-Za-z0-9_\-.]', '', name)
    return safe if safe else None


@login_required(login_url=reverse_lazy('orders:login'))
def product_image(request, product_id):
    """Serve product image from Product_images. Uses Product.image when available, else tries common patterns."""
    if not product_id or not _PRODUCT_ID_SAFE_RE.match(product_id):
        raise Http404('Invalid product id')
    root = getattr(settings, 'PRODUCT_IMAGES_ROOT', None) or (settings.BASE_DIR / 'Product_images')
    root = root if hasattr(root, 'exists') else Path(root)
    if not root.exists():
        raise Http404('Product images folder not found')

    candidates = []
    db_image = Product.objects.filter(product_id=product_id).values_list('image', flat=True).first()
    if db_image:
        fn = _safe_image_filename(db_image)
        if fn:
            candidates.append(root / fn)
    candidates.extend(
        root / f'{product_id}{suffix}{ext}'
        for suffix in ('1', '000')
        for ext in _IMAGE_EXTS
    )

    for path in candidates:
        if path.is_file():
            ext = path.suffix.lower()
            content_type = _CONTENT_TYPES.get(ext, 'application/octet-stream')
            return FileResponse(path.open('rb'), content_type=content_type, as_attachment=False)
    raise Http404('Product image not found')


class UpdateTaskStatusView(LoginRequiredMixin, View):
    """AJAX endpoint to mark task as complete."""

    login_url = reverse_lazy('orders:login')
    def post(self, request, task_id):
        task = get_object_or_404(OrderTask, id=task_id)

        if request.user != task.assigned_to and not request.user.is_staff:
            return JsonResponse({'error': 'Permission denied'}, status=403)

        actual_date = request.POST.get('actual_date')
        notes = request.POST.get('notes', '')

        parsed_date = None
        if actual_date:
            try:
                parsed_date = date.fromisoformat(actual_date)
            except ValueError:
                parsed_date = None

        task.actual_date = parsed_date
        task.notes = notes
        task.status = 'completed'
        task.alert_status = 'normal'
        task.save()

        return JsonResponse({
            'status': 'success',
            'message': 'Task marked complete',
            'task_id': task.id,
            'completion_percentage': task.order.completion_percentage,
        })


class UserPreferencesView(LoginRequiredMixin, View):
    """Manage user's notification and dashboard preferences."""

    login_url = reverse_lazy('orders:login')
    def get(self, request):
        prefs, _ = UserDashboardPreference.objects.get_or_create(user=request.user)
        return render(request, 'settings/preferences.html', {'prefs': prefs})

    def post(self, request):
        prefs, _ = UserDashboardPreference.objects.get_or_create(user=request.user)

        prefs.daily_email_enabled = request.POST.get('daily_email_enabled') == 'on'
        prefs.daily_email_time = request.POST.get('daily_email_time', '09:00')
        prefs.send_warning_alerts = request.POST.get('send_warning_alerts') == 'on'
        prefs.send_critical_alerts = request.POST.get('send_critical_alerts') == 'on'
        prefs.show_completed_tasks = request.POST.get('show_completed_tasks') == 'on'
        prefs.default_view = request.POST.get('default_view', 'my_tasks')
        prefs.save()

        return redirect('orders:dashboard')


def _lead_time_days(sc_date, crd):
    if not sc_date or not crd:
        return None
    return (crd.date() - sc_date.date()).days


def _select_wip_type(department, lead_time):
    if not department or lead_time is None:
        return None
    return (
        WipTypeDefinition.objects.filter(
            department=department,
            is_active=True,
            lead_time_min__lte=lead_time,
            lead_time_max__gte=lead_time,
        )
        .order_by('lead_time_min')
        .first()
    )


def _compute_planned_dates(crd_date, checkpoints):
    planned = {}
    last_date = None
    for cp in checkpoints:
        if cp.rule_type == 'crd_offset':
            planned_date = crd_date + timedelta(days=cp.offset_days)
        else:
            if last_date is None:
                continue
            planned_date = last_date + timedelta(days=cp.offset_days)
        planned[cp.id] = planned_date
        last_date = planned_date
    return planned


class WorkflowListView(LoginRequiredMixin, View):
    """List workflow entries for a template."""

    login_url = reverse_lazy('orders:login')

    def get(self, request, slug):
        template = get_object_or_404(WorkflowGridTemplate, slug=slug, is_active=True)
        columns = list(template.columns.all())

        profile = getattr(request.user, 'orders_profile', None)
        if profile and profile.is_supervisor:
            entries = WorkflowGridEntry.objects.filter(template=template, department=profile.department)
        else:
            entries = WorkflowGridEntry.objects.filter(template=template, assigned_user=request.user)

        entries = entries.select_related('order_detail', 'assigned_user', 'department').order_by('order_detail__sc_number')

        context = {
            'template': template,
            'columns': columns,
            'entries': entries,
        }
        return render(request, 'orders/workflow_list.html', context)


class WorkflowEntryEditView(LoginRequiredMixin, View):
    """Edit workflow entry values."""

    login_url = reverse_lazy('orders:login')

    def get(self, request, entry_id):
        entry = get_object_or_404(WorkflowGridEntry, id=entry_id)
        template = entry.template
        columns = list(template.columns.all())
        return render(request, 'orders/workflow_edit.html', {
            'entry': entry,
            'template': template,
            'columns': columns,
        })

    def post(self, request, entry_id):
        entry = get_object_or_404(WorkflowGridEntry, id=entry_id)
        template = entry.template
        columns = list(template.columns.all())

        data = dict(entry.data or {})
        for column in columns:
            data[column.key] = request.POST.get(column.key, '')
        entry.data = data
        entry.save(update_fields=['data', 'updated_at'])
        return redirect('orders:workflow-list', slug=template.slug)


def _propagate_checkpoint_action_date(task):
    """
    When a checkpoint action date is set, copy it to other WipTasks that share
    the same Product ID, same checkpoint label, and SC date within ±30 days.
    Uses checkpoint label (not id) so orders under different WIP types still match.
    """
    if not task.action_date:
        return
    task = WipTask.objects.select_related(
        'wip_order__sodetail', 'wip_order__somain', 'checkpoint',
    ).get(pk=task.pk)
    product_id = getattr(task.wip_order.sodetail, 'product_id', None)
    if not product_id:
        return
    checkpoint_label = getattr(task.checkpoint, 'label', None)
    if not checkpoint_label:
        return
    somain = task.wip_order.somain
    if not somain or not getattr(somain, 'sc_date', None):
        return
    sc_date = somain.sc_date.date() if hasattr(somain.sc_date, 'date') else somain.sc_date
    low = sc_date - timedelta(days=30)
    high = sc_date + timedelta(days=30)
    others = WipTask.objects.filter(
        checkpoint__label=checkpoint_label,
        wip_order__sodetail__product_id=product_id,
        wip_order__somain__sc_date__date__gte=low,
        wip_order__somain__sc_date__date__lte=high,
    ).exclude(id=task.id).select_related('wip_order')
    for other in others:
        other.action_date = task.action_date
        other.status = task.status
        other.save()


class WipDashboardView(LoginRequiredMixin, View):
    """WIP dashboard with planned/action dates and KPI."""

    login_url = reverse_lazy('orders:login')

    def get(self, request):
        sc_number = request.GET.get('sc_number', '').strip()
        cust_order = request.GET.get('cust_order', '').strip()
        sc_date_from = request.GET.get('sc_date_from', '').strip()
        sc_date_to = request.GET.get('sc_date_to', '').strip()
        order_date_from = request.GET.get('order_date_from', '').strip()
        order_date_to = request.GET.get('order_date_to', '').strip()
        crd_from = request.GET.get('crd_from', '').strip()
        crd_to = request.GET.get('crd_to', '').strip()
        critical_date_from = request.GET.get('critical_date_from', '').strip()
        critical_date_to = request.GET.get('critical_date_to', '').strip()
        department_code = request.GET.get('department', '').strip()
        global_q = request.GET.get('q', '').strip()

        profile = getattr(request.user, 'orders_profile', None)
        is_supervisor = bool(profile and profile.is_supervisor and profile.department)
        supervisor_department = profile.department if is_supervisor else None

        if is_supervisor:
            orders_qs = WipOrder.objects.filter(department=supervisor_department)
        else:
            orders_qs = WipOrder.objects.filter(assigned_user=request.user)

        # Advanced filters based on SOMain fields (SC number, dates, customer order, department)
        if sc_number:
            orders_qs = orders_qs.filter(sodetail__sc_number__icontains=sc_number)
        if cust_order:
            orders_qs = orders_qs.filter(somain__cust_order__icontains=cust_order)
        if department_code:
            orders_qs = orders_qs.filter(department__code=department_code)

        if order_date_from:
            try:
                orders_qs = orders_qs.filter(somain__order_date__date__gte=order_date_from)
            except ValueError:
                pass
        if order_date_to:
            try:
                orders_qs = orders_qs.filter(somain__order_date__date__lte=order_date_to)
            except ValueError:
                pass
        if sc_date_from:
            try:
                orders_qs = orders_qs.filter(somain__sc_date__date__gte=sc_date_from)
            except ValueError:
                pass
        if sc_date_to:
            try:
                orders_qs = orders_qs.filter(somain__sc_date__date__lte=sc_date_to)
            except ValueError:
                pass
        if crd_from:
            try:
                orders_qs = orders_qs.filter(somain__crd__date__gte=crd_from)
            except ValueError:
                pass
        if crd_to:
            try:
                orders_qs = orders_qs.filter(somain__crd__date__lte=crd_to)
            except ValueError:
                pass

        # Critical Date: filter by checkpoint planned_date (searches all checkpoint records)
        if critical_date_from:
            try:
                orders_qs = orders_qs.filter(tasks__planned_date__gte=critical_date_from).distinct()
            except ValueError:
                pass
        if critical_date_to:
            try:
                orders_qs = orders_qs.filter(tasks__planned_date__lte=critical_date_to).distinct()
            except ValueError:
                pass

        if global_q:
            detail_sc_numbers = (
                SODetail.objects.filter(
                    Q(sc_number__icontains=global_q)
                    | Q(product_id__icontains=global_q)
                    | Q(cust_item_code__icontains=global_q)
                    | Q(supplier_id__icontains=global_q)
                    | Q(product_name__icontains=global_q)
                    | Q(item_description__icontains=global_q)
                    | Q(supplier_item_code__icontains=global_q)
                    | Q(bmi_item_code__icontains=global_q)
                    | Q(french_item_code__icontains=global_q)
                    | Q(brand__icontains=global_q)
                )
                .values_list('sc_number', flat=True)
                .distinct()
            )
            orders_qs = orders_qs.filter(
                Q(somain__sc_number__icontains=global_q)
                | Q(somain__created_by__icontains=global_q)
                | Q(somain__cust_order__icontains=global_q)
                | Q(somain__user_id__icontains=global_q)
                | Q(somain__cu_code__icontains=global_q)
                | Q(sodetail__sc_number__in=detail_sc_numbers)
            )

        orders_qs = orders_qs.select_related('somain', 'sodetail', 'wip_type', 'department', 'assigned_user')

        # Checkpoints: supervisors see all checkpoints for their department;
        # regular users see only checkpoints for WIP types actually used by their WIP orders.
        if is_supervisor and supervisor_department:
            checkpoints_qs = WipCheckpointDefinition.objects.filter(
                wip_type__department=supervisor_department,
                wip_type__is_active=True,
            )
        else:
            wip_type_ids = list(
                orders_qs.values_list('wip_type_id', flat=True).distinct(),
            )
            if wip_type_ids:
                checkpoints_qs = WipCheckpointDefinition.objects.filter(
                    wip_type_id__in=wip_type_ids,
                    wip_type__is_active=True,
                )
            else:
                checkpoints_qs = WipCheckpointDefinition.objects.none()

        checkpoints = list(checkpoints_qs.order_by('wip_type__name', 'order'))

        unique_labels = []
        inspection_detail_labels = set()
        inspection_simple_labels = set()
        for cp in checkpoints:
            if cp.label not in unique_labels:
                unique_labels.append(cp.label)
            label_upper = cp.label.upper()
            if 'INSPECTION' in label_upper:
                # Labels like "INSPECTION - Inspection Date" get full UI (date + by + result)
                if 'DATE' in label_upper:
                    inspection_detail_labels.add(cp.label)
                else:
                    # Labels like "INSPECTION - Booking" get date-only UI (no inspected by/result)
                    inspection_simple_labels.add(cp.label)

        orders_qs = orders_qs.order_by('sodetail__sc_number', 'sodetail__product_id')
        paginator = Paginator(orders_qs, 50)
        page_obj = paginator.get_page(request.GET.get('page'))

        task_prefetch = Prefetch(
            'tasks',
            queryset=WipTask.objects.select_related('checkpoint'),
        )
        page_orders = page_obj.object_list.prefetch_related(task_prefetch)

        rows = []
        today = date.today()
        for order in page_orders:
            task_map = {}
            for task in order.tasks.all():
                critical_class = ''
                if task.action_date:
                    critical_class = 'critical-done'
                elif task.planned_date:
                    days_left = (task.planned_date - today).days
                    if days_left <= 0:
                        critical_class = 'critical-overdue'
                    elif 7 <= days_left <= 14:
                        critical_class = 'critical-warning'
                task.critical_class = critical_class
                task_map[task.checkpoint.label] = task
            rows.append({
                'order': order,
                'tasks': {label: task_map.get(label) for label in unique_labels},
            })

        departments = list(Department.objects.order_by('name', 'code'))
        team_users = []
        if is_supervisor and supervisor_department:
            # Users in the same department as the supervisor (for assigning WIP orders)
            team_users = list(
                UserModel.objects.filter(orders_profile__department=supervisor_department)
                .order_by('username')
            )
        show_advanced = request.GET.get('advanced') == '1' or any([
            sc_number,
            cust_order,
            sc_date_from,
            sc_date_to,
            order_date_from,
            order_date_to,
            crd_from,
            crd_to,
            critical_date_from,
            critical_date_to,
            department_code,
        ])

        # Preserve filters in pagination links
        get_copy = request.GET.copy()
        if 'page' in get_copy:
            get_copy.pop('page')
        pagination_query = get_copy.urlencode()

        context = {
            'rows': rows,
            'checkpoint_labels': unique_labels,
            'page_obj': page_obj,
            'departments': departments,
            'team_users': team_users,
            'is_supervisor': is_supervisor,
            'show_advanced': show_advanced,
            'pagination_query': pagination_query,
            'filters': {
                'sc_number': sc_number,
                'cust_order': cust_order,
                'sc_date_from': sc_date_from,
                'sc_date_to': sc_date_to,
                'order_date_from': order_date_from,
                'order_date_to': order_date_to,
                'crd_from': crd_from,
                'crd_to': crd_to,
                'critical_date_from': critical_date_from,
                'critical_date_to': critical_date_to,
                'department': department_code,
                'q': global_q,
            },
            'inspection_detail_labels': inspection_detail_labels,
            'inspection_simple_labels': inspection_simple_labels,
        }
        return render(request, 'orders/wip_dashboard.html', context)

    def post(self, request):
        updated = 0
        for key, value in request.POST.items():
            # Supervisor can also assign WIP orders via assigned_<order_id> fields
            if key.startswith('assigned_'):
                profile = getattr(request.user, 'orders_profile', None)
                if not (profile and profile.is_supervisor and profile.department):
                    continue
                try:
                    _, order_id_str = key.split('_', 1)
                    order_id = int(order_id_str)
                except (ValueError, TypeError):
                    continue

                try:
                    wip_order = WipOrder.objects.select_related('department').get(id=order_id)
                except WipOrder.DoesNotExist:
                    continue

                # Only allow assigning orders in the supervisor's own department
                if wip_order.department != profile.department:
                    continue

                user_id = value.strip()
                if user_id:
                    try:
                        user_obj = UserModel.objects.get(id=int(user_id))
                    except (ValueError, UserModel.DoesNotExist):
                        continue
                    wip_order.assigned_user = user_obj
                else:
                    wip_order.assigned_user = None

                wip_order.save(update_fields=['assigned_user'])
                updated += 1
                continue

            if (
                not key.startswith('planned_')
                and not key.startswith('action_')
                and not key.startswith('inspection_by_')
                and not key.startswith('inspection_result_')
            ):
                continue
            # All task-related fields share the same numeric suffix
            try:
                _, task_suffix = key.split('_', 1)
                task_id = int(task_suffix)
            except (ValueError, TypeError):
                continue

            try:
                task = WipTask.objects.select_related('wip_order').get(id=task_id)
            except WipTask.DoesNotExist:
                continue

            profile = getattr(request.user, 'orders_profile', None)
            if profile and profile.is_supervisor:
                if task.wip_order.department != profile.department:
                    continue
            elif task.wip_order.assigned_user != request.user:
                continue

            if key.startswith('planned_'):
                if value:
                    try:
                        task.planned_date = date.fromisoformat(value)
                    except ValueError:
                        continue
                else:
                    task.planned_date = None
            elif key.startswith('action_'):
                if value:
                    try:
                        task.action_date = date.fromisoformat(value)
                        task.status = 'completed'
                    except ValueError:
                        continue
                else:
                    # Don't clear action_date when form value is empty - otherwise we overwrite
                    # action dates that were just propagated from another row (same product, same checkpoint).
                    continue
            elif key.startswith('inspection_by_'):
                # Simple assignment; empty string clears
                task.inspection_by = value or None
            elif key.startswith('inspection_result_'):
                task.inspection_result = value or None

            task.save()
            if key.startswith('action_') and task.action_date:
                _propagate_checkpoint_action_date(task)
            updated += 1

        page = request.POST.get('page', '')
        redirect_url = 'orders:wip-dashboard'
        if page:
            return redirect(f"{reverse_lazy(redirect_url)}?page={page}")
        return redirect(redirect_url)


class WipTaskEditView(LoginRequiredMixin, View):
    """Edit a single WIP checkpoint (task): planned date, action date, status."""

    login_url = reverse_lazy('orders:login')

    def _can_edit_task(self, request, task):
        profile = getattr(request.user, 'orders_profile', None)
        if profile and profile.is_supervisor and profile.department:
            return task.wip_order.department == profile.department
        return task.wip_order.assigned_user == request.user

    def get(self, request, task_id):
        task = get_object_or_404(
            WipTask.objects.select_related(
                'wip_order', 'wip_order__sodetail', 'wip_order__somain', 'wip_order__department',
                'checkpoint', 'checkpoint__wip_type',
            ),
            id=task_id,
        )
        if not self._can_edit_task(request, task):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        return render(request, 'orders/wip_task_edit.html', {
            'task': task,
            'status_choices': WipTask.STATUS_CHOICES,
        })

    def post(self, request, task_id):
        task = get_object_or_404(WipTask.objects.select_related('wip_order'), id=task_id)
        if not self._can_edit_task(request, task):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied

        planned_val = request.POST.get('planned_date', '').strip()
        action_val = request.POST.get('action_date', '').strip()
        status_val = request.POST.get('status', task.status or 'pending').strip()

        if planned_val:
            try:
                task.planned_date = date.fromisoformat(planned_val)
            except ValueError:
                pass
        else:
            task.planned_date = None
        if action_val:
            try:
                task.action_date = date.fromisoformat(action_val)
            except ValueError:
                pass
        else:
            task.action_date = None
        if status_val in dict(WipTask.STATUS_CHOICES):
            task.status = status_val

        task.save()
        if task.action_date:
            _propagate_checkpoint_action_date(task)
        return redirect('orders:wip-task-edit', task_id=task.id)


def _get_inspection_labels_for_tasks(tasks):
    """Build inspection_detail_labels and inspection_simple_labels from task checkpoints."""
    inspection_detail_labels = set()
    inspection_simple_labels = set()
    for task in tasks:
        label_upper = task.checkpoint.label.upper()
        if 'INSPECTION' in label_upper:
            if 'DATE' in label_upper:
                inspection_detail_labels.add(task.checkpoint.label)
            else:
                inspection_simple_labels.add(task.checkpoint.label)
    return inspection_detail_labels, inspection_simple_labels


class WipOrderEditView(LoginRequiredMixin, View):
    """Edit all checkpoints for a WIP order."""

    login_url = reverse_lazy('orders:login')

    def _check_access(self, request, wip_order):
        profile = getattr(request.user, 'orders_profile', None)
        if profile and profile.is_supervisor and profile.department:
            return wip_order.department == profile.department
        return wip_order.assigned_user_id == request.user.id

    def get(self, request, order_id):
        wip_order = get_object_or_404(WipOrder, id=order_id)
        if not self._check_access(request, wip_order):
            return redirect('orders:wip-dashboard')
        tasks = wip_order.tasks.select_related('checkpoint').order_by('checkpoint__order')
        inspection_detail_labels, inspection_simple_labels = _get_inspection_labels_for_tasks(tasks)
        profile = getattr(request.user, 'orders_profile', None)
        is_supervisor = bool(profile and profile.is_supervisor and profile.department)
        team_users = []
        if is_supervisor and profile.department:
            team_users = list(
                UserModel.objects.filter(orders_profile__department=profile.department)
                .order_by('username')
            )
        return render(request, 'orders/wip_edit.html', {
            'wip_order': wip_order,
            'tasks': tasks,
            'inspection_detail_labels': inspection_detail_labels,
            'inspection_simple_labels': inspection_simple_labels,
            'is_supervisor': is_supervisor,
            'team_users': team_users,
            'status_choices': WipTask.STATUS_CHOICES,
        })

    def post(self, request, order_id):
        wip_order = get_object_or_404(WipOrder, id=order_id)
        if not self._check_access(request, wip_order):
            return redirect('orders:wip-dashboard')
        tasks = wip_order.tasks.select_related('checkpoint').order_by('checkpoint__order')

        if 'assigned_user' in request.POST and getattr(
            getattr(request.user, 'orders_profile', None), 'is_supervisor', False
        ):
            profile = request.user.orders_profile
            if profile.department and wip_order.department == profile.department:
                user_id = request.POST.get('assigned_user', '').strip()
                if user_id:
                    try:
                        wip_order.assigned_user = UserModel.objects.get(id=int(user_id))
                    except (ValueError, UserModel.DoesNotExist):
                        wip_order.assigned_user = None
                else:
                    wip_order.assigned_user = None
                wip_order.save(update_fields=['assigned_user'])

        for key, value in request.POST.items():
            if (
                not key.startswith('planned_')
                and not key.startswith('action_')
                and not key.startswith('inspection_by_')
                and not key.startswith('inspection_result_')
                and not key.startswith('status_')
            ):
                continue
            try:
                _, task_suffix = key.split('_', 1)
                task_id = int(task_suffix)
            except (ValueError, TypeError):
                continue
            try:
                task = WipTask.objects.select_related('wip_order').get(id=task_id)
            except WipTask.DoesNotExist:
                continue
            if task.wip_order_id != wip_order.id:
                continue
            if key.startswith('planned_'):
                if value:
                    try:
                        task.planned_date = date.fromisoformat(value)
                    except ValueError:
                        pass
                else:
                    task.planned_date = None
            elif key.startswith('action_'):
                if value:
                    try:
                        task.action_date = date.fromisoformat(value)
                        task.status = 'completed'
                    except ValueError:
                        pass
                else:
                    continue
            elif key.startswith('inspection_by_'):
                task.inspection_by = value or None
            elif key.startswith('inspection_result_'):
                task.inspection_result = value or None
            elif key.startswith('status_'):
                if value in dict(WipTask.STATUS_CHOICES):
                    task.status = value
            task.save()
            if key.startswith('action_') and task.action_date:
                _propagate_checkpoint_action_date(task)
        return redirect('orders:wip-edit', order_id=order_id)


class WipAdminView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Admin menu: manage WIP types and checkpoints per team (department)."""

    login_url = reverse_lazy('orders:login')

    def test_func(self):
        return self.request.user.is_staff

    def get(self, request):
        departments = (
            Department.objects
            .prefetch_related(
                'wip_types__checkpoints',
            )
            .order_by('name', 'code')
        )
        # Build changelist URLs for Django admin (optional: only if user has permission)
        wip_type_changelist = None
        wip_checkpoint_changelist = None
        if request.user.is_staff:
            try:
                from django.urls import reverse
                wip_type_changelist = reverse('admin:orders_wiptypedefinition_changelist')
                wip_checkpoint_changelist = reverse('admin:orders_wipcheckpointdefinition_changelist')
            except Exception:
                pass

        team_data = []
        for dept in departments:
            wip_types = list(dept.wip_types.filter(is_active=True).order_by('name'))
            wip_types_inactive = list(dept.wip_types.filter(is_active=False).order_by('name'))
            team_data.append({
                'department': dept,
                'wip_types': wip_types,
                'wip_types_inactive': wip_types_inactive,
                'wip_type_count': len(wip_types) + len(wip_types_inactive),
            })

        context = {
            'team_data': team_data,
            'wip_type_changelist': wip_type_changelist,
            'wip_checkpoint_changelist': wip_checkpoint_changelist,
        }
        return render(request, 'orders/wip_admin.html', context)
