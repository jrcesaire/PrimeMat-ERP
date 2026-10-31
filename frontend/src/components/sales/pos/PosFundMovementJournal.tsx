/**
 * Journal des mouvements de fonds manuels en caisse (Point de Vente).
 * Permet d'enregistrer les dépôts et retraits de fonds non liés à une vente,
 * et d'en consulter l'historique pour une session donnée.
 * Conforme au PRD §4.1.2 §5 — Journal des mouvements de fonds manuels.
 */
"use client";

import { useState } from "react";
import { Plus, ArrowLeft, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  usePosFundMovements,
  useCreatePosFundMovement,
} from "@/hooks/usePosSessions";
import {
  PosFundMovement,
  PosFundMovementCreate,
} from "@/lib/types";
import { formatCurrency, formatDate } from "@/lib/utils";

interface Props {
  sessionId: number | null;
  onBack: () => void;
  /**
   * Session clôturée : consultation seule. Les mouvements impactent le solde
   * théorique du rapport de clôture, qui doit rester figé après clôture.
   */
  readOnly?: boolean;
}

function movementTypeBadge(type: string) {
  return type === "deposit" ? (
    <Badge variant="default" className="text-green-600 border-green-100 bg-green-50">
      Dépôt
    </Badge>
  ) : (
    <Badge variant="default" className="text-red-600 border-red-100 bg-red-50">
      Retrait
    </Badge>
  );
}

