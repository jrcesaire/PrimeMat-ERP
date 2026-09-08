/**
 * Détail d'une dépense — lecture.
 */
"use client";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { Card } from "@/components/ui/card";
import { useExpenses, type Expense } from "@/hooks/useOperations";
import { formatCurrency, formatDate } from "@/lib/utils";

const CATEGORY_LABELS: Record<string, string> = {
  general: "Général",
  transport: "Transport",
  salaires: "Salaires",
  loyer: "Loyer",
  utilities: "Eau / Électricité",
  achats: "Achats",
};

const METHOD_LABELS: Record<string, string> = {
  cash: "Espèces",
  mobile_money: "Mobile Money",
  bank: "Virement",
};

export default function ExpenseDetailPage({ params }: { params: { id: string } }) {
  const id = Number(params.id) || 0;
  const { data: expenses = [], isLoading } = useExpenses();

  const expense: Expense | undefined = expenses.find((e) => e.id === id);
  if (isLoading)
    return <p className="p-6 text-sm text-gray-500">Chargement…</p>;
  if (!expense)
    return (
      <p className="p-6 text-sm text-gray-500">
        Dépense introuvable (ou accès refusé).
      </p>
    );

  return (
    <div className="space-y-6">
      <div>
        <Link href="/dashboard/expenses" className="text-sm text-gray-500 hover:text-primary">
          <ArrowLeft className="mr-1 inline h-4 w-4" /> Retour aux dépenses
        </Link>
        <h1 className="mt-1 text-2xl font-bold text-gray-900">
          {expense.reference} — {expense.label}
        </h1>
        <p className="text-sm text-gray-600">
          {expense.expense_date ? formatDate(expense.expense_date) : "Date inconnue"}
        </p>
      </div>

      <Card className="grid grid-cols-2 gap-4 p-4 sm:grid-cols-4">
        <div>
          <p className="text-xs text-gray-500">Catégorie</p>
          <p className="text-sm font-medium text-gray-900">
            {CATEGORY_LABELS[expense.category] ?? expense.category}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Mode de paiement</p>
          <p className="text-sm font-medium text-gray-900">
            {METHOD_LABELS[expense.payment_method] ?? expense.payment_method}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Montant</p>
          <p className="text-lg font-bold text-red-600">
            -{formatCurrency(expense.amount)}
          </p>
        </div>
      </Card>

      {expense.notes && (
        <Card className="p-4">
          <p className="text-xs text-gray-500">Notes</p>
          <p className="mt-1 text-sm text-gray-700">{expense.notes}</p>
        </Card>
      )}
    </div>
  );
}