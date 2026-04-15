# QA Workflow Automation System

Product Quality Assurance Workflow Management Platform built with Django 4.x and PostgreSQL.

## Project Overview

This system digitizes the QA team's Excel-based workflow for tracking products (toys/consumer goods) through multiple QA stages:

- **Report/Test Plan (R)** - Initial QA enquiry and test plan
- **Artwork Review & Approval (A)** - Design/artwork review
- **Factory Sample Check (F)** - Initial production sample inspection
- **Mockup/Red Sample Check (M)** - First production run sample
- **Gold Seal/Shipment Sample Check (G)** - Final pre-shipment sample

The system also tracks compliance documentation including:
- DOI (Declaration of Innocence)
- CSA (Chemical Safety Assessment)
- BOM (Bill of Materials)
- DOC (Declaration of Compliance)
- Test Reports (BSEN 71, REACH, Cadmium, Phthalates, PAHs, SCCP, etc.)

## Technology Stack

- **Django 4.x**
- **PostgreSQL 14+**
- **Python 3.9+**
- **Windows Server 2019/2022** (Native deployment, no Docker)

## Installation

### Prerequisites

1. Python 3.9 or higher
2. PostgreSQL 14 or higher
3. pip (Python package manager)

### Setup Steps

1. **Navigate to project directory**:
   ```bash
   cd C:\dev\qa_workflow_automation
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   venv\Scripts\activate  # On Windows
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure PostgreSQL database**:
   - Create a database named `qa_workflow_db`
   - Update database credentials in `qa_workflow/settings.py` if needed:
     ```python
     DATABASES = {
         'default': {
             'ENGINE': 'django.db.backends.postgresql',
             'NAME': 'qa_workflow_db',
             'USER': 'postgres',
             'PASSWORD': 'your_password',
             'HOST': 'localhost',
             'PORT': '5432',
         }
     }
     ```

5. **Run migrations**:
   ```bash
   python manage.py migrate
   ```

6. **Create a superuser**:
   ```bash
   python manage.py createsuperuser
   ```

7. **Create initial QA stages for products** (optional):
   ```bash
   python manage.py create_initial_stages
   ```

8. **Run the development server**:
   ```bash
   python manage.py runserver
   ```

9. **Access the application**:
   - Admin interface: http://127.0.0.1:8000/admin/
   - Dashboard: http://127.0.0.1:8000/

## Importing Data from Excel

To import products from your existing Excel template:

```bash
python manage.py import_excel path/to/your/excel_file.xlsx --sheet "MTL (2)"
```

Options:
- `--sheet`: Sheet name to import from (default: "MTL (2)")
- `--dry-run`: Preview what would be imported without saving to database

Example:
```bash
python manage.py import_excel "C:\Users\ricky_lai\Downloads\qa_data.xlsx" --sheet "MTL (2)"
```

## Project Structure

```
C:\dev\qa_workflow_automation\
├── manage.py
├── requirements.txt
├── README.md
├── .gitignore
├── qa_workflow/          # Main project settings
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── qa_app/               # Main application
│   ├── __init__.py
│   ├── admin.py         # Django admin configuration
│   ├── apps.py
│   ├── models.py        # Product, ProductStage, ComplianceDocument, etc.
│   ├── views.py         # Dashboard and product views
│   ├── urls.py
│   └── management/
│       └── commands/
│           ├── import_excel.py      # Excel import command
│           └── create_initial_stages.py
└── templates/
    └── qa_app/          # HTML templates
        ├── dashboard.html
        ├── product_list.html
        └── product_detail.html
```

## Key Features

### Product Management
- Track products by BMUK Item No. and MTL Ref NO.
- Material-based classification (Plastic, Fabric, Cosmetic, Wood, Slime, etc.)
- Supplier information and FOB port tracking
- Product images and specifications
- Test requirements tracking

### QA Stages Workflow
- Five predefined stages (R/A/F/M/G)
- Stage status tracking (Not Started, In Progress, Completed, On Hold, Rejected)
- Completion dates and notes for each stage
- Artwork status management

### Compliance Documentation
- Multiple document types (DOI, CSA, BOM, DOC, Test Reports)
- ITS reference number tracking
- Test result status (OK, Failed, Pending, N/A)
- File uploads for certificates and reports
- Expiry date tracking

### Test Requirements
- Material-specific test requirements
- Test status tracking
- ITS reference numbers
- Required stage association

### Dashboard
- QA owner dashboard with assigned products
- Stage pipeline visualization
- Missing compliance document alerts
- Product status overview

## Usage

### Adding a New Product

1. Go to Admin → Products → Add Product
2. Fill in all required fields:
   - BMUK Item No. (unique identifier)
   - MTL Ref NO. (internal tracking)
   - Description
   - Material Type
   - Supplier Information
   - Dates (Merchant Enquiry Date, Shipdate CRD)
3. Assign to a QA In-charge user
4. Save - initial stages will be created automatically

### Managing QA Stages

1. Navigate to a product detail page
2. Stages are automatically created (R/A/F/M/G)
3. Update stage status and completion dates as work progresses
4. Add notes for each stage (e.g., Artwork Status)

### Uploading Compliance Documents

1. Go to Admin → Compliance Documents → Add Compliance Document
2. Select the product
3. Choose document type
4. Upload file and fill in test information (if applicable)
5. Set last update date and expiry date (if applicable)

### Importing from Excel

The system can import products from your existing Excel templates. The import command maps Excel columns to system fields as specified in the project plan.

## Windows Server Deployment

For production deployment on Windows Server:

1. **Install Python and PostgreSQL** on the server
2. **Set up IIS** with wfastcgi or use Django's development server for internal use
3. **Configure static files**:
   ```bash
   python manage.py collectstatic
   ```
4. **Set DEBUG = False** in `settings.py`
5. **Configure ALLOWED_HOSTS** with your server domain/IP
6. **Set up Windows Task Scheduler** for ERP sync jobs (future implementation)

## ERP Integration (Future)

The system includes models for ERP integration:
- `ERPOrder` - Order data from FoxPro
- `ERPShipment` - Shipment tracking

Scheduled sync tasks will be implemented to pull data from FoxPro database.

## Development Notes

- Media files are stored in `media/` directory
- Static files are collected to `staticfiles/` directory
- Database migrations should be run after model changes
- Admin interface is the primary interface for data entry

## Support

For issues or questions, refer to the project plan document: `qa_requirements_updated.md`

## License

Internal use only - Quality Assurance Department
