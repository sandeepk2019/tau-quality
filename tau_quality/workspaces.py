"""Fill the 15 Tau module workspaces with the ERPNext records behind each demo module.

Each workspace gets shortcuts (top row), cards (groups of links) and a short description.
Links to doctypes that do not exist on the site are skipped, so the builder is safe to re-run.
Roles are not touched here; they come from access.py.
"""

import json

import frappe

from tau_quality.access import MODULES

# module key -> (shortcuts, cards, description)
# shortcuts: [(doctype, label)]
# cards: [(group label, [(doctype, label)])]
# A target written as ("Workspace", name) links to another workspace instead of a doctype.
LAYOUT = {
    "dashboard": (
        [("Sales Order", "Sales orders"), ("Non Conformance", "NCRs"), ("G8D Report", "8D reports"), ("Work Order", "Work orders")],
        [
            ("Sales and finance", [("Sales Order", "Sales Order"), ("Sales Invoice", "Sales Invoice"), ("Payment Entry", "Payment Entry")]),
            ("Operations and quality", [("Work Order", "Work Order"), ("Non Conformance", "Non Conformance"), ("G8D Report", "G8D Report")]),
            ("Master data", [("Item", "Item"), ("Customer", "Customer"), ("Supplier", "Supplier")]),
        ],
        "Executive view: open orders, receivables, running work orders, open NCRs and 8D reports. The figures on the ERP home page come from the same records.",
    ),
    "crm": (
        [("Lead", "Leads"), ("Opportunity", "Opportunities"), ("Quotation", "Quotations"), ("Customer", "Customers")],
        [
            ("Enquiry to quote", [("Lead", "Lead"), ("Opportunity", "Opportunity"), ("Quotation", "Quotation")]),
            ("Customers and programmes", [("Customer", "Customer"), ("Project", "Project"), ("Task", "Task"), ("Issue", "Customer issue")]),
        ],
        "CRM and programme management: enquiries, quotations, customers and customer programmes.",
    ),
    "sales": (
        [("Sales Order", "Sales orders"), ("Delivery Note", "Dispatch"), ("Sales Invoice", "Invoices"), ("Packing Slip", "Packing slips")],
        [
            ("Orders and dispatch", [("Sales Order", "Sales Order"), ("Delivery Note", "Delivery Note"), ("Packing Slip", "Packing Slip")]),
            ("Invoicing and GST", [("Sales Invoice", "Sales Invoice"), ("Payment Entry", "Payment Entry"), ("Sales Taxes and Charges Template", "Sales tax template"), ("GST Settings", "GST Settings")]),
        ],
        "Sales and dispatch: orders, delivery, invoices and GST e-invoicing.",
    ),
    "engineering": (
        [("Routing", "Routings"), ("Workstation", "Workstations"), ("BOM", "BOMs"), ("Operation", "Operations")],
        [
            ("Routes and BOMs", [("Routing", "Routing"), ("BOM", "BOM"), ("Operation", "Operation"), ("Workstation", "Workstation")]),
            ("APQP and quality plans", [("Quality Procedure", "Quality Procedure"), ("Quality Inspection Template", "Inspection template"), ("Quality Inspection Parameter", "Inspection parameter"), ("Item", "Item")]),
        ],
        "Engineering and APQP: routings, operations, workstations, BOMs and quality plans for the sensor routes.",
    ),
    "docs": (
        [("Quality Procedure", "Procedures"), ("Quality Inspection Template", "Inspection templates"), ("Workspace", "SOP Library"), ("Workspace", "IMS Documents")],
        [
            ("Procedures and flowcharts", [("Quality Procedure", "Quality Procedure"), ("Routing", "Routing flow"), ("Workspace", "SOP Library"), ("Workspace", "IMS Documents")]),
            ("Inspection plans", [("Quality Inspection Template", "Quality Inspection Template"), ("Quality Inspection Parameter", "Quality Inspection Parameter")]),
        ],
        "Documents and flowcharts: SOP and IMS libraries, quality procedures and inspection plans.",
    ),
    "suppliers": (
        [("Purchase Order", "Purchase orders"), ("Supplier", "Suppliers"), ("Material Request", "Material requests"), ("Purchase Receipt", "Goods receipts")],
        [
            ("Procurement", [("Material Request", "Material Request"), ("Supplier Quotation", "Supplier Quotation"), ("Purchase Order", "Purchase Order")]),
            ("Receipts and invoices", [("Purchase Receipt", "Purchase Receipt"), ("Purchase Invoice", "Purchase Invoice")]),
            ("Suppliers", [("Supplier", "Supplier")]),
        ],
        "Suppliers and procurement: requirements, purchase orders, goods receipts, supplier invoices and supplier records.",
    ),
    "inventory": (
        [("Stock Entry", "Stock entries"), ("Bin", "Stock balance"), ("Batch", "Batches"), ("Serial No", "Serial numbers")],
        [
            ("Stock movements", [("Stock Entry", "Stock Entry"), ("Stock Reconciliation", "Stock Reconciliation"), ("Stock Ledger Entry", "Stock Ledger Entry")]),
            ("Traceability", [("Batch", "Batch"), ("Serial No", "Serial No")]),
            ("Masters", [("Item", "Item"), ("Warehouse", "Warehouse")]),
        ],
        "Inventory and WMS: stores, lots and serials with barcode traceability.",
    ),
    "planning": (
        [("Production Plan", "Production plans"), ("Material Request", "Material requests"), ("Work Order", "Work orders"), ("BOM", "BOMs")],
        [
            ("Planning", [("Production Plan", "Production Plan"), ("Material Request", "Material Request"), ("Work Order", "Work Order")]),
            ("Masters", [("BOM", "BOM"), ("Item", "Item")]),
        ],
        "MPS and MRP planning: production plans, material requirements and work orders.",
    ),
    "production": (
        [("Work Order", "Work orders"), ("Job Card", "Job cards"), ("Workstation", "Workstations"), ("Serial No", "Serial numbers")],
        [
            ("Execution", [("Work Order", "Work Order"), ("Job Card", "Job Card"), ("Stock Entry", "Stock Entry")]),
            ("Shop floor", [("Workstation", "Workstation"), ("Operation", "Operation"), ("Serial No", "Serial No")]),
        ],
        "Production and MES: work orders, job cards and serial tracking across the five sensor routes.",
    ),
    "quality": (
        [("Non Conformance", "NCRs"), ("Quality Action", "CAPA actions"), ("G8D Report", "8D reports"), ("Quality Inspection", "Inspections")],
        [
            ("NCR, MRB and CAPA", [("Non Conformance", "Non Conformance"), ("Quality Action", "Quality Action"), ("G8D Report", "G8D Report")]),
            ("Inspection", [("Quality Inspection", "Quality Inspection"), ("Quality Inspection Template", "Inspection template"), ("Quality Procedure", "Quality Procedure")]),
            ("Management review", [("Quality Goal", "Quality Goal"), ("Quality Review", "Quality Review"), ("Quality Meeting", "Quality Meeting"), ("Workflow", "Workflows")]),
        ],
        "Quality management: NCR, MRB, CAPA and 8D records, inspections, procedures and management review.",
    ),
    "maintenance": (
        [("Asset", "Assets"), ("Asset Maintenance", "Maintenance plans"), ("Maintenance Visit", "Visits"), ("Downtime Entry", "Downtime")],
        [
            ("Assets", [("Asset", "Asset"), ("Asset Maintenance", "Asset Maintenance"), ("Asset Repair", "Asset Repair")]),
            ("Calibration and logs", [("Asset Maintenance Log", "Asset Maintenance Log"), ("Maintenance Visit", "Maintenance Visit"), ("Downtime Entry", "Downtime Entry")]),
        ],
        "Maintenance and calibration: gauges and machines, maintenance plans, calibration logs and downtime.",
    ),
    "finance": (
        [("Sales Invoice", "Sales invoices"), ("Purchase Invoice", "Purchase invoices"), ("Payment Entry", "Payments"), ("Journal Entry", "Journal entries")],
        [
            ("Accounts", [("Journal Entry", "Journal Entry"), ("Payment Entry", "Payment Entry"), ("Payment Request", "Payment Request"), ("Bank Transaction", "Bank Transaction")]),
            ("GST and invoices", [("Sales Invoice", "Sales Invoice"), ("Purchase Invoice", "Purchase Invoice"), ("GST Settings", "GST Settings")]),
        ],
        "Accounts, GST and Tally: invoices, payments, journal entries and GST settings.",
    ),
    "hr": (
        [("Employee", "Employees"), ("Attendance", "Attendance"), ("Leave Application", "Leaves"), ("Training Event", "Training events")],
        [
            ("People", [("Employee", "Employee"), ("Attendance", "Attendance"), ("Leave Application", "Leave Application"), ("Salary Slip", "Salary Slip")]),
            ("Skills and training", [("Skill", "Skill"), ("Employee Skill Map", "Employee Skill Map"), ("Training Program", "Training Program"), ("Training Event", "Training Event")]),
            ("Organisation", [("Department", "Department"), ("Designation", "Designation")]),
        ],
        "HR, skills and training: employees, attendance, leaves, skill matrix and training records.",
    ),
    "reports": (
        [("Dashboard", "Dashboards"), ("Number Card", "Number cards"), ("Dashboard Chart", "Charts"), ("Report", "Reports")],
        [
            ("Analytics", [("Dashboard", "Dashboard"), ("Number Card", "Number Card"), ("Dashboard Chart", "Dashboard Chart")]),
            ("Reports", [("Report", "Report")]),
        ],
        "Reports and analytics: dashboards, number cards, charts and reports.",
    ),
    "admin": (
        [("User", "Users"), ("Role", "Roles"), ("Notification Log", "Notifications"), ("Version", "Audit trail")],
        [
            ("Users and roles", [("User", "User"), ("Role", "Role"), ("Workflow", "Workflow")]),
            ("Audit", [("Version", "Version"), ("Notification Log", "Notification Log")]),
        ],
        "Users, RBAC and audit: user accounts, roles, workflows and the audit trail.",
    ),
}


