# Admin User Guide – Order Workflow & WIP

This guide explains how to use the Order Workflow system and how to perform admin tasks, including managing Work-in-Progress (WIP) for each team.

---

## 1. Logging in and main menu

- Open the Order Workflow app (e.g. `http://yourserver/orders-workflow/`).
- Log in with your username and password.
- After login you see the **Dashboard** and the main navigation:
  - **Dashboard** – Task summary and recent orders
  - **Orders** – List and search sales orders (SC numbers)
  - **WIP** – Work-in-progress dashboard (planned/action dates and KPI)
  - **Repeat Workflow** / **New Workflow** – Grid-based workflow entries
  - **Preferences** – Your notification and display settings
  - **Admin** – Shown only to staff users; manage WIP by team (see Section 5)

---

## 2. Dashboard

- The dashboard shows tasks assigned to you (or to your team if you are a supervisor).
- You see counts for **Critical**, **Warning**, and **Normal** tasks and recent orders.
- Use **Preferences** to turn daily emails and alert types on/off and to choose your default view (My Tasks, All Orders, Team View).

---

## 3. Orders

- **Orders** lists sales orders (SOMain) with filters: SC number, customer order, dates, department, status, and a global search.
- Click an SC number to open **Order detail**: header (customer, CRD, department, etc.) and line items (SODetail) with product and amounts.
- Access depends on your role:
  - **ADMIN** – All orders
  - **SUPERVISOR** – Orders in your department
  - **NORMAL** – Only your own orders (by User ID)

---

## 4. WIP (Work-in-Progress)

- **WIP** shows order lines that are in progress, with **critical dates** and action dates per checkpoint and KPI.
- **Critical date** = the date by which each checkpoint must be actioned. Missing it risks delaying the CRD (Cargo Ready Date) and shipment.
- **Each user sees only their own WIP** – orders assigned to them (based on who created/modified the order in the system, i.e. the merchandiser / User ID).
- Supervisors see WIP for their entire department.
- You can **edit** critical dates and action dates in the table and click **Save**. Action date = when you completed the checkpoint.
- **Daily alert email** lists checkpoints that reach the critical date today (or are overdue) and reminds you to take action immediately.
- Data is driven by **WIP types** and **checkpoints** defined per team (department), selected by lead time. Only staff can change those definitions (see Section 5).

---

## 5. Admin: Managing WIP for each team (staff only)

If you have **staff** access, you see **Admin** in the main menu.

### 5.1 Opening the WIP management page

- Click **Admin** in the header, or go to:  
  `http://yourserver/orders-workflow/wip/manage/`
- This page lists every **team (department)** and their WIP setup.

### 5.2 What you see per team

For each team (department name and code) the page shows:

- **WIP types** – Each type has a name and a lead-time range (min–max days). Only **active** types are used on the WIP dashboard.
- **Checkpoints** – For each WIP type, the checkpoints (e.g. “Sample approval”, “PP meeting”) with:
  - **Rule type**: CRD offset (days before/after CRD) or Previous checkpoint offset (days after the previous checkpoint)
  - **Offset days**: The number used in that rule

Inactive WIP types are listed separately (greyed out) so you can see the full setup.

### 5.3 How to change WIP setup

- On the WIP management page, use **Edit WIP types in Admin** for a team. That opens Django Admin with the list of WIP types filtered to that department.
- In Django Admin you can:
  - **Add** a WIP type: set Department, name, lead time min/max, and “Is active”.
  - **Edit** a type: change name, lead times, or active flag.
  - **Add** checkpoints: choose WIP type, label, order, rule type (CRD offset / Previous checkpoint offset), and offset days.
  - **Edit** checkpoints: change label, order, rule type, or offset.
- The **Quick links** at the bottom open the full WIP type and checkpoint lists in Django Admin (no department filter).

### 5.4 After changing WIP definitions

- Changing WIP types or checkpoints does not automatically update existing WIP orders.
- Run your usual sync process (e.g. the **sync_wip_orders** management command) so that WIP orders and tasks are updated from the new definitions.

---

## 6. User roles and access (FoxUser)

Access to orders and WIP is based on the **FoxUser** record linked to your username (User ID) and **Department user level**:

- **ADMIN** – Can see all orders and all departments; can use Admin menu (if also Django staff).
- **SUPERVISOR** – Can see all orders in their department; WIP dashboard can show department-wide WIP.
- **NORMAL** – Can see only orders where they are the assigned user (User ID).

User and department data (including FoxUser and Department) are maintained in Django Admin or via your existing import/sync (e.g. from FoxPro).

---

## 7. Using Django Admin for data management

Django Admin (`http://yourserver/admin/`) is used for:

- **Orders app**: Orders, Workflow templates/stages, Order tasks, User dashboard preferences, SOMain, SODetail, Product, Payment term, Customer, FoxUser, Supplier, **Department**, User profile, Workflow grid template/column/entry, **WIP type definition**, **WIP checkpoint definition**, WIP order, WIP task.
- **User management**: Django users and groups (optional).

To manage WIP by team, use either:

- The **Admin** menu in the Order Workflow app (Section 5), which takes you to the right place in Django Admin, or  
- Directly in Admin: **Orders → WIP type definitions** and **WIP checkpoint definitions**, optionally filtering by Department.

---

## 8. Useful management commands (for admins/setup)

Run these from the project directory with your virtual environment activated, e.g.:

```bash
python manage.py <command_name> [options]
```

- **sync_wip_orders** – Create or update WIP orders and tasks from SOMain/SODetail and WIP type/checkpoint definitions.
- **load_wip_definitions** – Load WIP types and checkpoints from an Excel file for a department (e.g. “WIP type definition.xlsx”). Requires `--file` and `--department-code`.
- **send_wip_reminders** – Send WIP reminder emails (if configured).
- **sync_somain** / **import_*** – Data sync/import from your external sources (e.g. FoxPro) as per your deployment docs.

---

## 9. Summary checklist for admins

- **Daily use**: Use Dashboard, Orders, and WIP as needed; set Preferences.
- **WIP setup per team**: Use **Admin → Manage WIP for each team** to see departments and their WIP types/checkpoints, then use “Edit WIP types in Admin” to add or edit in Django Admin.
- **After WIP changes**: Run **sync_wip_orders** (or your equivalent) so WIP orders and tasks reflect the new definitions.
- **Users and departments**: Manage FoxUser, Department, and Django users in Django Admin or via your import process.
- **Troubleshooting**: Check that the user has a FoxUser with the correct Department and Department user level (ADMIN/SUPERVISOR/NORMAL), and that WIP types for that department are **active** and have checkpoints.

---

*Document version: 1.0. For technical setup and installation, see README.md.*
