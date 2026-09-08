"""
Modèles SQLAlchemy du Core.

Exporte tous les modèles pour un import centralisé::

    from app.core.models import User, Company, Role
"""
from app.core.database import Base, TenantMixin  # noqa: F401

from app.core.models.company import Agency, Company
from app.core.models.currency import Currency
from app.core.models.tax import Tax
from app.core.models.user import User, UserRole
from app.core.models.role import Permission, Role, RolePermission
from app.core.models.setting import Setting
from app.core.models.sequence import Sequence
from app.core.models.audit_log import AuditLog
from app.core.models.module_info import ModuleInfo

__all__ = [
    "Base",
    "TenantMixin",
    "Company",
    "Agency",
    "Currency",
    "Tax",
    "User",
    "UserRole",
    "Role",
    "Permission",
    "RolePermission",
    "Setting",
    "Sequence",
    "AuditLog",
    "ModuleInfo",
]
