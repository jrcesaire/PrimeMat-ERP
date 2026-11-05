/**
 * Écran de gestion des sessions de caisse (Point de Vente).
 * Conforme au PRD "Improvements module PoS" §4.2.2.
 */
"use client";

import { useEffect, useState } from "react";
import { ArrowLeft, Circle, FileText, Lock, Plus, Save, Trash2, Wallet } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { PosCloseReport } from "@/components/sales/pos/PosCloseReport";
import { PosFundMovementJournal } from "@/components/sales/pos/PosFundMovementJournal";
import {
  usePosSessions,
  useOpenPosSession,
  useClosePosSession,
  useUpdatePosSession,
} from "@/hooks/usePosSessions";
import { usePermission } from "@/hooks/useAuth";
import { PosSession, PosSessionCreate, PosSessionClose } from "@/lib/types";
import { formatCurrency } from "@/lib/utils";

const STATUS_CONFIG: Record<
  "open" | "closing" | "closed",
  { label: string; variant: "default" | "secondary" | "destructive" | "outline"; icon: React.ElementType }
> = {
  open: { label: "Ouverte", variant: "default", icon: Circle },
  closing: { label: "Clôture en cours", variant: "outline", icon: Lock },
  closed: { label: "Clôturée", variant: "secondary", icon: Trash2 },
};

function SessionStatusBadge({ status }: { status: string }) {
  const config =
    STATUS_CONFIG[status as keyof typeof STATUS_CONFIG] ?? STATUS_CONFIG.closed;
  const Icon = config.icon;
  return (
    <Badge variant={config.variant} className="flex items-center gap-1.5">
      <Icon className="h-3 w-3" />
      {config.label}
    </Badge>
  );
}

interface Props {
  onBack?: () => void;
}