export function PosFundMovementJournal({ sessionId, onBack, readOnly = false }: Props) {
  const { data: page, isLoading, refetch } = usePosFundMovements(sessionId);
  const createMutation = useCreatePosFundMovement();
  const [openDialog, setOpenDialog] = useState(false);
  const [formData, setFormData] = useState<PosFundMovementCreate>({
    session_id: sessionId ?? 0,
    movement_type: "deposit",
    amount: 0,
    label: "",
    reference: undefined,
    notes: undefined,
  });
  const [saving, setSaving] = useState(false);

  const movements = page?.items ?? [];
  const totalDeposit = movements
    .filter((m) => m.movement_type === "deposit")
    .reduce((sum, m) => sum + m.amount, 0);
  const totalWithdrawal = movements
    .filter((m) => m.movement_type === "withdrawal")
    .reduce((sum, m) => sum + m.amount, 0);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between gap-2">
          <Button variant="outline" size="sm" onClick={onBack}>
            <ArrowLeft className="h-4 w-4" /> Retour
          </Button>
          <h1 className="text-2xl font-bold text-gray-900">Mouvements de fonds</h1>
        </div>
        <p className="p-10 text-center text-sm text-gray-500">Chargement…</p>
      </div>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.label || !formData.label.trim()) return;
    if (!formData.amount || formData.amount <= 0) return;
    setSaving(true);
    try {
      await createMutation.mutateAsync(formData);
      setFormData({
        session_id: sessionId ?? 0,
        movement_type: "deposit",
        amount: 0,
        label: "",
        reference: undefined,
        notes: undefined,
      });
      setOpenDialog(false);
      refetch();
    } finally {
      setSaving(false);
    }
  };
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={onBack}>
            <ArrowLeft className="h-4 w-4" /> Retour
          </Button>
          {/* Bouton simple (et non `DialogTrigger`) : le déclencheur Radix doit
              être enfant de `Dialog`, or la modale est rendue plus bas. */}
          {!readOnly && (
            <Button
              size="sm"
              disabled={!sessionId}
              onClick={() => setOpenDialog(true)}
            >
              <Plus className="h-4 w-4" /> Ajouter un mouvement
            </Button>
          )}
        </div>
        <h1 className="text-2xl font-bold text-gray-900">Mouvements de fonds</h1>
      </div>

      {sessionId === null && (
        <div className="p-4 rounded-lg bg-amber-50 border border-amber-200 text-amber-800 text-sm">
          Sélectionnez une session de caisse pour consulter et ajouter des mouvements de fonds.
        </div>
      )}

      {readOnly && sessionId !== null && (
        <div className="p-4 rounded-lg bg-gray-50 border border-gray-200 text-gray-600 text-sm">
          Session clôturée : le journal reste consultable, mais aucun mouvement ne peut
          plus y être ajouté.
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Récapitulatif</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="space-y-1">
            <div className="text-xs uppercase text-gray-500">Mouvements</div>
            <div className="text-lg font-medium">{movements.length}</div>
          </div>
          <div className="space-y-1">
            <div className="text-xs uppercase text-green-600">Dépôts totaux</div>
            <div className="text-lg font-medium text-green-600">
              {formatCurrency(totalDeposit)}
            </div>
          </div>
          <div className="space-y-1">
            <div className="text-xs uppercase text-red-600">Retraits totaux</div>
            <div className="text-lg font-medium text-red-600">
              {formatCurrency(totalWithdrawal)}
            </div>
          </div>
          <div className="space-y-1">
            <div className="text-xs uppercase text-gray-900">Solde net</div>
            <div className="text-lg font-medium font-bold">
              {formatCurrency(totalDeposit - totalWithdrawal)}
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Historique des mouvements</CardTitle>
        </CardHeader>
        <CardContent>
          {movements.length === 0 ? (
            <p className="p-4 text-center text-sm text-gray-500">
              Aucun mouvement de fonds enregistré pour cette session.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200 text-left text-xs uppercase text-gray-500">
                    <th className="px-4 py-3">Date</th>
                    <th className="px-4 py-3">Type</th>
                    <th className="px-4 py-3">Montant</th>
                    <th className="px-4 py-3">Libellé</th>
                    <th className="px-4 py-3 text-right">Par</th>
                  </tr>
                </thead>
                <tbody>
                  {movements.map((m) => (
                    <tr key={m.id} className="border-b border-gray-100">
                      <td className="px-4 py-3 text-gray-600">
                        {formatDate(m.created_at)}
                      </td>
                      <td className="px-4 py-3">{movementTypeBadge(m.movement_type)}</td>
                      <td className="px-4 py-3 font-medium">
                        {m.movement_type === "deposit" ? "+" : "-"}
                        {formatCurrency(m.amount)}
                      </td>
                      <td className="px-4 py-3 text-gray-800">
                        {m.label}
                        {m.reference && (
                          <span className="ml-1 text-xs text-gray-400">
                            ({m.reference})
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right text-xs text-gray-500">
                        #{m.created_by ?? "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
      <Dialog open={openDialog} onOpenChange={setOpenDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {formData.movement_type === "deposit"
                ? "Dépôt de fonds"
                : "Retrait de fonds"}
            </DialogTitle>
            <DialogDescription>
              Enregistrez un mouvement de caisse non lié à une vente.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label>Type de mouvement</Label>
              <div className="grid grid-cols-2 gap-2">
                <Button
                  variant={formData.movement_type === "deposit" ? "default" : "outline"}
                  size="sm"
                  onClick={() =>
                    setFormData({ ...formData, movement_type: "deposit" })
                  }
                >
                  Dépôt
                </Button>
                <Button
                  variant={formData.movement_type === "withdrawal" ? "default" : "outline"}
                  size="sm"
                  onClick={() =>
                    setFormData({ ...formData, movement_type: "withdrawal" })
                  }
                >
                  Retrait
                </Button>
              </div>
            </div>

            <div className="space-y-2">
              <Label>Montant</Label>
              <Input
                type="number"
                min="0"
                step="0.01"
                value={formData.amount}
                onChange={(e) =>
                  setFormData({ ...formData, amount: parseFloat(e.target.value) || 0 })
                }
                placeholder="0,00"
              />
            </div>

            <div className="space-y-2">
              <Label>Libellé *</Label>
              <Input
                value={formData.label}
                onChange={(e) =>
                  setFormData({ ...formData, label: e.target.value })
                }
                placeholder="Ex: Dépôt de monnaie, Retrait pour change"
              />
            </div>

            <div className="space-y-2">
              <Label>Référence (optionnelle)</Label>
              <Input
                value={formData.reference ?? ""}
                onChange={(e) =>
                  setFormData({ ...formData, reference: e.target.value || undefined })
                }
                placeholder="N° de pièce justificative"
              />
            </div>

            <div className="space-y-2">
              <Label>Notes</Label>
              <Input
                value={formData.notes ?? ""}
                onChange={(e) =>
                  setFormData({ ...formData, notes: e.target.value || undefined })
                }
                placeholder="Observations..."
              />
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOpenDialog(false)}>
                Annuler
              </Button>
              <Button
                type="submit"
                disabled={saving || !formData.label.trim() || !formData.amount}
              >
                {saving ? (
                  <RefreshCw className="h-4 w-4 animate-spin" />
                ) : (
                  "Enregistrer"
                )}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
