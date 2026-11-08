/**
 * Onglet Paramètres → Documents.
 *
 * - Conditions Générales de Vente (page finale des documents) — PDF ou texte ;
 * - Filigrane des documents (image superposée en transparence, opacité
 *   réglable, pages A4 uniquement).
 *
 * La **nomenclature des références** a été déplacée vers l'onglet
 * « Séquences » (matricules employés, pièces et documents).
 */
"use client";

import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api/client";
import { withLoader } from "@/lib/loader";

export function DocumentsTab() {
  return (
    <div className="space-y-6">
      <WatermarkCard />
      <CgvCard />
    </div>
  );
}

/** Filigrane des documents (image superposée en transparence, opacité réglable — pages A4, jamais le ticket POS). */
function WatermarkCard() {
  const fileRef = useRef<HTMLInputElement>(null);
  const [info, setInfo] = useState<{
    exists: boolean;
    size?: number;
    preview?: string;
    opacity?: number;
    saturation?: number;
  } | null>(null);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const [opacity, setOpacity] = useState(10);
  const [saturation, setSaturation] = useState(100);
  // Enregistrement explicite : les curseurs ne modifient que l'état local, la
  // persistance est déclenchée par le bouton « Enregistrer ».
  const [dirty, setDirty] = useState(false);
  const [savingSettings, setSavingSettings] = useState(false);
  const [settingsSaved, setSettingsSaved] = useState(false);

  const refresh = () => {
    apiClient
      .get("/core/settings/watermark")
      .then((res) => {
        setInfo(res.data);
        if (typeof res.data?.opacity === "number") setOpacity(res.data.opacity);
        if (typeof res.data?.saturation === "number")
          setSaturation(res.data.saturation);
        setDirty(false);
      })
      .catch(() => {
        setInfo({ exists: false, opacity: 10, saturation: 100 });
        setDirty(false);
      });
  };

  const onOpacityChange = (v: number) => {
    setOpacity(v);
    setSettingsSaved(false);
    setDirty(true);
  };

  const onSaturationChange = (v: number) => {
    setSaturation(v);
    setSettingsSaved(false);
    setDirty(true);
  };

  /** Persiste l'opacité et la saturation du filigrane (bouton « Enregistrer »). */
  const saveWatermarkSettings = async () => {
    setSavingSettings(true);
    setMsg("");
    try {
      await apiClient.put("/core/settings/watermark/opacity", { value: opacity });
      await apiClient.put("/core/settings/watermark/saturation", {
        value: saturation,
      });
      setDirty(false);
      setSettingsSaved(true);
      window.setTimeout(() => setSettingsSaved(false), 3000);
    } catch {
      setMsg("Échec de l'enregistrement des réglages du filigrane.");
    } finally {
      setSavingSettings(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const upload = async (f: File) => {
    setBusy(true);
    setMsg("");
    try {
      const form = new FormData();
      form.append("file", f);
      const res = await apiClient.post("/core/settings/watermark", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setMsg(`Filigrane chargé ✓ (${((res.data.size ?? 0) / 1024).toFixed(0)} Ko) — il couvrira le tableau des produits à l'export du PDF.`);
      refresh();
    } catch {
      setMsg("Échec du chargement (PNG ou JPEG, max 2 Mo).");
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    setBusy(true);
    try {
      await apiClient.delete("/core/settings/watermark");
      setMsg("Filigrane supprimé.");
      refresh();
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card className="p-6">
      <h2 className="mb-1 text-lg font-semibold">Filigrane des documents</h2>
      <p className="mb-4 text-sm text-muted">
        Image <strong>superposée en transparence</strong> sur toutes les pages A4
        des documents PDF (PNG ou JPEG — max 2 Mo), hors page CGV annexée et hors
        ticket POS. Réglez son opacité ci-dessous.
      </p>
      <div className="mb-4 flex items-start gap-4">
        {info?.exists && info.preview ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={info.preview}
            alt="Aperçu du filigrane"
            className="h-24 w-24 rounded-md border border-line bg-subtle object-contain p-1"
          />
        ) : (
          <div className="flex h-24 w-24 items-center justify-center rounded-md border border-dashed border-line text-xs text-faint">
            Aucun filigrane
          </div>
        )}
        <div>
          <input
            ref={fileRef}
            type="file"
            accept="image/png,image/jpeg,.png,.jpg,.jpeg"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) void upload(f);
              e.target.value = "";
            }}
          />
          <div className="flex flex-wrap items-center gap-2">
            <Button size="sm" disabled={busy} onClick={() => fileRef.current?.click()}>
              {busy ? "Traitement…" : info?.exists ? "Remplacer l'image" : "Charger une image"}
            </Button>
            {info?.exists && (
              <Button
                size="sm"
                variant="outline"
                className="text-red-600"
                disabled={busy}
                onClick={() => void remove()}
              >
                Supprimer
              </Button>
            )}
          </div>
          {info?.exists && info.size ? (
            <p className="mt-2 text-xs text-muted">{(info.size / 1024).toFixed(0)} Ko</p>
          ) : null}
          {msg && <p className="mt-2 text-xs text-muted">{msg}</p>}
        </div>
      </div>

      <div className="mt-4 border-t border-line pt-4">
        <div className="mb-1 flex items-center justify-between">
          <label htmlFor="wm-opacity" className="text-sm font-medium text-muted">
            Opacité du filigrane
          </label>
          <span className="text-sm font-semibold text-ink">{opacity} %</span>
        </div>
        <input
          id="wm-opacity"
          type="range"
          min={1}
          max={100}
          step={1}
          value={opacity}
          onChange={(e) => onOpacityChange(Number(e.target.value))}
          className="w-full max-w-md cursor-pointer accent-blue-600"
        />
        <p className="mt-1 text-xs text-muted">
          Valeur basse = filigrane très discret (recommandé : 5–15 %), valeur
          haute = plus visible mais gêne la lecture.
        </p>
      </div>

      <div className="mt-4 border-t border-line pt-4">
        <div className="mb-1 flex items-center justify-between">
          <label htmlFor="wm-saturation" className="text-sm font-medium text-muted">
            Saturation du filigrane
          </label>
          <span className="text-sm font-semibold text-ink">{saturation} %</span>
        </div>
        <input
          id="wm-saturation"
          type="range"
          min={0}
          max={100}
          step={1}
          value={saturation}
          onChange={(e) => onSaturationChange(Number(e.target.value))}
          className="w-full max-w-md cursor-pointer accent-purple-600"
        />
        <p className="mt-1 text-xs text-muted">
          100 % = couleur pleine, 0 % = niveaux de gris (N&B).
        </p>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-line pt-4">
        <Button
          onClick={() => void saveWatermarkSettings()}
          disabled={savingSettings || !dirty}
        >
          {savingSettings ? "Enregistrement…" : "Enregistrer"}
        </Button>
        {settingsSaved && (
          <span className="text-sm font-medium text-green-600">
            Réglages enregistrés ✓
          </span>
        )}
        {dirty && !savingSettings && (
          <span className="text-xs text-muted">
            Modifications non enregistrées
          </span>
        )}
      </div>
    </Card>
  );
}

/** Conditions Générales de Vente (CGV) : PDF chargé ou texte de repli. */
function CgvCard() {
  const queryClient = useQueryClient();
  const [cgv, setCgv] = useState("");
  const [cgvSaved, setCgvSaved] = useState(false);
  const [pdfInfo, setPdfInfo] = useState<{ exists: boolean; size?: number } | null>(
    null,
  );
  const [pdfMsg, setPdfMsg] = useState<string | null>(null);
  const [pdfBusy, setPdfBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let mounted = true;
    apiClient
      .get("/core/settings/cgv_content")
      .then((res) => {
        if (mounted) setCgv(String(res.data?.value ?? ""));
      })
      .catch(() => {
        if (mounted) setCgv("");
      });
    apiClient
      .get("/core/settings/cgv-pdf")
      .then((res) => {
        if (mounted) setPdfInfo(res.data);
      })
      .catch(() => {
        if (mounted) setPdfInfo({ exists: false });
      });
    return () => {
      mounted = false;
    };
  }, [queryClient]);

  const saveCgv = async () => {
    setCgvSaved(false);
    await apiClient.post("/core/settings/", {
      key: "cgv_content",
      value: cgv,
      is_public: true,
    });
    setCgvSaved(true);
    setTimeout(() => setCgvSaved(false), 3000);
  };

  const uploadPdf = async (file: File) => {
    setPdfBusy(true);
    setPdfMsg(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      await apiClient.post("/core/settings/cgv-pdf", fd);
      const res = await apiClient.get("/core/settings/cgv-pdf");
      setPdfInfo(res.data);
      setPdfMsg("PDF de CGV chargé ✓ — joint en dernière page des devis et factures.");
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setPdfMsg(typeof detail === "string" ? detail : "Erreur lors du chargement du PDF.");
    } finally {
      setPdfBusy(false);
    }
  };

  const deletePdf = async () => {
    setPdfBusy(true);
    setPdfMsg(null);
    try {
      await apiClient.delete("/core/settings/cgv-pdf");
      setPdfInfo({ exists: false });
      setPdfMsg("PDF supprimé — le texte CGV ci-dessous est utilisé.");
    } catch {
      setPdfMsg("Erreur lors de la suppression du PDF.");
    } finally {
      setPdfBusy(false);
    }
  };

  const downloadPdf = () => {
    void withLoader(
      apiClient
        .get("/core/settings/cgv-pdf/download", { responseType: "blob" })
        .then((res) => {
          const url = URL.createObjectURL(res.data);
          window.open(url, "_blank", "noopener");
          setTimeout(() => URL.revokeObjectURL(url), 60_000);
        }),
      "Téléchargement du PDF…",
    );
  };

  return (
    <Card className="p-6">
      <h2 className="mb-1 text-lg font-semibold">
        Conditions Générales de Vente (CGV)
      </h2>
      <p className="mb-4 text-sm text-muted">
        Deux options : un <strong>PDF chargé</strong> (recommandé — ajouté en dernière page
        des devis et factures) ou le <strong>texte</strong> ci-dessous (repli).
      </p>

      {/* PDF de CGV */}
      <div className="mb-5 rounded-lg border border-line p-4">
        <h3 className="mb-2 text-sm font-semibold text-ink">PDF de CGV</h3>
        {pdfInfo?.exists ? (
          <p className="mb-2 text-sm text-muted">
            <span className="font-medium text-green-700">PDF chargé ✓</span>
            {pdfInfo.size ? ` — ${(pdfInfo.size / 1024).toFixed(0)} Ko` : ""}
          </p>
        ) : (
          <p className="mb-2 text-sm text-muted">Aucun PDF chargé.</p>
        )}
        <div className="flex flex-wrap items-center gap-2">
          <input
            ref={fileRef}
            type="file"
            accept="application/pdf,.pdf"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) void uploadPdf(f);
              e.target.value = "";
            }}
          />
          <Button
            size="sm"
            disabled={pdfBusy}
            onClick={() => fileRef.current?.click()}
          >
            {pdfBusy ? "Traitement…" : pdfInfo?.exists ? "Remplacer le PDF" : "Charger un PDF"}
          </Button>
          {pdfInfo?.exists && (
            <>
              <Button size="sm" variant="outline" onClick={downloadPdf}>
                Télécharger
              </Button>
              <Button
                size="sm"
                variant="outline"
                className="text-red-600"
                disabled={pdfBusy}
                onClick={() => void deletePdf()}
              >
                Supprimer
              </Button>
            </>
          )}
        </div>
        {pdfMsg && <p className="mt-2 text-xs text-muted">{pdfMsg}</p>}
      </div>

      {/* Texte CGV (repli) */}
      <h3 className="mb-2 text-sm font-semibold text-ink">Texte des CGV (repli)</h3>
      <p className="mb-2 text-xs text-muted">
        Utilisé uniquement si aucun PDF n'est chargé. Affiché en dernière page des
        devis et factures.
      </p>
      <textarea
        className="min-h-[140px] w-full rounded-md border border-line p-3 text-sm"
        value={cgv}
        onChange={(e) => setCgv(e.target.value)}
        placeholder="Conditions Générales de Vente…"
      />
      <div className="mt-3 flex items-center gap-3">
        <Button onClick={saveCgv}>
          {cgvSaved ? "CGV enregistrées ✓" : "Enregistrer le texte"}
        </Button>
        {cgvSaved && (
          <span className="text-xs text-green-600">
            Page finale des documents mise à jour.
          </span>
        )}
      </div>
    </Card>
  );
}
