import frappe

from tau_quality.access import MODULES, workspace_roles


def execute():
    """Limit each Tau module workspace to the ERP roles granted in access.py (demo ACL),
    and make the site home page the Tau home (www/home.html), which shows sign-in to guests."""
    for key, _name, _icon, _group, ws_name in MODULES:
        if not frappe.db.exists("Workspace", ws_name):
            continue
        roles = [r for r in workspace_roles(key) if frappe.db.exists("Role", r)]
        ws = frappe.get_doc("Workspace", ws_name)
        ws.set("roles", [{"role": r} for r in roles])
        ws.save(ignore_permissions=True)

    frappe.db.set_single_value("Website Settings", "home_page", "home")
    frappe.db.commit()
