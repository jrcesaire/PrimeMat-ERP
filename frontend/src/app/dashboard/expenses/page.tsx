/**
 * Page Dépenses — liste et enregistrement rapide.
 */
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useExpenses, useCreateExpense } from "@/hooks/useOperations";
import { formatCurrency, formatDate } from "@/lib/utils";

export default function ExpensesPage() {
  const router = useRouter();
  const { data: expenses = [], isLoading } = useExpenses();
  const createExpense = useCreateExpense();

  const [label, setLabel] = useState("");
  const [category, setCategory] = useState("general");
  const [amount, setAmount] = useState(0);
  const [method, setMethod] = useState("cash");
  const [error, setError] = useState<string | null>(null);

  const total = expenses.reduce((s, e) => s + (e.amount || 0), 0);

  const handleCreate = async () => {
    setError(null);
    if (!label.trim()) return setError("Libellé requis.");
    if (amount <= 0) return setError("Montant requis.");
    try {
      await createExpense.mutateAsync({
        label: label.trim(),
        category,
        amount,
        payment_method: method,
      });
      setLabel("");
      setAmount(0);
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Erreur lors de l'enregistrement");
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dépenses</h1>
        <p className="text-sm text-gray-600">
          Total enregistré : <strong>{formatCurrency(total)}</strong>
        </p>
      </div>

      {/* Saisie rapide */}
      <Card className="space-y-3 p-4">
        <h2 className="font-semibold text-gray-800">Enregistrer une dépense</h2>
        {error && <div className="rounded-md bg-red-50 p-3 text-sm text-red-600">{error}</div>}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-5">
          <Input
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder="Libellé (ex : Carburant)"
            className="sm:col-span-2"
          />
          <select
            className="rounded-md border border-gray-300 px-3 py-2 text-sm"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            <option value="general">Général</option>
            <option value="transport">Transport</option>
            <option value="salaires">Salaires</option>
            <option value="loyer">Loyer</option>
            <option value="utilities">Eau / Électricité</option>
            <option value="achats">Achats</option>
          </select>
          <select
            className="rounded-md border border-gray-300 px-3 py-2 text-sm"
            value={method}
            onChange={(e) => setMethod(e.target.value)}
          >
            <option value="cash">Espèces</option>
            <option value="mobile_money">Mobile Money</option>
            <option value="bank">Virement</option>
          </select>
          <Input
            type="number"
            min={0}
            value={amount || ""}
            onChange={(e) => setAmount(Number(e.target.value))}
            placeholder="Montant"
          />
        </div>
        <Button onClick={handleCreate} disabled={createExpense.isPending}>
          {createExpense.isPending ? "Enregistrement…" : "Enregistrer la dépense"}
        </Button>
      </Card>

      {/* Liste */}
      <Card className="overflow-hidden p-0">
        {isLoading ? (
          <p className="p-6 text-sm text-gray-500">Chargement…</p>
        ) : expenses.length === 0 ? (
          <p className="p-10 text-center text-sm text-gray-500">Aucune dépense.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-left text-xs uppercase text-gray-500">
                <th className="px-4 py-3">Référence</th>
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3">Libellé</th>
                <th className="px-4 py-3">Catégorie</th>
                <th className="px-4 py-3">Mode</th>
                <th className="px-4 py-3 text-right">Montant</th>
              </tr>
            </thead>
            <tbody>
              {expenses.map((e) => (
                <tr
                  key={e.id}
                  onClick={() => router.push(`/dashboard/expenses/${e.id}`)}
                  className="cursor-pointer border-b border-gray-100 hover:bg-gray-50"
                >
                  <td className="px-4 py-3 font-medium text-gray-900 hover:text-primary hover:underline">{e.reference}</td>
                  <td className="px-4 py-3 text-gray-600">
                    {e.expense_date ? formatDate(e.expense_date) : "—"}
                  </td>
                  <td className="px-4 py-3">{e.label}</td>
                  <td className="px-4 py-3">
                    <span className="inline-flex rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-700">
                      {e.category}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{e.payment_method}</td>
                  <td className="px-4 py-3 text-right font-semibold text-red-600">
                    -{formatCurrency(e.amount)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
