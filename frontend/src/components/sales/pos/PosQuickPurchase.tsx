/**
 * Achats de quincaillerie depuis le Point de Vente (PRD « Improvements module
 * PoS » §4.2.2.5 et US5).
 *
 * Écran immersif (sidebar + header masqués, bouton « Retour ») ouvert depuis la
 * tuile « Achats » du dashboard PoS. Le caissier y saisit en quelques secondes
 * un achat de fourniture / quincaillerie ; l'achat est enregistré comme
 * **facture fournisseur** dans le module Achats global, puis comptabilisé et
 * réglé sur la caisse — il apparaît donc dans le grand livre de l'entreprise
 * (D 601 + D 4452 / C 401, puis D 401 / C 531).
 */
"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  BookOpen,
  Check,
  ExternalLink,
  PackagePlus,
  Receipt,
  ShoppingBag,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { usePermission } from "@/hooks/useAuth";
import { useCreatePosPurchase, useSuppliers } from "@/hooks/usePurchases";
import { setPosFocus } from "@/lib/pos-focus";
import type { SupplierInvoice } from "@/lib/types";

/** Date du jour au format attendu par les champs `<input type="date">`. */
function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

/** Style des listes déroulantes, aligné sur le composant Input. */
const SELECT_CLASS =
  "flex h-10 w-full rounded-md border border-line bg-surface px-3 py-2 text-sm focus:border-primary focus:ring-1 focus:ring-primary disabled:cursor-not-allowed disabled:opacity-50";

/** Formate un montant dans la devise de la facture. */
function formatAmount(amount: number, currency = "XOF"): string {
  return `${new Intl.NumberFormat("fr-FR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(amount)} ${currency}`;
}

