import frappe
from frappe.utils import flt, getdate, nowdate
from urllib.parse import quote

from tau_quality.access import MODULES, ROLE_ACL, module_access, workspace_slug

ROUTE_OF = {m[0]: "/app/" + workspace_slug(m[4]) for m in MODULES}
ROLE_ACL_ORDER = [r for r in ROLE_ACL if r != "System Manager"] + ["System Manager"]


def _rows(doctype, filters, fields):
    """Rows the user may read. Returns None when the user cannot read the doctype."""
    try:
        return frappe.get_list(doctype, filters=filters, fields=fields, limit_page_length=0)
    except frappe.PermissionError:
        return None


def _kpi(key, label, value, sub, link, kind="count", cls=""):
    return {"module": key, "label": label, "value": value, "sub": sub, "link": link, "kind": kind, "cls": cls}


def _kpis(access):
    today = getdate(nowdate())
    out = []

    def add(key, build):
        if key not in access:
            return
        try:
            item = build()
        except frappe.PermissionError:
            return
        if item:
            out.append(item)

    def sales_orders():
        rows = _rows("Sales Order", {"docstatus": 1, "status": ["not in", ["Completed", "Closed"]]},
                     ["name", "delivery_date"])
        if rows is None:
            return None
        late = sum(1 for r in rows if r.delivery_date and getdate(r.delivery_date) < today)
        return _kpi("sales", "Open sales orders", len(rows), f"{late} past due date", ROUTE_OF["sales"],
                    cls="warn" if late else "ok")

    def receivables():
        rows = _rows("Sales Invoice", {"docstatus": 1, "outstanding_amount": [">", 0]}, ["outstanding_amount"])
        if rows is None:
            return None
        total = sum(flt(r.outstanding_amount) for r in rows)
        return _kpi("finance", "Receivables", total, f"{len(rows)} invoices open", ROUTE_OF["finance"], kind="money")

    def work_orders():
        rows = _rows("Work Order", {"status": "In Process"}, ["name"])
        if rows is None:
            return None
        return _kpi("production", "Work orders running", len(rows), "status: In Process", ROUTE_OF["production"])

    def ncrs():
        rows = _rows("Non Conformance", {"workflow_state": ["not in", ["Closed", "Cancelled"]]}, ["name"])
        if rows is None:
            return None
        return _kpi("quality", "Open NCRs", len(rows), "MRB, rework and CAPA", ROUTE_OF["quality"],
                    cls="bad" if rows else "ok")

    def eight_d():
        rows = _rows("G8D Report", {"status": ["!=", "Closed"]}, ["name"])
        if rows is None:
            return None
        return _kpi("quality", "Open 8D reports", len(rows), "sign-off pending or in progress", ROUTE_OF["quality"],
                    cls="warn" if rows else "ok")

    def items():
        rows = _rows("Item", {"disabled": 0}, ["name"])
        if rows is None:
            return None
        return _kpi("inventory", "Active items", len(rows), "masters in ERP", ROUTE_OF["inventory"])

    def customers():
        rows = _rows("Customer", {"disabled": 0}, ["name"])
        if rows is None:
            return None
        return _kpi("crm", "Customers", len(rows), "active accounts", ROUTE_OF["crm"])

    def suppliers():
        rows = _rows("Supplier", {"disabled": 0}, ["name"])
        if rows is None:
            return None
        return _kpi("suppliers", "Suppliers", len(rows), "active accounts", ROUTE_OF["suppliers"])

    def operations():
        rows = _rows("Operation", {"name": ["like", "OP-%"]}, ["name"])
        if rows is None:
            return None
        return _kpi("engineering", "Shop-floor operations", len(rows), "OP-40 to OP-290", ROUTE_OF["engineering"])

    for key, build in [("sales", sales_orders), ("finance", receivables), ("production", work_orders),
                       ("quality", ncrs), ("quality", eight_d), ("inventory", items), ("crm", customers),
                       ("suppliers", suppliers), ("engineering", operations)]:
        add(key, build)
    return out


def _orders(access):
    if "sales" not in access:
        return None
    rows = _rows("Sales Order", {"docstatus": 1, "status": ["not in", ["Completed", "Closed"]]},
                 ["name", "customer_name", "delivery_date", "status", "grand_total"])
    if rows is None:
        return None
    today = getdate(nowdate())
    rows.sort(key=lambda r: (r.delivery_date is None, r.delivery_date))
    return [{
        "name": r.name,
        "customer": r.customer_name,
        "delivery_date": str(r.delivery_date) if r.delivery_date else None,
        "late": bool(r.delivery_date and getdate(r.delivery_date) < today),
        "status": r.status,
        "grand_total": flt(r.grand_total),
    } for r in rows[:8]]


def _alerts(user):
    rows = frappe.get_list(
        "Notification Log",
        filters={"for_user": user},
        fields=["subject", "document_type", "document_name", "creation", "read"],
        order_by="creation desc",
        limit_page_length=9,
    )
    return [{
        "subject": r.subject,
        "document_type": r.document_type,
        "document_name": r.document_name,
        "creation": str(r.creation),
        "read": bool(r.read),
    } for r in rows]


@frappe.whitelist(allow_guest=True)
def home_data():
    """Data for the ERP home page. Guests get no user, so the page shows sign-in."""
    user = frappe.session.user
    if user == "Guest":
        return {"user": None}

    roles = sorted(r for r in frappe.get_roles(user) if r not in ("All", "Guest"))
    access = module_access(roles)

    modules = []
    for key, name, icon, group, _ws in MODULES:
        if key in access:
            modules.append({
                "key": key, "name": name, "ic": icon, "group": group,
                "route": ROUTE_OF[key], "access": access[key],
            })

    primary = next((r for r in ROLE_ACL_ORDER if r in roles), "User")
    return {
        "user": user,
        "full_name": frappe.get_cached_value("User", user, "full_name") or user,
        "title": primary,
        "roles": roles,
        "modules": modules,
        "kpis": _kpis(access),
        "orders": _orders(access),
        "alerts": _alerts(user),
    }
