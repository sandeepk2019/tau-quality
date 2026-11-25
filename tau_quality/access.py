"""Module access for the Tau Power ERP home page and module workspaces.

The module list, its grouping and the role grants follow the client demo
(Tau-Power-ERP-Demo.html, ACL block). 'rw' = create and edit, 'r' = read only.
Keys are the demo module keys; each maps to the ERP workspace that opens it.
"""

ALL = "all"

MODULES = [
    # key, name, icon, group, workspace
    ("dashboard", "Executive dashboard", "◫", "Overview", "Tau Executive Dashboard"),
    ("crm", "CRM & Programmes", "☎", "Customer", "Tau CRM and Programmes"),
    ("sales", "Sales & Dispatch", "⇪", "Customer", "Tau Sales and Dispatch"),
    ("engineering", "Engineering & APQP", "⚙", "Engineering", "Tau Engineering and APQP"),
    ("docs", "Documents & Flowcharts", "▤", "Engineering", "Tau Documents and Flowcharts"),
    ("suppliers", "Suppliers & Procurement", "⇩", "Supply chain", "Tau Suppliers and Procurement"),
    ("inventory", "Inventory & WMS", "▦", "Supply chain", "Tau Inventory and WMS"),
    ("planning", "MPS / MRP Planning", "◷", "Operations", "Tau MPS and MRP Planning"),
    ("production", "Production & MES", "⚒", "Operations", "Tau Production and MES"),
    ("quality", "Quality Management", "✓", "Operations", "Tau Quality Management"),
    ("maintenance", "Maintenance & Calibration", "🔧", "Operations", "Tau Maintenance and Calibration"),
    ("finance", "Accounts, GST & Tally", "₹", "Finance", "Tau Accounts GST and Tally"),
    ("hr", "HR, Skills & Training", "♟", "People", "Tau HR Skills and Training"),
    ("reports", "Reports & Analytics", "▥", "Insight", "Tau Reports and Analytics"),
    ("admin", "Users, RBAC & Audit", "⚿", "System", "Tau Users RBAC and Audit"),
]

# ERP role -> module grants. Demo role mapping:
#   Executive / CEO = ceo, Engineering = engineering, Production Planner = planner,
#   Warehouse = stores, Shop-floor Operator = operator, Quality Manager = quality,
#   Finance and Tax = finance, Sales and Programme = sales, Read-only Auditor = auditor.
# HR Manager and Projects Manager have no demo role; their grants are our choice.
ROLE_ACL = {
    "System Manager": ALL,
    "Executive / CEO": {
        "dashboard": "rw", "crm": "r", "sales": "r", "engineering": "r", "docs": "r", "suppliers": "r",
        "inventory": "r", "planning": "r", "production": "r", "quality": "r", "maintenance": "r",
        "finance": "r", "hr": "r", "reports": "rw", "admin": "r",
    },
    "Engineering": {
        "dashboard": "r", "crm": "r", "engineering": "rw", "docs": "rw", "production": "r", "quality": "r",
        "maintenance": "r", "inventory": "r", "reports": "r", "hr": "r",
    },
    "Production Planner": {
        "dashboard": "r", "planning": "rw", "production": "rw", "inventory": "r", "sales": "r",
        "suppliers": "r", "engineering": "r", "docs": "r", "reports": "r",
    },
    "Warehouse": {
        "dashboard": "r", "inventory": "rw", "suppliers": "rw", "sales": "rw", "production": "r",
        "docs": "r", "reports": "r",
    },
    "Shop-floor Operator": {"dashboard": "r", "production": "rw", "inventory": "r", "docs": "r", "quality": "r"},
    "Quality Manager": {
        "dashboard": "r", "quality": "rw", "suppliers": "r", "production": "r", "inventory": "r",
        "engineering": "r", "maintenance": "rw", "docs": "rw", "hr": "r", "reports": "r",
    },
    "Finance and Tax": {
        "dashboard": "r", "finance": "rw", "sales": "r", "suppliers": "r", "crm": "r", "hr": "r",
        "reports": "rw", "inventory": "r",
    },
    "Sales and Programme": {
        "dashboard": "r", "crm": "rw", "sales": "rw", "engineering": "r", "finance": "r", "inventory": "r",
        "production": "r", "docs": "r", "reports": "r",
    },
    "Read-only Auditor": "read-all",
    "HR Manager": {"dashboard": "r", "hr": "rw"},
    "Projects Manager": {"dashboard": "r", "crm": "rw", "sales": "r", "planning": "r", "engineering": "r"},
}

RANK = {"r": 1, "rw": 2}


def _expand(acl):
    if acl == ALL:
        return {m[0]: "rw" for m in MODULES}
    if acl == "read-all":
        return {m[0]: "r" for m in MODULES}
    return acl


def module_access(roles):
    """Return {module key: 'rw' | 'r'} for the union of the user's roles."""
    access = {}
    for role in roles:
        if role not in ROLE_ACL:
            continue
        for key, level in _expand(ROLE_ACL[role]).items():
            if RANK[level] > RANK.get(access.get(key), 0):
                access[key] = level
    return access


def workspace_roles(module_key):
    """ERP roles that should see a module workspace (System Manager always)."""
    roles = ["System Manager"]
    for role in ROLE_ACL:
        if role == "System Manager":
            continue
        if module_key in _expand(ROLE_ACL[role]):
            roles.append(role)
    return roles


def workspace_slug(name):
    return name.lower().replace(" ", "-")
