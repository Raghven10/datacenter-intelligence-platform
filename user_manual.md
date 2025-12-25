# Datacenter Intelligence Platform - User Manual

Welcome to the **Datacenter Intelligence Platform (DI Platform)**. This manual provides a module-wise breakdown of the application's features and functionalities.

---

## 🔐 Authentication & Access

### Login Page
The entry point of the application. Ensure you have valid credentials assigned by the System Administrator.

![Login Page](/static/images/manual/login_page_1766646784825.png)

- **Default Sysadmin:** `syaadmin` / `Test@12345`
- **Security:** CSRF protection and JWT-based session management are active.

---

## 📊 Command Center (Dashboard)
The central analytical hub providing real-time overview of the datacenter health.

![Dashboard](/static/images/manual/dashboard_1766646870025.png)

- **KPI Cards:** Monitor total assets, unserviceable equipment, and active workflows.
- **Visual Analytics:** Interactive charts for equipment health distribution.
- **Activity Feed:** Quick look at recent system events.

---

## 🏗️ Asset Management

### Facility Locations
Manage the physical hierarchy of your datacenter.

![Facility Locations](/static/images/manual/places_1766646885528.png)

- Group equipments by building, floor, room, or rack.
- View equipment count per location at a glance.

### Equipment Inventory
A detailed list of all technical assets in the facility.

![Equipment List](/static/images/manual/equipment_list_1766646898631.png)

- Track serviceability and operational status (ON/OFF) for every item.
- Filter by type or location to find specific assets.

---

## 📝 Operations & Inspections

### New Inspection Log
The primary tool for operators to record daily technical parameters.

![New Inspection](/static/images/manual/di_form_1766646915169.png)

- **Modular Inputs:** Log pressure, temperature, voltage, and health for each component.
- **Escalation:** Forward reports to specific roles (e.g., OIC Elect) for review.
- **Auto-Alerts:** Marking an item as "Unserviceable" triggers immediate system alerts.

### Workflow Tracking
Monitor the lifecycle of inspection reports.

![Workflow Tracking](/static/images/manual/workflow_tracking_1766646931048.png)

- **Timeline view:** History of all actions (Submission -> Approval -> Finalization).
- **Nudge Feature:** Notify responsible personnel if a report is pending their action.

---

## ⚙️ Administration

### User Directory
Manage platform users and their primary access levels.

![User Directory](/static/images/manual/user_directory_1766646949904.png)

- Create, edit, or deactivate user accounts.
- Assign primary roles for system-wide permissions.

### Access Roles (RBAC)
Configure the Role-Based Access Control system.

![Access Roles](/static/images/manual/access_roles_1766646966829.png)

- Define roles like `OIC Elect`, `CDO`, and `Sysadmin`.
- Manage fine-grained permissions (Coming Soon).

---

## 📑 User Manual Link
Access this manual anytime from the **Dashboard** or **Login Page**.
