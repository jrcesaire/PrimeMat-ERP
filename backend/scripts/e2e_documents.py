"""
Test de bout en bout du parcours Devis → Commande → Facture → Encaissement.

Vérifie :
- la mise à jour des CGV (paramètre `cgv_content`),
- la création d'un devis avec lignes + coupes BAC,
- l'aperçu HTML du devis (présence de la page CGV),
- l'impression PDF du devis,
- la confirmation du devis en commande,
- la création d'une facture depuis la commande,
- l'encaissement partiel puis total (statuts de facture),
- le reçu PDF du paiement,
- l'impression PDF de la facture.

Usage (depuis le dossier backend) :
    python scripts/e2e_documents.py [--base http://localhost:8001]
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Console Windows : force l'UTF-8 pour les accents/flèches
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

EMAIL = "admin@abc.com"
PASSWORD = "HRM14kxpovYL_B3t"
COMPANY_CODE = "GEA"

CGV_TEST = (
    "CONDITIONS GENERALES DE VENTE — TEST E2E\n"
    "1. Prix : nets, en francs CFA, hors transport.\n"
    "2. Paiement : 50% à la commande, solde à la livraison.\n"
    "3. Retards : pénalité de 1% par mois de retard.\n"
    "4. Litiges : tribunaux d'Abidjan compétents."
)

_results: list[tuple[str, bool, str]] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    _results.append((label, ok, detail))
    status = "OK  " if ok else "FAIL"
    print(f"[{status}] {label}" + (f" — {detail}" if detail else ""))


def call(method: str, path: str, token: str | None = None,
         payload: dict | None = None, base: str = "") -> tuple[int, bytes]:
    """Appel HTTP simple (stdlib). Retourne (status, body)."""
    url = base + path
    req = urllib.request.Request(url, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    try:
        with urllib.request.urlopen(req, data=data, timeout=60) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def jload(body: bytes) -> dict | list:
    try:
        return json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return {}


# === SUITE DU SCÉNARIO (insérée ci-dessous) ===


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://localhost:8001")
    args = parser.parse_args()
    base = args.base.rstrip("/") + "/api/v1"

    # 1. Login -----------------------------------------------------------------
    code, body = call("POST", "/core/auth/login", payload={
        "email": EMAIL, "password": PASSWORD, "company_code": COMPANY_CODE,
    }, base=base)
    check("Login", code == 200, f"HTTP {code}")
    if code != 200:
        print(body.decode("utf-8", "replace")[:500])
        return 1
    token = jload(body).get("access_token")
    check("Token reçu", bool(token))

    # 2. CGV — mise à jour du paramètre ---------------------------------------
    code, body = call("GET", "/core/settings/cgv_content", token, base=base)
    before = jload(body).get("value")
    code, body = call("PUT", "/core/settings/cgv_content", token, {
        "value": CGV_TEST, "type": "string", "is_public": True,
    }, base=base)
    if code == 404:
        # Le paramètre n'existe pas encore en base → upsert via POST
        code, body = call("POST", "/core/settings", token, {
            "key": "cgv_content", "value": CGV_TEST,
            "type": "string", "is_public": True,
        }, base=base)
    check("Mise à jour CGV", code in (200, 201), f"HTTP {code}")
    code, body = call("GET", "/core/settings/cgv_content", token, base=base)
    check("CGV persistée", jload(body).get("value") == CGV_TEST,
          f"avant={str(before)[:40]!r}")

    # 3. Client -----------------------------------------------------------------
    code, body = call("GET", "/crm/partners", token, base=base)
    partners = jload(body) if code == 200 else []
    if isinstance(partners, list) and partners:
        partner_id = partners[0]["id"]
        partner_name = partners[0].get("name", "?")
    else:
        code, body = call("POST", "/crm/partners", token, {
            "name": "Client Test E2E SARL", "role": "client",
            "entity_type": "company", "phone": "+225 07 00 00 00 00",
        }, base=base)
        created = jload(body)
        check("Création client", code in (200, 201), f"HTTP {code}")
        partner_id, partner_name = created.get("id"), created.get("name", "?")
    check("Client disponible", bool(partner_id), f"id={partner_id} ({partner_name})")

    # === SUITE (devis, facture, encaissements) ===
    return _run_sales_flow(base, token, partner_id)


def _run_sales_flow(base: str, token: str, partner_id: int) -> int:
    """Devis → HTML/PDF → commande → facture → encaissements → PDF."""
    # 4. Devis ------------------------------------------------------------------
    quote_payload = {
        "partner_id": partner_id,
        "currency_code": "XOF",
        "notes": "Test E2E devis → facture",
        "tax_percent": 0,
        "lines": [
            {
                "description": "Ciment CIMAF 42.5 — sac 50 kg",
                "quantity": 100,
                "unit": "sac",
                "unit_price": 5500,
            },
            {
                "description": "Fer à béton HA12 — coupe sur mesure",
                "quantity": 12,
                "unit": "barre",
                "sell_by_length": True,
                "unit_price": 4500,
                "cuts": [
                    {"quantity": 6, "length": 6.0},
                    {"quantity": 6, "length": 4.5},
                ],
            },
        ],
    }
    code, body = call("POST", "/sales/quotes", token, quote_payload, base=base)
    quote = jload(body)
    check("Création devis", code == 201 and bool(quote.get("id")),
          f"HTTP {code} ref={quote.get('reference')} total={quote.get('amount_total')}")
    quote_id = quote.get("id")
    if not quote_id:
        print(body.decode("utf-8", "replace")[:800])
        return 1

    # 5. Aperçu HTML + CGV -------------------------------------------------------
    code, html = call("GET", f"/sales/quotes/{quote_id}/preview-html", token, base=base)
    html_text = html.decode("utf-8", "replace")
    check("Aperçu HTML devis", code == 200, f"HTTP {code}")
    check("Page CGV présente (devis)",
          "cgv-page" in html_text or "model-terms-cgv" in html_text
          or "Conditions Générales de Vente" in html_text)
    check("Contenu CGV affiché (devis)", "TEST E2E" in html_text)
    check("Coupes BAC affichées (devis)", "6 feuilles de 6,00 m" in html_text)

    # 6. PDF devis ---------------------------------------------------------------
    code, pdf = call("GET", f"/sales/quotes/{quote_id}/print", token, base=base)
    check("PDF devis", code == 200 and pdf[:5] == b"%PDF-",
          f"HTTP {code} {len(pdf)} octets")

    # === SUITE (commande, facture, paiements) ===
    return _run_billing_flow(base, token, partner_id, quote_id)


def _run_billing_flow(base: str, token: str, partner_id: int, quote_id: int) -> int:
    """Commande → facture → encaissements → reçus/PDF → vérif contexte CGV."""
    # 7. Confirmation → commande -------------------------------------------------
    code, body = call("POST", f"/sales/quotes/{quote_id}/confirm", token, {}, base=base)
    order = jload(body)
    check("Confirmation devis → commande", code == 200 and bool(order.get("id")),
          f"HTTP {code} ref={order.get('reference')}")
    order_id = order.get("id")
    if not order_id:
        print(body.decode("utf-8", "replace")[:800])
        return 1

    # 8. Facture depuis la commande ----------------------------------------------
    code, body = call("POST", "/invoicing/invoices/from-order", token,
                      {"order_id": order_id, "due_days": 30}, base=base)
    invoice = jload(body)
    check("Création facture depuis commande",
          code == 201 and bool(invoice.get("id")),
          f"HTTP {code} ref={invoice.get('reference')} "
          f"total={invoice.get('amount_total')}")
    invoice_id = invoice.get("id")
    if not invoice_id:
        print(body.decode("utf-8", "replace")[:800])
        return 1
    total = float(invoice.get("amount_total") or 0)

    # 8ter. S-7 : encaissement d'un brouillon refusé (contrôle serveur) ------------
    code, body = call("POST", "/payments/payments", token, {
        "partner_id": partner_id, "invoice_id": invoice_id,
        "method": "cash", "amount": 1000, "direction": "in",
    }, base=base)
    check("S-7 : paiement sur brouillon refusé", code == 400, f"HTTP {code}")

    # 8bis. Confirmation du brouillon (flux Odoo : brouillon → posté) ------------
    # Depuis P0, from-order crée un brouillon par défaut ; le contrôle S-7
    # refuse l'encaissement d'une facture non confirmée.
    code, body = call("POST", f"/invoicing/invoices/{invoice_id}/post", token, {}, base=base)
    check("Confirmation facture (brouillon → posted)", code == 200, f"HTTP {code}")

    # 9. Encaissement partiel → statut PARTIALLY_PAID -----------------------------
    acompte = round(total * 0.4, 2)
    code, body = call("POST", "/payments/payments", token, {
        "partner_id": partner_id, "invoice_id": invoice_id,
        "method": "cash", "amount": acompte, "direction": "in",
        "notes": "Acompte 40%",
    }, base=base)
    payment_1 = jload(body)
    check("Acompte enregistré", code == 201 and bool(payment_1.get("id")),
          f"HTTP {code} ref={payment_1.get('reference')}")

    code, body = call("GET", f"/invoicing/invoices/{invoice_id}", token, base=base)
    inv = jload(body)
    check("Statut facture = partially_paid",
          inv.get("status") == "partially_paid", f"status={inv.get('status')}")
    check("Montant payé à jour", abs(float(inv.get("paid_amount") or 0) - acompte) < 0.01,
          f"paid={inv.get('paid_amount')} due={inv.get('amount_due')}")

    # 10. Solde → statut PAID ------------------------------------------------------
    due = float(inv.get("amount_due") or 0)
    code, body = call("POST", "/payments/payments", token, {
        "partner_id": partner_id, "invoice_id": invoice_id,
        "method": "mobile_money", "amount": due, "direction": "in",
        "notes": "Solde",
    }, base=base)
    payment_2 = jload(body)
    check("Solde encaissé", code == 201 and bool(payment_2.get("id")),
          f"HTTP {code} ref={payment_2.get('reference')}")

    code, body = call("GET", f"/invoicing/invoices/{invoice_id}", token, base=base)
    inv = jload(body)
    check("Statut facture = paid", inv.get("status") == "paid",
          f"status={inv.get('status')}")

    # 11. Reçu PDF du paiement -------------------------------------------------------
    code, pdf = call("GET", f"/payments/payments/{payment_2.get('id')}/receipt", token, base=base)
    check("Reçu PDF paiement", code == 200 and pdf[:5] == b"%PDF-",
          f"HTTP {code} {len(pdf)} octets")

    # 12. PDF facture -----------------------------------------------------------------
    code, pdf = call("GET", f"/invoicing/invoices/{invoice_id}/print", token, base=base)
    check("PDF facture", code == 200 and pdf[:5] == b"%PDF-",
          f"HTTP {code} {len(pdf)} octets")

    # 13. Contexte async : CGV chargée par load_quote / load_invoice ----------------
    try:
        import asyncio

        # Enregistre tous les modèles dans le registre SQLAlchemy
        # (hors process uvicorn, les relations ne se résolvent que si
        # toutes les classes sont importées).
        import app.main  # noqa: F401  (charge tous les modules + modèles)
        import app.core.models  # noqa: F401
        import app.modules.catalogue.models  # noqa: F401  (Product)
        import app.modules.crm.models  # noqa: F401
        import app.modules.invoicing.models  # noqa: F401
        import app.modules.sales.models  # noqa: F401

        from app.core.documents.context import ContextBuilder

        ctx_q = asyncio.run(ContextBuilder().load_quote(quote_id))
        check("Contexte devis contient les CGV", ctx_q.get("cgv") == CGV_TEST,
              f"cgv={str(ctx_q.get('cgv'))[:40]!r}")
        ctx_i = asyncio.run(ContextBuilder().load_invoice(invoice_id))
        check("Contexte facture contient les CGV", ctx_i.get("cgv") == CGV_TEST)
    except Exception as exc:  # noqa: BLE001
        check("Contexte async contient les CGV", False, f"exception: {exc}")

    # 14. Scénario acomptes : devis → commande → acompte 40 % → solde ----------
    try:
        code, body = call("POST", "/sales/quotes", token, {
            "partner_id": partner_id,
            "currency_code": "XOF",
            "notes": "Test E2E acomptes",
            "lines": [
                {
                    "description": "Carreaux 60×60 — palette",
                    "quantity": 50,
                    "unit": "m²",
                    "unit_price": 8000,
                },
            ],
        }, base=base)
        q2 = jload(body)
        check("Devis acompte créé", code == 201 and bool(q2.get("id")),
              f"HTTP {code} ref={q2.get('reference')}")
        code, body = call("POST", f"/sales/quotes/{q2.get('id')}/confirm", token,
                          {}, base=base)
        o2 = jload(body)
        check("Commande acompte confirmée", code == 200 and bool(o2.get("id")),
              f"HTTP {code} ref={o2.get('reference')}")
        o2_id, o2_total = o2.get("id"), float(o2.get("amount_total") or 0)

        # Acompte 40 % — brouillon
        code, body = call("POST", "/invoicing/invoices/from-order", token, {
            "order_id": o2_id, "mode": "down_payment_percent",
            "value": 40, "post": False,
        }, base=base)
        dp = jload(body)
        expected_dp = round(o2_total * 0.4, 2)
        check("Acompte 40 % créé (brouillon)",
              code == 201 and dp.get("status") == "draft"
              and abs(float(dp.get("amount_total") or 0) - expected_dp) < 0.01,
              f"HTTP {code} status={dp.get('status')} "
              f"total={dp.get('amount_total')} attendu={expected_dp}")

        # Sur-facturation refusée (acompte fixe > reste à facturer)
        code, body = call("POST", "/invoicing/invoices/from-order", token, {
            "order_id": o2_id, "mode": "down_payment_fixed",
            "value": o2_total * 2,
        }, base=base)
        check("Sur-facturation refusée (HTTP 400)", code == 400, f"HTTP {code}")

        # Confirmation de la facture brouillon
        code, body = call("POST", f"/invoicing/invoices/{dp.get('id')}/post",
                          token, {}, base=base)
        check("Acompte confirmé (posted)", code == 200
              and jload(body).get("status") == "posted", f"HTTP {code}")

        # Encaissement de l'acompte → facture partiellement payée
        code, body = call("POST", "/payments/payments", token, {
            "partner_id": partner_id, "invoice_id": dp.get("id"),
            "method": "cash", "amount": expected_dp, "direction": "in",
        }, base=base)
        check("Acompte encaissé", code == 201, f"HTTP {code}")

        # Facture de solde (mode full) → 60 % restant
        code, body = call("POST", "/invoicing/invoices/from-order", token, {
            "order_id": o2_id, "mode": "full", "post": True,
        }, base=base)
        solde = jload(body)
        expected_solde = round(o2_total - expected_dp, 2)
        check("Facture de solde créée (total = reste)",
              code == 201 and abs(float(solde.get("amount_total") or 0)
                                  - expected_solde) < 0.01,
              f"HTTP {code} total={solde.get('amount_total')} "
              f"attendu={expected_solde}")

        # Encaissement du solde → paid
        code, body = call("POST", "/payments/payments", token, {
            "partner_id": partner_id, "invoice_id": solde.get("id"),
            "method": "mobile_money", "amount": expected_solde, "direction": "in",
        }, base=base)
        code2, body = call("GET", f"/invoicing/invoices/{solde.get('id')}",
                           token, base=base)
        check("Solde payé (facture paid)", code == 201
              and jload(body).get("status") == "paid", f"HTTP {code}/{code2}")

        # Nouvelle facture refusée : commande entièrement facturée
        code, body = call("POST", "/invoicing/invoices/from-order", token, {
            "order_id": o2_id, "mode": "full",
        }, base=base)
        check("Re-facturation refusée (HTTP 400)", code == 400, f"HTTP {code}")
    except Exception as exc:  # noqa: BLE001
        check("Scénario acomptes", False, f"exception: {exc}")

    # 15. Re-confirmation — round-trips brouillon → confirmé --------------------
    # a) Paiement : remise au brouillon puis re-confirmation --------------------
    p2_id = payment_2.get("id")
    code, body = call("POST", f"/payments/payments/{p2_id}/back-to-draft",
                      token, {}, base=base)
    pay = jload(body)
    check("Paiement remis au brouillon", code == 200
          and pay.get("status") == "draft",
          f"HTTP {code} status={pay.get('status')}")

    code, body = call("GET", f"/invoicing/invoices/{invoice_id}", token, base=base)
    inv = jload(body)
    check("Facture décréditée après révocation du solde",
          abs(float(inv.get("paid_amount") or 0) - acompte) < 0.01
          and inv.get("status") == "partially_paid",
          f"paid={inv.get('paid_amount')} status={inv.get('status')}")

    code, body = call("POST", f"/payments/payments/{p2_id}/confirm", token, {},
                      base=base)
    pay = jload(body)
    check("Paiement re-confirmé (statut paid)",
          code == 200 and pay.get("status") == "paid",
          f"HTTP {code} status={pay.get('status')}")

    code, body = call("GET", f"/invoicing/invoices/{invoice_id}", token, base=base)
    inv = jload(body)
    check("Facture re-créditée après re-confirmation",
          abs(float(inv.get("paid_amount") or 0) - total) < 0.01
          and inv.get("status") == "paid",
          f"paid={inv.get('paid_amount')} status={inv.get('status')}")

    # b) Facture : confirmée → brouillon → re-confirmée (aucun paiement) --------
    try:
        code, body = call("POST", "/sales/quotes", token, {
            "partner_id": partner_id,
            "currency_code": "XOF",
            "notes": "Test E2E re-confirmation facture",
            "tax_percent": 0,
            "lines": [{
                "description": "Sac de ciment — test re-confirmation",
                "quantity": 5, "unit": "sac", "unit_price": 5000,
            }],
        }, base=base)
        q3 = jload(body)
        check("Devis de re-confirmation créé",
              code == 201 and bool(q3.get("id")),
              f"HTTP {code} ref={q3.get('reference')}")
        code, body = call("POST", f"/sales/quotes/{q3.get('id')}/confirm",
                          token, {}, base=base)
        o3 = jload(body)
        check("Commande de re-confirmation créée",
              code == 200 and bool(o3.get("id")), f"HTTP {code}")
        code, body = call("POST", "/invoicing/invoices/from-order", token,
                          {"order_id": o3.get("id"), "post": False}, base=base)
        inv3 = jload(body)
        inv3_id = inv3.get("id")
        check("Facture brouillon créée (re-confirmation)",
              code == 201 and inv3.get("status") == "draft",
              f"HTTP {code} status={inv3.get('status')}")
        code, body = call("POST", f"/invoicing/invoices/{inv3_id}/post",
                          token, {}, base=base)
        check("Facture confirmée (1re passe)",
              code == 200 and jload(body).get("status") == "posted",
              f"HTTP {code}")
        code, body = call("POST",
                          f"/invoicing/invoices/{inv3_id}/reset-to-draft",
                          token, {}, base=base)
        check("Facture remise au brouillon",
              code == 200 and jload(body).get("status") == "draft",
              f"HTTP {code}")
        code, body = call("POST", f"/invoicing/invoices/{inv3_id}/post",
                          token, {}, base=base)
        check("Facture re-confirmée (brouillon → posted)",
              code == 200 and jload(body).get("status") == "posted",
              f"HTTP {code}")
    except Exception as exc:  # noqa: BLE001
        check("Round-trip re-confirmation facture", False, f"exception: {exc}")

    # c) Livraison : BL (pending) → brouillon → re-confirmé (pending) -----------
    try:
        code, body = call("POST", "/delivery/notes/from-order", token,
                          {"order_id": order_id,
                           "notes": "Test E2E re-confirmation BL"},
                          base=base)
        bl = jload(body)
        check("BL créé (statut pending)",
              code == 201 and bl.get("status") == "pending",
              f"HTTP {code} status={bl.get('status')}")
        code, body = call("POST",
                          f"/delivery/notes/{bl.get('id')}/back-to-draft",
                          token, {}, base=base)
        check("BL remis au brouillon",
              code == 200 and jload(body).get("status") == "draft",
              f"HTTP {code} status={jload(body).get('status')}")
        code, body = call("POST", f"/delivery/notes/{bl.get('id')}/status",
                          token, {"status": "pending"}, base=base)
        check("BL re-confirmé (draft → pending)",
              code == 200 and jload(body).get("status") == "pending",
              f"HTTP {code} status={jload(body).get('status')}")
    except Exception as exc:  # noqa: BLE001
        check("Round-trip re-confirmation livraison", False, f"exception: {exc}")

    # Résumé --------------------------------------------------------------------------
    failed = [r for r in _results if not r[1]]
    print("\n===== RÉSUMÉ =====")
    print(f"Total : {len(_results)} | OK : {len(_results) - len(failed)} | "
          f"ÉCHECS : {len(failed)}")
    for label, _ok, detail in failed:
        print(f"  ✗ {label} — {detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