export function PosSessionsManager({ onBack }: Props) {
  const [openDialog, setOpenDialog] = useState(false);
  const [closeDialog, setCloseDialog] = useState(false);
  const [pendingCloseId, setPendingCloseId] = useState<number | null>(null);
  const [sessionToUpdate, setSessionToUpdate] = useState<PosSession | null>(null);
  const [updateDialog, setUpdateDialog] = useState(false);

  // Ligne de session cliquable : la session sélectionnée ouvre son détail
  // (rapport de clôture / journal des mouvements de fonds).
  const [selectedSession, setSelectedSession] = useState<PosSession | null>(null);
  const [subView, setSubView] = useState<"report" | "movements" | null>(null);

  const { data, refetch } = usePosSessions(0, 50);
  const sessions = data?.items ?? [];
  const activeSession = sessions.find((s) => s.status === "open");

  const openSession = useOpenPosSession();
  const closeSession = useClosePosSession();
  const updateSession = useUpdatePosSession();

  // §7 du PRD : la clôture manuelle anticipée d'une session est réservée
  // aux rôles Administrateur / Manager (permission « pos:close »).
  const can = usePermission();
  const canClose = can("pos:close");

  useEffect(() => {
    if (openSession.isSuccess || closeSession.isSuccess || updateSession.isSuccess) {
      refetch();
    }
  }, [openSession.isSuccess, closeSession.isSuccess, updateSession.isSuccess, refetch]);

  const handleOpen = async (data: PosSessionCreate) => {
    try {
      await openSession.mutateAsync(data);
      setOpenDialog(false);
    } catch { /* handled by mutation */ }
  };

  const handleClose = async (data: PosSessionClose) => {
    if (pendingCloseId === null) return;
    try {
      await closeSession.mutateAsync({ id: pendingCloseId, data });
      setCloseDialog(false);
      setPendingCloseId(null);
    } catch { /* handled by mutation */ }
  };

  const handleUpdateNotes = async (notes: string | null) => {
    if (sessionToUpdate === null) return;
    try {
      await updateSession.mutateAsync({ id: sessionToUpdate.id, data: { notes } });
      setUpdateDialog(false);
      setSessionToUpdate(null);
    } catch { /* handled by mutation */ }
  };

  const formatDate = (iso: string | null) => {
    if (!iso) return "—";
    return new Date(iso).toLocaleString("fr-FR", {
      dateStyle: "short",
      timeStyle: "short",
    });
  };

  // Sous-vue plein écran d'une session sélectionnée. La `key` force le
  // remontage du composant : le formulaire de mouvement repart ainsi de la
  // session courante au lieu de garder l'état de la session précédente.
  if (subView === "report" && selectedSession) {
    return (
      <PosCloseReport
        key={selectedSession.id}
        sessionId={selectedSession.id}
        onBack={() => setSubView(null)}
      />
    );
  }
  if (subView === "movements" && selectedSession) {
    return (
      <PosFundMovementJournal
        key={selectedSession.id}
        sessionId={selectedSession.id}
        onBack={() => setSubView(null)}
        readOnly={selectedSession.status !== "open"}
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        {onBack ? (
          <Button variant="outline" size="sm" onClick={onBack} className="flex items-center gap-2">
            <ArrowLeft className="h-4 w-4" /> Retour à la vente
          </Button>
        ) : null}
        <div>
          <h1 className="text-[28px] font-semibold leading-tight text-ink">Sessions de caisse</h1>
          <p className="text-sm text-muted">
            Gestion des sessions journalières du Point de Vente
          </p>
        </div>
        <Button
          onClick={() => setOpenDialog(true)}
          disabled={activeSession != null}
          className="flex items-center gap-2"
        >
          <Plus className="h-4 w-4" />
          {activeSession != null ? "Session déjà ouverte" : "Ouvrir une session"}
        </Button>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Sessions de caisse</CardTitle>
          <CardDescription>{sessions.length} session(s) trouvée(s)</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-subtle text-left text-xs uppercase tracking-wide text-muted">
                  <th className="px-4 py-3">Référence</th>
                  <th className="px-4 py-3 text-center">Statut</th>
                  <th className="px-4 py-3 text-right">Solde initial</th>
                  <th className="px-4 py-3 text-right">Solde final</th>
                  <th className="px-4 py-3">Ouvert le</th>
                  <th className="px-4 py-3">Fermé le</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {sessions.length === 0 ? (
                  <tr><td colSpan={7} className="px-4 py-8 text-center text-faint">Aucune session de caisse pour le moment.</td></tr>
                ) : (
                  sessions.map((s) => (
                    <tr
                      key={s.id}
                      onClick={() => {
                        setSelectedSession(s);
                        setSubView(null);
                      }}
                      className={`cursor-pointer border-b border-line ${
                        selectedSession?.id === s.id
                          ? "bg-blue-50"
                          : "hover:bg-subtle"
                      }`}
                      title="Cliquer pour voir le détail de la session"
                    >
                      <td className="px-4 py-3 font-medium text-ink">{s.reference}</td>
                      <td className="px-4 py-3 text-center"><SessionStatusBadge status={s.status} /></td>
                      <td className="px-4 py-3 text-right text-ink">{formatCurrency(s.initial_balance)}</td>
                      <td className="px-4 py-3 text-right">{s.closing_balance !== null ? (<span className="font-medium text-ink">{formatCurrency(s.closing_balance)}</span>) : (<span className="text-faint">—</span>)}</td>
                      <td className="px-4 py-3 text-muted">{formatDate(s.opened_at)}</td>
                      <td className="px-4 py-3 text-muted">{formatDate(s.closed_at)}</td>
                      <td className="px-4 py-3 text-right">
                        {s.status === "open" && canClose && (
                          <Button variant="outline" size="sm" onClick={(e) => { e.stopPropagation(); setPendingCloseId(s.id); setCloseDialog(true); }}>Clôturer</Button>
                        )}
                        {s.status === "open" && (
                          <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); setSessionToUpdate(s); setUpdateDialog(true); }} className="ml-2 p-1.5"><Save className="h-3 w-3" /></Button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Détail de la session sélectionnée (ligne cliquable). */}
      {selectedSession && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-3">
            <div>
              <CardTitle>Détail — {selectedSession.reference}</CardTitle>
              <CardDescription>
                Statut :{" "}
                {STATUS_CONFIG[
                  selectedSession.status as keyof typeof STATUS_CONFIG
                ]?.label ?? selectedSession.status}{" "}
                — Solde initial : {formatCurrency(selectedSession.initial_balance)}{" "}
                — Solde final :{" "}
                {selectedSession.closing_balance !== null
                  ? formatCurrency(selectedSession.closing_balance)
                  : "—"}
              </CardDescription>
            </div>
            <SessionStatusBadge status={selectedSession.status} />
          </CardHeader>
          <CardContent className="flex flex-wrap items-center gap-2">
            <Button
              size="sm"
              className="flex items-center gap-2"
              onClick={() => setSubView("report")}
            >
              <FileText className="h-4 w-4" /> Rapport de clôture
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="flex items-center gap-2"
              onClick={() => setSubView("movements")}
            >
              <Wallet className="h-4 w-4" /> Mouvements de fonds
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setSelectedSession(null)}
            >
              Fermer le détail
            </Button>
          </CardContent>
        </Card>
      )}

      {activeSession && (
        <Card className="border-green-100 bg-green-50">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-green-900">Session active : {activeSession.reference}</CardTitle>
              <CardDescription>Solde initial : {formatCurrency(activeSession.initial_balance)} — Ouverte le {formatDate(activeSession.opened_at)}</CardDescription>
            </div>
            <Badge variant="default">En cours</Badge>
          </CardHeader>
        </Card>
      )}
      {/* Modal : Ouvrir une session */}
      <Dialog open={openDialog} onOpenChange={setOpenDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Ouvrir une nouvelle session de caisse</DialogTitle>
            <DialogDescription>
              Le solde initial correspond au fonds de caisse disponible en début de journée.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={(e) => {
            e.preventDefault();
            const formData = new FormData(e.currentTarget);
            handleOpen({
              initial_balance: Number(formData.get("initial_balance") || 0),
              notes: formData.get("notes") as string || null,
            });
          }}>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Solde initial (FCFA)</Label>
                  <Input name="initial_balance" type="number" step="0.01" min="0" defaultValue="0" required />
                </div>
                <div className="space-y-2">
                  <Label>Ouvert par</Label>
                  <Input disabled defaultValue="Utilisateur courant" />
                </div>
              </div>
              <div className="space-y-2">
                <Label>Notes (optionnel)</Label>
                <Input name="notes" placeholder="Ex. : Fonds de caisse du matin" />
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOpenDialog(false)}>Annuler</Button>
              <Button type="submit" disabled={openSession.isPending}>
                {openSession.isPending ? "Ouverture…" : "Ouvrir la session"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Modal : Clôturer une session */}
      <Dialog open={closeDialog} onOpenChange={setCloseDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Clôturer la session de caisse</DialogTitle>
            <DialogDescription>
              Saisissez le solde final constaté en caisse. Le solde sera figé et servira de solde initial pour la prochaine session.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={(e) => {
            e.preventDefault();
            const formData = new FormData(e.currentTarget);
            handleClose({
              closing_balance: Number(formData.get("closing_balance") || 0),
              notes: formData.get("notes") as string || null,
            });
          }}>
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>Solde final (FCFA)</Label>
                <Input name="closing_balance" type="number" step="0.01" min="0" required />
              </div>
              <div className="space-y-2">
                <Label>Notes (optionnel)</Label>
                <Input name="notes" placeholder="Ex. : Écart de caisse constaté" />
              </div>
              {activeSession && (
                <div className="space-y-1 p-3 rounded bg-subtle border border-line">
                  <div className="text-xs text-muted uppercase">Solde initial</div>
                  <div className="text-sm font-medium">{formatCurrency(activeSession.initial_balance)}</div>
                </div>
              )}
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setCloseDialog(false)}>Annuler</Button>
              <Button type="submit" disabled={closeSession.isPending || pendingCloseId === null}>
                {closeSession.isPending ? "Clôture…" : "Clôturer la session"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
      {/* Modal : Modifier les notes d'une session ouverte */}
      <Dialog open={updateDialog} onOpenChange={setUpdateDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Modifier les notes de la session</DialogTitle>
            <DialogDescription>{sessionToUpdate?.reference}</DialogDescription>
          </DialogHeader>
          <form onSubmit={(e) => {
            e.preventDefault();
            const formData = new FormData(e.currentTarget);
            handleUpdateNotes(formData.get("notes") as string || null);
          }}>
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>Notes</Label>
                <Input name="notes" defaultValue={sessionToUpdate?.notes ?? ""} placeholder="Ajouter une note sur cette session…" />
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setUpdateDialog(false)}>Annuler</Button>
              <Button type="submit" disabled={updateSession.isPending}>
                {updateSession.isPending ? "Enregistrement…" : "Enregistrer"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

    </div>
  );
}
