"""module Achats — fournisseurs, DA, BC, BR, factures fournisseur

Revision ID: f3b7c9d2a1e4
Revises: e8a3c5d1f2b6
Create Date: 2026-10-13

Module Achats (PRD V1) :
- ``partners`` : + ``rating`` (évaluation 1-5), ``delivery_days`` ;
- ``partner_categories`` : classification fournisseur <-> catégories produits ;
- ``purchase_requests`` / ``purchase_request_lines`` : demande d'achat ;
- ``purchase_orders`` / ``purchase_order_lines`` : bon de commande ;
- ``purchase_receptions`` / ``purchase_reception_lines`` : bon de réception ;
- ``supplier_invoices`` / ``supplier_invoice_lines`` : facture fournisseur.

Toutes les créations sont idempotentes (garde ``has_table``).
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3b7c9d2a1e4'
down_revision: Union[str, None] = 'e8a3c5d1f2b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(table: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table)


def _columns(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table):
        return set()
    return {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    # --- 1. Colonnes fournisseur sur partners ------------------------------
    if "rating" not in _columns("partners"):
        with op.batch_alter_table("partners") as batch_op:
            batch_op.add_column(sa.Column("rating", sa.Numeric(3, 2), nullable=True))
    if "delivery_days" not in _columns("partners"):
        with op.batch_alter_table("partners") as batch_op:
            batch_op.add_column(sa.Column("delivery_days", sa.Integer(), nullable=True))

    # --- 2. partner_categories ---------------------------------------------
    if not _has_table("partner_categories"):
        op.create_table(
            "partner_categories",
            sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
            sa.Column("company_id", sa.Integer(),
                      sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
            sa.Column("partner_id", sa.Integer(),
                      sa.ForeignKey("partners.id", ondelete="CASCADE"), nullable=False),
            sa.Column("category_id", sa.Integer(),
                      sa.ForeignKey("product_categories.id", ondelete="CASCADE"), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("created_by", sa.Integer(),
                      sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("updated_by", sa.Integer(),
                      sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.UniqueConstraint("partner_id", "category_id", name="uq_partner_category"),
        )
        op.create_index("ix_partner_categories_partner_id", "partner_categories", ["partner_id"])
        op.create_index("ix_partner_categories_category_id", "partner_categories", ["category_id"])


    # --- 3. Demande d'achat -------------------------------------------------
    if not _has_table("purchase_requests"):
        op.create_table(
            "purchase_requests",
            sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
            sa.Column("company_id", sa.Integer(),
                      sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
            sa.Column("number", sa.String(30), nullable=False, unique=True),
            sa.Column("requester_id", sa.Integer(),
                      sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("validator_id", sa.Integer(),
                      sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("supplier_id", sa.Integer(),
                      sa.ForeignKey("partners.id", ondelete="SET NULL"), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
            sa.Column("priority", sa.String(10), nullable=False, server_default="normal"),
            sa.Column("request_date", sa.Date(), nullable=False),
            sa.Column("needed_by", sa.Date(), nullable=True),
            sa.Column("submitted_at", sa.DateTime(), nullable=True),
            sa.Column("validated_at", sa.DateTime(), nullable=True),
            sa.Column("rejection_reason", sa.Text(), nullable=True),
            sa.Column("estimated_total", sa.Numeric(14, 4), nullable=False, server_default="0"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("created_by", sa.Integer(),
                      sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("updated_by", sa.Integer(),
                      sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        )
        op.create_index("ix_purchase_requests_number", "purchase_requests", ["number"])
        op.create_index("ix_purchase_requests_status", "purchase_requests", ["status"])
        op.create_index("ix_purchase_requests_supplier_id", "purchase_requests", ["supplier_id"])

    if not _has_table("purchase_request_lines"):
        op.create_table(
            "purchase_request_lines",
            sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
            sa.Column("company_id", sa.Integer(),
                      sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
            sa.Column("request_id", sa.Integer(),
                      sa.ForeignKey("purchase_requests.id", ondelete="CASCADE"), nullable=False),
            sa.Column("product_id", sa.Integer(),
                      sa.ForeignKey("products.id", ondelete="SET NULL"), nullable=True),
            sa.Column("description", sa.String(500), nullable=True),
            sa.Column("quantity", sa.Numeric(14, 4), nullable=False, server_default="1"),
            sa.Column("unit", sa.String(30), nullable=True),
            sa.Column("estimated_unit_price", sa.Numeric(14, 4), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("created_by", sa.Integer(),
                      sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("updated_by", sa.Integer(),
                      sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        )
        op.create_index("ix_purchase_request_lines_request_id",
                        "purchase_request_lines", ["request_id"])

    # --- 4. Bon de commande -------------------------------------------------
    if not _has_table("purchase_orders"):
        op.create_table(
            "purchase_orders",
            sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
            sa.Column("company_id", sa.Integer(),
                      sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
            sa.Column("number", sa.String(30), nullable=False, unique=True),
            sa.Column("supplier_id", sa.Integer(),
                      sa.ForeignKey("partners.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("origin_request_id", sa.Integer(),
                      sa.ForeignKey("purchase_requests.id", ondelete="SET NULL"), nullable=True),
            sa.Column("status", sa.String(30), nullable=False, server_default="draft"),
            sa.Column("order_date", sa.Date(), nullable=False),
            sa.Column("expected_date", sa.Date(), nullable=True),
            sa.Column("currency_code", sa.String(3), nullable=False, server_default="XOF"),
            sa.Column("amount_untaxed", sa.Numeric(14, 4), nullable=False, server_default="0"),
            sa.Column("tax_amount", sa.Numeric(14, 4), nullable=False, server_default="0"),
            sa.Column("amount_total", sa.Numeric(14, 4), nullable=False, server_default="0"),
            sa.Column("payment_terms_days", sa.Integer(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("confirmed_at", sa.DateTime(), nullable=True),
            sa.Column("cancelled_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("created_by", sa.Integer(),
                      sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("updated_by", sa.Integer(),
                      sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        )
        op.create_index("ix_purchase_orders_number", "purchase_orders", ["number"])
        op.create_index("ix_purchase_orders_status", "purchase_orders", ["status"])
        op.create_index("ix_purchase_orders_supplier_id", "purchase_orders", ["supplier_id"])

    if not _has_table("purchase_order_lines"):
        op.create_table(
            "purchase_order_lines",
            sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
            sa.Column("company_id", sa.Integer(),
                      sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
            sa.Column("order_id", sa.Integer(),
                      sa.ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False),
            sa.Column("product_id", sa.Integer(),
                      sa.ForeignKey("products.id", ondelete="SET NULL"), nullable=True),
            sa.Column("description", sa.String(500), nullable=True),
            sa.Column("quantity", sa.Numeric(14, 4), nullable=False, server_default="1"),
            sa.Column("quantity_received", sa.Numeric(14, 4), nullable=False, server_default="0"),
            sa.Column("unit", sa.String(30), nullable=True),
            sa.Column("unit_price", sa.Numeric(14, 4), nullable=False, server_default="0"),
            sa.Column("tax_rate", sa.Numeric(6, 2), nullable=False, server_default="0"),
            sa.Column("discount_percent", sa.Numeric(6, 2), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("created_by", sa.Integer(),
                      sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("updated_by", sa.Integer(),
                      sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        )
        op.create_index("ix_purchase_order_lines_order_id", "purchase_order_lines", ["order_id"])


    # --- 5. Bon de réception ------------------------------------------------
    if not _has_table("purchase_receptions"):
        op.create_table(
            "purchase_receptions",
            sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
            sa.Column("company_id", sa.Integer(),
                      sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
            sa.Column("number", sa.String(30), nullable=False, unique=True),
            sa.Column("order_id", sa.Integer(),
                      sa.ForeignKey("purchase_orders.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("warehouse_id", sa.Integer(),
                      sa.ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
            sa.Column("reception_date", sa.Date(), nullable=False),
            sa.Column("validated_at", sa.DateTime(), nullable=True),
            sa.Column("received_by", sa.Integer(),
                      sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("created_by", sa.Integer(),
                      sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("updated_by", sa.Integer(),
                      sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        )
        op.create_index("ix_purchase_receptions_number", "purchase_receptions", ["number"])
        op.create_index("ix_purchase_receptions_order_id", "purchase_receptions", ["order_id"])

    if not _has_table("purchase_reception_lines"):
        op.create_table(
            "purchase_reception_lines",
            sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
            sa.Column("company_id", sa.Integer(),
                      sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
            sa.Column("reception_id", sa.Integer(),
                      sa.ForeignKey("purchase_receptions.id", ondelete="CASCADE"), nullable=False),
            sa.Column("order_line_id", sa.Integer(),
                      sa.ForeignKey("purchase_order_lines.id", ondelete="SET NULL"), nullable=True),
            sa.Column("product_id", sa.Integer(),
                      sa.ForeignKey("products.id", ondelete="SET NULL"), nullable=True),
            sa.Column("description", sa.String(500), nullable=True),
            sa.Column("quantity", sa.Numeric(14, 4), nullable=False, server_default="1"),
            sa.Column("unit_cost", sa.Numeric(14, 4), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("created_by", sa.Integer(),
                      sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("updated_by", sa.Integer(),
                      sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        )
        op.create_index("ix_purchase_reception_lines_reception_id",
                        "purchase_reception_lines", ["reception_id"])


    # --- 6. Facture fournisseur --------------------------------------------
    if not _has_table("supplier_invoices"):
        op.create_table(
            "supplier_invoices",
            sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
            sa.Column("company_id", sa.Integer(),
                      sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
            sa.Column("reference", sa.String(30), nullable=False, unique=True),
            sa.Column("supplier_invoice_number", sa.String(50), nullable=True),
            sa.Column("supplier_id", sa.Integer(),
                      sa.ForeignKey("partners.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("order_id", sa.Integer(),
                      sa.ForeignKey("purchase_orders.id", ondelete="SET NULL"), nullable=True),
            sa.Column("reception_id", sa.Integer(),
                      sa.ForeignKey("purchase_receptions.id", ondelete="SET NULL"), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
            sa.Column("invoice_date", sa.Date(), nullable=False),
            sa.Column("due_date", sa.Date(), nullable=True),
            sa.Column("currency_code", sa.String(3), nullable=False, server_default="XOF"),
            sa.Column("amount_untaxed", sa.Numeric(14, 4), nullable=False, server_default="0"),
            sa.Column("tax_amount", sa.Numeric(14, 4), nullable=False, server_default="0"),
            sa.Column("amount_total", sa.Numeric(14, 4), nullable=False, server_default="0"),
            sa.Column("paid_amount", sa.Numeric(14, 4), nullable=False, server_default="0"),
            sa.Column("matching_status", sa.String(20), nullable=True),
            sa.Column("matching_details", sa.JSON(), nullable=True),
            sa.Column("posted_at", sa.DateTime(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("created_by", sa.Integer(),
                      sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("updated_by", sa.Integer(),
                      sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        )
        op.create_index("ix_supplier_invoices_reference", "supplier_invoices", ["reference"])
        op.create_index("ix_supplier_invoices_status", "supplier_invoices", ["status"])
        op.create_index("ix_supplier_invoices_supplier_id", "supplier_invoices", ["supplier_id"])
        op.create_index("ix_supplier_invoices_order_id", "supplier_invoices", ["order_id"])

    if not _has_table("supplier_invoice_lines"):
        op.create_table(
            "supplier_invoice_lines",
            sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
            sa.Column("company_id", sa.Integer(),
                      sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
            sa.Column("invoice_id", sa.Integer(),
                      sa.ForeignKey("supplier_invoices.id", ondelete="CASCADE"), nullable=False),
            sa.Column("order_line_id", sa.Integer(),
                      sa.ForeignKey("purchase_order_lines.id", ondelete="SET NULL"), nullable=True),
            sa.Column("product_id", sa.Integer(),
                      sa.ForeignKey("products.id", ondelete="SET NULL"), nullable=True),
            sa.Column("description", sa.String(500), nullable=True),
            sa.Column("quantity", sa.Numeric(14, 4), nullable=False, server_default="1"),
            sa.Column("unit_price", sa.Numeric(14, 4), nullable=False, server_default="0"),
            sa.Column("tax_rate", sa.Numeric(6, 2), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("created_by", sa.Integer(),
                      sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("updated_by", sa.Integer(),
                      sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        )
        op.create_index("ix_supplier_invoice_lines_invoice_id",
                        "supplier_invoice_lines", ["invoice_id"])


def downgrade() -> None:
    for table in (
        "supplier_invoice_lines", "supplier_invoices",
        "purchase_reception_lines", "purchase_receptions",
        "purchase_order_lines", "purchase_orders",
        "purchase_request_lines", "purchase_requests",
        "partner_categories",
    ):
        if _has_table(table):
            op.drop_table(table)

    with op.batch_alter_table("partners") as batch_op:
        if "delivery_days" in _columns("partners"):
            batch_op.drop_column("delivery_days")
        if "rating" in _columns("partners"):
            batch_op.drop_column("rating")