def _target(dt):
    """Return (link type, name) for a doctype name or a ("Workspace", name) pair."""
    if isinstance(dt, tuple):
        return dt[0], dt[1]
    return "DocType", dt


def _exists(dt):
    kind, name = _target(dt)
    return bool(frappe.db.exists(kind, name))


def _slug(text):
    return "".join(c if c.isalnum() else "-" for c in text.lower()).strip("-")


def build(ws_name, shortcuts, cards, description):
    ws = frappe.get_doc("Workspace", ws_name)
    ws.set("shortcuts", [])
    ws.set("links", [])
    blocks = [
        {"id": "hdr", "type": "header", "data": {"text": f"<b>{ws_name}</b>", "col": 12}},
        {"id": "desc", "type": "paragraph", "data": {"text": description, "col": 12}},
    ]
    for i, (dt, label) in enumerate(shortcuts):
        if not _exists(dt):
            continue
        kind, name = _target(dt)
        ws.append("shortcuts", {"label": label, "type": kind, "link_to": name,
                                "doc_view": "List" if kind == "DocType" else ""})
        blocks.append({"id": f"sc{i}", "type": "shortcut", "data": {"shortcut_name": label, "col": 3}})
    for group, items in cards:
        rows = [(dt, label) for dt, label in items if _exists(dt)]
        if not rows:
            continue
        ws.append("links", {"label": group, "type": "Card Break"})
        for dt, label in rows:
            kind, name = _target(dt)
            ws.append("links", {"label": label, "type": "Link", "link_type": kind, "link_to": name, "onboard": 0})
        blocks.append({"id": f"card-{_slug(group)}", "type": "card", "data": {"card_name": group, "col": 4}})
    ws.content = json.dumps(blocks)
    ws.save(ignore_permissions=True)


def build_all():
    for key, _name, _icon, _group, ws_name in MODULES:
        if key not in LAYOUT or not frappe.db.exists("Workspace", ws_name):
            continue
        shortcuts, cards, description = LAYOUT[key]
        build(ws_name, shortcuts, cards, description)
    frappe.db.commit()
