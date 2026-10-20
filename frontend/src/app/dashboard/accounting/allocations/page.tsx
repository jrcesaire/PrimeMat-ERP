/**
 * Page « Lettrage tiers » — rapprochement paiement ↔ facture.
 *
 * Permet de visualiser les factures avec un solde restant à lettrer
 * et de créer des lettrages (allocations) liant un paiement à une facture.
 */
"use client";

import { useState } from "react";
import {
  ArrowRight,
  CheckCircle2,
  Clock,
  CreditCard,
  FileText,
  Loader2,
  Plus,
  Search,
  User,
  Wallet,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiClient } from "@/lib/api/client";
import {
  useAllocationSummary,
  useCreateAllocation,
  useAllocationsForInvoice,
  type InvoiceAllocationSummary,
} from "@/hooks/useAllocations";

interface PaymentLite {
  id: number;
  reference: string;
  amount: number;
  payment_date: string;
  payment_type: string;
  status: string;
}

const EMPTY_SUMMARY: InvoiceAllocationSummary[] = [];

export default function AllocationsPage() {
  const [selectedInvoiceId, setSelectedInvoiceId] = useState<number | null>(
    null
  );
  const [paymentId, setPaymentId] = useState<number | null>(null);
  const [allocatedAmount, setAllocatedAmount] = useState<number | null>(null);
  const [allocationDate, setAllocationDate] = useState<string>(
    new Date().toISOString().split("T")[0]
  );
  const [notes, setNotes] = useState("");

  const summary = useAllocationSummary();
  const data = summary.data ?? EMPTY_SUMMARY;
  const isLoading = summary.isPending;

  const createAllocation = useCreateAllocation();
  const isCreating = createAllocation.isPending;

  // Hooks toujours appelés inconditionnellement (Rules of Hooks) :
  // le hook gère lui-même le cas invoiceId === null via enabled: !!invoiceId.
  const allocationsQuery = useAllocationsForInvoice(selectedInvoiceId);
  const allocations = allocationsQuery.data ?? [];

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedInvoiceId || !paymentId || !allocatedAmount) return;
    try {
      await createAllocation.mutateAsync({
        invoice_id: selectedInvoiceId,
        payment_id: paymentId,
        allocated_amount: allocatedAmount,
        allocation_date: allocationDate,
        notes: notes || undefined,
      });
      setPaymentId(null);
      setAllocatedAmount(null);
      setNotes("");
    } catch {
      // L'erreur est déjà affichée par react-query / API
    }
  };

  const formatAmount = (v: number) => v.toLocaleString("fr-FR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* En-tête */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Lettrage tiers — Factures ↔ Paiements
          </h1>
          <p className="text-gray-600">
            Rapprochez les paiements encaissés/émis avec les factures
            correspondantes pour solder les comptes tiers (411 / 401).
          </p>
        </div>
        <Button
          className="bg-[#0a2a6b] text-white hover:bg-[#0d3a8f]"
          onClick={() => setSelectedInvoiceId(null)}
        >
          <FileText className="mr-2 h-4 w-4" /> Toutes les factures
        </Button>
      </div>

      <hr className="border-gray-200" />

      {/* Section 1 : Factures avec solde restant */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CreditCard className="h-4 w-4" />
            Factures en attente de lettrage
          </CardTitle>
          <CardDescription>
            Solde restant = montant total − montants déjà lettrés
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Référence</TableHead>
                  <TableHead>Partenaire</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead className="text-right">Montant total</TableHead>
                  <TableHead className="text-right">Déjà lettré</TableHead>
                  <TableHead className="text-right">Solde restant</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.map((inv) => (
                  <TableRow
                    key={inv.invoice_id}
                    className="cursor-pointer hover:bg-gray-50"
                    onClick={() =>
                      setSelectedInvoiceId(
                        selectedInvoiceId === inv.invoice_id ? null : inv.invoice_id
                      )
                    }
                  >
                    <TableCell className="font-medium">{inv.invoice_reference}</TableCell>
                    <TableCell className="text-sm text-gray-600">—</TableCell>
                    <TableCell className="text-sm text-gray-600">—</TableCell>
                    <TableCell className="text-right text-sm font-medium">
                      {formatAmount(inv.amount_total)}
                    </TableCell>
                    <TableCell className="text-right text-sm">
                      {formatAmount(inv.allocated_amount)}
                    </TableCell>
                    <TableCell
                      className={`text-right text-sm font-medium ${
                        inv.remaining_amount > 0
                          ? "text-amber-700"
                          : "text-green-700"
                      }`}
                    >
                      {formatAmount(inv.remaining_amount)}
                    </TableCell>
                    <TableCell>
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={inv.remaining_amount <= 0}
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedInvoiceId(inv.invoice_id);
                        }}
                      >
                        {inv.remaining_amount <= 0 ? "Soldé" : "Lettre"}
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
                {data.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-gray-500">
                      Aucune facture avec solde restant à lettrer.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Section 2 : Formulaire de lettrage (si une facture est sélectionnée) */}
      {selectedInvoiceId && (
        <Card className="border-blue-200">
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <CardTitle className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-blue-600" />
              Créer un lettrage
            </CardTitle>
            <CardDescription className="text-sm text-gray-600">
              Facture sélectionnée : #{selectedInvoiceId}
            </CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="space-y-2">
              <Label>ID du paiement</Label>
              <Input
                type="number"
                value={paymentId ?? ""}
                onChange={(e) =>
                  setPaymentId(e.target.value ? Number(e.target.value) : null)
                }
                placeholder="Ex: 42"
              />
            </div>
            <div className="space-y-2">
              <Label>Montant à allouer</Label>
              <Input
                type="number"
                step="0.01"
                value={allocatedAmount ?? ""}
                onChange={(e) =>
                  setAllocatedAmount(e.target.value ? Number(e.target.value) : null)
                }
                placeholder="0,00"
              />
            </div>
            <div className="space-y-2 flex items-end">
              <Label>Date</Label>
              <Input
                type="date"
                value={allocationDate}
                onChange={(e) => setAllocationDate(e.target.value)}
              />
            </div>
            <div className="space-y-2 md:col-span-3">
              <Label>Notes (optionnel)</Label>
              <Input
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Référence chèque, numéro de virement…"
              />
            </div>
          </CardContent>
          <CardFooter>
            <Button
              type="submit"
              onClick={handleCreate}
              disabled={isCreating || !selectedInvoiceId || !paymentId || !allocatedAmount}
              className="bg-[#0a2a6b] text-white w-full hover:bg-[#0d3a8f] flex items-center justify-center gap-2"
            >
              {isCreating ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Enregistrement…
                </>
              ) : (
                <>
                  <Plus className="mr-2 h-4 w-4" />
                  Confirmer le lettrage
                </>
              )}
            </Button>
          </CardFooter>
        </Card>
      )}

      {/* Section 3 : Lettrages existants pour la facture sélectionnée */}
      {selectedInvoiceId && allocations.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-4 w-4" />
              Lettrages existants
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Paiement</TableHead>
                    <TableHead className="text-right">Montant alloué</TableHead>
                    <TableHead>Date</TableHead>
                    <TableHead>Notes</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {allocations.map((alloc) => (
                    <TableRow key={alloc.id}>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Wallet className="h-3 w-3 text-gray-400" />
                          <span className="text-sm font-medium">#{alloc.payment_id}</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-right text-sm font-medium">
                        {formatAmount(alloc.allocated_amount)}
                      </TableCell>
                      <TableCell className="text-sm text-gray-600">
                        {alloc.allocation_date}
                      </TableCell>
                      <TableCell className="text-sm text-gray-500">
                        {alloc.notes ?? "—"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
