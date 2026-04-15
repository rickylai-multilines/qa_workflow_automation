"""
Views for QA Workflow application
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.db.models import Q, Count
from .models import Product, ProductStage, ComplianceDocument


class CustomLoginView(LoginView):
    """Custom login view that redirects to dashboard"""
    template_name = 'qa_app/login.html'
    redirect_authenticated_user = True


@login_required
def dashboard(request):
    """QA Owner Dashboard"""
    user = request.user
    
    # Get products assigned to current user
    my_products = Product.objects.filter(assigned_user=user)
    
    # Get products by status
    in_progress = my_products.filter(status='in_progress')
    on_hold = my_products.filter(status='on_hold')
    completed = my_products.filter(status='completed')
    
    # Get products by stage
    stage_stats = {}
    for stage_code, stage_name in ProductStage.STAGE_CHOICES:
        stage_stats[stage_code] = {
            'name': stage_name,
            'count': my_products.filter(qa_stages__stage_type=stage_code, qa_stages__status='in_progress').count()
        }
    
    # Get products with missing compliance documents
    products_with_missing_docs = []
    for product in in_progress:
        required_docs = ['doi', 'csa', 'bom', 'doc']
        existing_docs = set(product.compliance_documents.values_list('document_type', flat=True))
        missing = [doc for doc in required_docs if doc not in existing_docs]
        if missing:
            products_with_missing_docs.append({
                'product': product,
                'missing_docs': missing
            })
    
    context = {
        'my_products': my_products[:10],  # Recent 10
        'in_progress_count': in_progress.count(),
        'on_hold_count': on_hold.count(),
        'completed_count': completed.count(),
        'stage_stats': stage_stats,
        'products_with_missing_docs': products_with_missing_docs[:5],
    }
    
    return render(request, 'qa_app/dashboard.html', context)


@login_required
def product_list(request):
    """List all products with filtering"""
    products = Product.objects.all()
    
    # Filtering
    status_filter = request.GET.get('status')
    material_filter = request.GET.get('material')
    assigned_filter = request.GET.get('assigned')
    search_query = request.GET.get('search')
    
    if status_filter:
        products = products.filter(status=status_filter)
    if material_filter:
        products = products.filter(material_type=material_filter)
    if assigned_filter:
        products = products.filter(assigned_user_id=assigned_filter)
    if search_query:
        products = products.filter(
            Q(bmuk_item_no__icontains=search_query) |
            Q(mtl_ref_no__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(supplier_name__icontains=search_query)
        )
    
    context = {
        'products': products,
        'status_choices': Product._meta.get_field('status').choices,
        'material_choices': Product._meta.get_field('material_type').choices,
    }
    
    return render(request, 'qa_app/product_list.html', context)


@login_required
def product_detail(request, pk):
    """Detailed product view with all stages and compliance documents"""
    product = get_object_or_404(Product, pk=pk)
    
    # Get all stages
    stages = product.qa_stages.all().order_by('stage_type')
    
    # Get compliance documents grouped by type
    compliance_docs = {}
    for doc_type, doc_name in ComplianceDocument.DOC_TYPE_CHOICES:
        docs = product.compliance_documents.filter(document_type=doc_type)
        if docs.exists():
            compliance_docs[doc_type] = docs.first()  # Get most recent
    
    # Get test requirements
    test_requirements = product.test_requirement_items.all()
    
    context = {
        'product': product,
        'stages': stages,
        'compliance_docs': compliance_docs,
        'test_requirements': test_requirements,
    }
    
    return render(request, 'qa_app/product_detail.html', context)