export function PosQuickPurchase() {
  const router = useRouter();
  const can = usePermission();
  const canCreate = can("pos:create");

  const { data: suppliers, isLoading: suppliersLoading } = useSuppliers();
  const createPurchase = useCreatePosPurchase();

  const [supplierId, setSupplierId] = useState<number | "">("");
  const [label, setLabel] = useState("");
  const [amountTotal, setAmountTotal] = useState("");
  const [taxRate, setTaxRate] = useState("0");
  const [purchaseDate, setPurchaseDate] = useState(todayIso());
  const [invoiceNumber, setInvoiceNumber] = useState("");
  const [notes, setNotes] = useState("");
  const [paid, setPaid] = useState(true);
  const [paymentMethod, setPaymentMethod] = useState<
    "cash" | "bank_transfer" | "check" | "mobile_money"
  >("cash");
  const [error, setError] = useState<string | null>(null);
  const [created, setCreated] = useState<SupplierInvoice | null>(null);

  // Mode immersif : sidebar + header masqués tant qu'on reste dans le PoS.
  useEffect(() => {
    setPosFocus(true);
    return () => setPosFocus(false);
  }, []);

  /** Aperçu de la ventilation HT / TVA du montant TTC saisi. */
  const preview = useMemo(() => {
    const total = Number(amountTotal.replace(",", "."));
    const rate = Number(taxRate.replace(",", ".")) || 0;
    if (!Number.isFinite(total) || total <= 0) return null;
    const untaxed = rate ? total / (1 + rate / 100) : total;
    return { untaxed, tax: total - untaxed, total };
  }, [amountTotal, taxRate]);

  const resetForm = () => {
    setSupplierId("");
    setLabel("");
    setAmountTotal("");
    setTaxRate("0");
    setPurchaseDate(todayIso());
    setInvoiceNumber("");
    setNotes("");
    setPaid(true);
    setPaymentMethod("cash");
    setError(null);
  };

  const handleSubmit = async () => {
    setError(null);
    const total = Number(amountTotal.replace(",", "."));
    if (supplierId === "") {
      setError("Sélectionnez le fournisseur de l'achat.");
      return;
    }
    if (!label.trim()) {
      setError("Saisissez le libellé de l'achat (ex. « Vis et pointes »).");
      return;
    }
    if (!Number.isFinite(total) || total <= 0) {
      setError("Le montant TTC doit être supérieur à zéro.");
      return;
    }

    try {
      const invoice = await createPurchase.mutateAsync({
        supplier_id: Number(supplierId),
        label: label.trim(),
        amount_total: total,
        tax_rate: Number(taxRate.replace(",", ".")) || 0,
        purchase_date: purchaseDate || null,
        supplier_invoice_number: invoiceNumber.trim() || null,
        notes: notes.trim() || null,
        paid,
        payment_method: paymentMethod,
      });
      setCreated(invoice);
      resetForm();
    } catch (err) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? null;
      setError(
        detail ?? "L'enregistrement de l'achat a échoué. Veuillez réessayer.",
      );
    }
  };

  const goBack = () => {
    setPosFocus(false);
    router.push("/dashboard/sales/pos");
  };

  return (
    <div className="min-h-screen bg-subtle flex flex-col px-[20px] md:px-[80px] py-6">
      {/* Bandeau : retour vers le menu du PoS */}
      <header className="flex items-center justify-between gap-4">
        <Button
          variant="outline"
          size="sm"
          onClick={goBack}
          title="Revenir au menu du Point de Vente"
        >
          <ArrowLeft className="h-4 w-4" /> Retour
        </Button>
        <div className="flex items-center gap-2 text-muted">
          <ShoppingBag className="h-5 w-5" />
          <div className="text-right leading-tight">
            <div className="text-sm font-semibold text-ink">
              Achats de quincaillerie
            </div>
            <div className="text-xs text-muted">Achat comptoir</div>
          </div>
        </div>
      </header>

      <main className="flex-1 w-full max-w-[760px] mx-auto py-8 space-y-6">
        {!canCreate ? (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <PackagePlus className="h-5 w-5 text-amber-600" /> Accès réservé
              </CardTitle>
              <CardDescription>
                La saisie d&apos;un achat comptoir nécessite la permission
                « pos:create ».
              </CardDescription>
            </CardHeader>
          </Card>
        ) : (
          <>
            {created && (
              <Card className="border-green-300 bg-green-50">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base text-green-800">
                    <Check className="h-5 w-5" /> Achat {created.reference}{" "}
                    enregistré
                  </CardTitle>
                  <CardDescription className="text-green-700">
                    Montant{" "}
                    {formatAmount(created.amount_total, created.currency_code)}
                    {created.status === "paid"
                      ? " — réglé sur la caisse du point de vente."
                      : " — en attente de règlement dans le module Achats."}
                  </CardDescription>
                </CardHeader>
                <CardContent className="flex flex-wrap gap-3">
                  <Link href="/dashboard/purchases/factures">
                    <Button variant="outline" size="sm">
                      <Receipt className="h-4 w-4" /> Factures fournisseur
                      <ExternalLink className="h-3 w-3" />
                    </Button>
                  </Link>
                  <Link href="/dashboard/accounting/ledger">
                    <Button variant="outline" size="sm">
                      <BookOpen className="h-4 w-4" /> Grand livre
                      <ExternalLink className="h-3 w-3" />
                    </Button>
                  </Link>
                </CardContent>
              </Card>
            )}



            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <ShoppingBag className="h-5 w-5" /> Nouvel achat comptoir
                </CardTitle>
                <CardDescription>
                  L&apos;achat est consolidé dans le module Achats global et
                  comptabilisé dans le grand livre de l&apos;entreprise.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-5">
                <div className="grid gap-5 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="pos-purchase-supplier">Fournisseur</Label>
                    <select
                      id="pos-purchase-supplier"
                      className={SELECT_CLASS}
                      value={supplierId}
                      disabled={suppliersLoading}
                      onChange={(e) => {
                        setCreated(null);
                        setSupplierId(
                          e.target.value ? Number(e.target.value) : "",
                        );
                      }}
                    >
                      <option value="">— Sélectionner —</option>
                      {(suppliers ?? []).map((supplier) => (
                        <option key={supplier.id} value={supplier.id}>
                          {supplier.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="pos-purchase-date">
                      Date de l&apos;achat
                    </Label>
                    <Input
                      id="pos-purchase-date"
                      type="date"
                      value={purchaseDate}
                      onChange={(e) => setPurchaseDate(e.target.value)}
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="pos-purchase-label">
                    Libellé de l&apos;achat
                  </Label>
                  <Input
                    id="pos-purchase-label"
                    placeholder="ex. Quincaillerie — vis, pointes, ciment"
                    value={label}
                    onChange={(e) => setLabel(e.target.value)}
                  />
                </div>

                <div className="grid gap-5 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="pos-purchase-amount">Montant TTC</Label>
                    <Input
                      id="pos-purchase-amount"
                      type="number"
                      min="0"
                      step="1"
                      inputMode="decimal"
                      placeholder="0"
                      value={amountTotal}
                      onChange={(e) => setAmountTotal(e.target.value)}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="pos-purchase-tax">Taux de TVA (%)</Label>
                    <Input
                      id="pos-purchase-tax"
                      type="number"
                      min="0"
                      max="100"
                      step="0.5"
                      value={taxRate}
                      onChange={(e) => setTaxRate(e.target.value)}
                    />
                  </div>
                </div>

                {preview && (
                  <p className="rounded-md bg-subtle px-3 py-2 text-xs text-muted">
                    Base HT&nbsp;: {formatAmount(preview.untaxed)} · TVA&nbsp;:{" "}
                    {formatAmount(preview.tax)} · Total&nbsp;:{" "}
                    {formatAmount(preview.total)}
                  </p>
                )}

                <div className="grid gap-5 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="pos-purchase-ref">
                      N° facturette fournisseur
                    </Label>
                    <Input
                      id="pos-purchase-ref"
                      placeholder="facultatif"
                      value={invoiceNumber}
                      onChange={(e) => setInvoiceNumber(e.target.value)}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="pos-purchase-notes">Notes</Label>
                    <Input
                      id="pos-purchase-notes"
                      placeholder="facultatif"
                      value={notes}
                      onChange={(e) => setNotes(e.target.value)}
                    />
                  </div>
                </div>

                <label className="flex items-center gap-2 text-sm text-muted">
                  <input
                    type="checkbox"
                    className="h-4 w-4 rounded border-line"
                    checked={paid}
                    onChange={(e) => setPaid(e.target.checked)}
                  />
                  Réglé immédiatement sur la caisse du point de vente
                </label>

                {paid && (
                  <div className="space-y-2 sm:max-w-[320px]">
                    <Label htmlFor="pos-purchase-method">
                      Mode de règlement
                    </Label>
                    <select
                      id="pos-purchase-method"
                      className={SELECT_CLASS}
                      value={paymentMethod}
                      onChange={(e) =>
                        setPaymentMethod(
                          e.target.value as
                            | "cash"
                            | "bank_transfer"
                            | "check"
                            | "mobile_money",
                        )
                      }
                    >
                      <option value="cash">Espèces (caisse 531)</option>
                      <option value="mobile_money">Mobile money (banque 511)</option>
                      <option value="bank_transfer">Virement (banque 511)</option>
                      <option value="check">Chèque (banque 511)</option>
                    </select>
                  </div>
                )}

                {error && (
                  <p className="text-sm text-red-600" role="alert">
                    {error}
                  </p>
                )}

                <div className="flex items-center gap-3">
                  <Button
                    onClick={handleSubmit}
                    disabled={createPurchase.isPending}
                  >
                    <PackagePlus className="h-4 w-4" />
                    {createPurchase.isPending
                      ? "Enregistrement…"
                      : "Enregistrer l'achat"}
                  </Button>
                  <Button
                    variant="ghost"
                    onClick={resetForm}
                    disabled={createPurchase.isPending}
                  >
                    Réinitialiser
                  </Button>
                </div>
              </CardContent>
            </Card>
          </>
        )}
      </main>
    </div>
  );
}

