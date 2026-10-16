/**
 * Onglet Paramètres → Documents.
 *
 * - Nomenclature des documents : par type (devis, commandes, factures…),
 *   préfixe, longueur de série, période de réinitialisation, suffixe
 *   (aucun / MMAA / AAAA / personnalisé) et aperçu de la prochaine référence.
 * - Conditions Générales de Vente (page finale des documents).
 * - Filigrane des documents (image superposée en transparence, opacité
 *   réglable, pages A4 uniquement).
 */
"use client";

import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { FileText, Loader2 } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiClient } from "@/lib/api/client";
import { withLoader } from "@/lib/loader";
import {
  DEFAULT_NOMENCLATURE,
  DOC_MODELS,
  useNomenclature,
  useSaveNomenclature,
  previewReference,
  type DocNomenclature,
} from "@/hooks/useNomenclature";

const RESET_OPTIONS: { value: DocNomenclature["reset"]; label: string }[] = [
  { value: "never", label: "Jamais" },
  { value: "month", label: "Mensuel" },
  { value: "quarter", label: "Trimestriel" },
  { value: "semester", label: "Semestriel" },
  { value: "year", label: "Annuel" },
];

const SUFFIX_OPTIONS: { value: DocNomenclature["suffix_type"]; label: string }[] = [
  { value: "none", label: "Aucun" },
  { value: "mmaa", label: "MMAA (ex. 2609)" },
  { value: "aaaa", label: "AAAA (ex. 2026)" },
  { value: "custom", label: "Personnalisé" },
];

export function DocumentsTab() {
  const { data: config, isLoading } = useNomenclature();
  const save = useSaveNomenclature();
  const [draft, setDraft] = useState<Record<string, DocNomenclature>>({});
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (config) setDraft({ ...config });
  }, [config]);

  const update = (model: string, patch: Partial<DocNomenclature>) =>
    setDraft((d) => ({
      ...d,
      [model]: { ...DEFAULT_NOMENCLATURE, ...d[model], ...patch },
    }));

  const handleSave = async () => {
    setSaved(false);
    await save.mutateAsync(draft);
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <div className="space-y-6">
      <Card className="p-6">
        <h2 className="mb-1 flex items-center gap-2 text-lg font-semibold">
          <FileText className="h-5 w-5 text-blue-600" />
          Nomenclature des documents
        </h2>
        <p className="mb-5 text-sm text-gray-500">
          Format : <span className="font-mono">PRÉFIXE-SERIE-SUFFIXE</span> — ex.{" "}
          <span className="font-mono">DEV-000123-2609</span>. La série (XXXXXX) peut être
          réinitialisée périodiquement. S'applique aux prochains documents créés.
        </p>
        {isLoading ? (
          <p className="flex items-center gap-2 text-gray-500">
            <Loader2 className="h-4 w-4 animate-spin" /> Chargement…
          </p>
        ) : (
          <div className="space-y-4">
            {DOC_MODELS.map(({ key, label }) => {
              const cfg = { ...DEFAULT_NOMENCLATURE, ...draft[key] };
              return (
                <div key={key} className="rounded-lg border border-gray-200 p-4">
                  <div className="mb-3 flex items-center justify-between">
                    <h3 className="font-medium text-gray-800">{label}</h3>
                    <span className="rounded-md bg-blue-50 px-3 py-1 font-mono text-sm text-blue-700">
                      {previewReference(cfg)}
                    </span>
                  </div>
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
                    <div>
                      <label className="mb-1 block text-xs font-medium text-gray-500">
                        Préfixe
                      </label>
                      <Input
                        value={cfg.prefix}
                        onChange={(e) =>
                          update(key, { prefix: e.target.value.toUpperCase() })
                        }
                        placeholder="DEV"
                      />
                    </div>
                    <div>
                      <label className="mb-1 block text-xs font-medium text-gray-500">
                        Longueur de la série
                      </label>
                      <Input
                        type="number"
                        min={3}
                        max={8}
                        value={cfg.padding}
                        onChange={(e) =>
                          update(key, { padding: Number(e.target.value) || 6 })
                        }
                      />
                    </div>
                    <div>
                      <label className="mb-1 block text-xs font-medium text-gray-500">
                        Réinitialisation
                      </label>
                      <select
                        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                        value={cfg.reset}
                        onChange={(e) =>
                          update(key, {
                            reset: e.target.value as DocNomenclature["reset"],
                          })
                        }
                      >
                        {RESET_OPTIONS.map((o) => (
                          <option key={o.value} value={o.value}>
                            {o.label}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="mb-1 block text-xs font-medium text-gray-500">
                        Suffixe
                      </label>
                      <select
                        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                        value={cfg.suffix_type}
                        onChange={(e) =>
                          update(key, {
                            suffix_type: e.target.value as DocNomenclature["suffix_type"],
                          })
                        }
                      >
                        {SUFFIX_OPTIONS.map((o) => (
                          <option key={o.value} value={o.value}>
                            {o.label}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                  {cfg.suffix_type === "custom" && (
                    <div className="mt-3 max-w-xs">
                      <label className="mb-1 block text-xs font-medium text-gray-500">
                        Suffixe personnalisé
                      </label>
                      <Input
                        value={cfg.suffix_custom}
                        onChange={(e) => update(key, { suffix_custom: e.target.value })}
                        placeholder="GEA"
                      />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        <div className="mt-5 flex items-center gap-3">
          <Button onClick={handleSave} disabled={save.isPending || isLoading}>
            {save.isPending ? "Enregistrement…" : "Enregistrer la nomenclature"}
          </Button>
          {saved && (
            <span className="text-sm text-green-600">
              Nomenclature enregistrée ✓ — appliquée aux prochains documents.
            </span>
          )}
        </div>
      </Card>
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
  const [opacitySaved, setOpacitySaved] = useState(false);
  const [saturationSaved, setSaturationSaved] = useState(false);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const refresh = () => {
    apiClient
      .get("/core/settings/watermark")
      .then((res) => {
        setInfo(res.data);
        if (typeof res.data?.opacity === "number") setOpacity(res.data.opacity);
        if (typeof res.data?.saturation === "number")
          setSaturation(res.data.saturation);
      })
      .catch(() => setInfo({ exists: false, opacity: 10, saturation: 100 }));
  };

  /** Sauvegarde différée (500 ms) : pas d'appel API à chaque cran du curseur. */
  const saveOpacity = async (v: number) => {
    try {
      await apiClient.put("/core/settings/watermark/opacity", { value: v });
      setOpacitySaved(true);
      window.setTimeout(() => setOpacitySaved(false), 2500);
    } catch {
      setMsg("Échec de l'enregistrement de l'opacité.");
    }
  };

  const saveSaturation = async (v: number) => {
    try {
      await apiClient.put("/core/settings/watermark/saturation", { value: v });
      setSaturationSaved(true);
      window.setTimeout(() => setSaturationSaved(false), 2500);
    } catch {
      setMsg("Échec de l'enregistrement de la saturation.");
    }
  };

  const onOpacityChange = (v: number) => {
    setOpacity(v);
    setOpacitySaved(false);
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => void saveOpacity(v), 500);
  };

  const onSaturationChange = (v: number) => {
    setSaturation(v);
    setSaturationSaved(false);
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => void saveSaturation(v), 500);
  };

  useEffect(() => {
    refresh();
    return () => {
      if (saveTimer.current) clearTimeout(saveTimer.current);
    };
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
      <p className="mb-4 text-sm text-gray-500">
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
            className="h-24 w-24 rounded-md border border-gray-200 bg-gray-50 object-contain p-1"
          />
        ) : (
          <div className="flex h-24 w-24 items-center justify-center rounded-md border border-dashed border-gray-300 text-xs text-gray-400">
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
            <p className="mt-2 text-xs text-gray-500">{(info.size / 1024).toFixed(0)} Ko</p>
          ) : null}
          {msg && <p className="mt-2 text-xs text-gray-600">{msg}</p>}
        </div>
      </div>

      <div className="mt-4 border-t border-gray-100 pt-4">
        <div className="mb-1 flex items-center justify-between">
          <label htmlFor="wm-opacity" className="text-sm font-medium text-gray-700">
            Opacité du filigrane
          </label>
          <span className="text-sm font-semibold text-gray-900">{opacity} %</span>
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
        <p className="mt-1 text-xs text-gray-500">
          Valeur basse = filigrane très discret (recommandé : 5–15 %), valeur
          haute = plus visible mais gêne la lecture.
          {opacitySaved && (
            <span className="ml-1 font-medium text-green-600">Enregistré ✓</span>
          )}
        </p>
      </div>

      <div className="mt-4 border-t border-gray-100 pt-4">
        <div className="mb-1 flex items-center justify-between">
          <label htmlFor="wm-saturation" className="text-sm font-medium text-gray-700">
            Saturation du filigrane
          </label>
          <span className="text-sm font-semibold text-gray-900">{saturation} %</span>
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
        <p className="mt-1 text-xs text-gray-500">
          100 % = couleur pleine, 0 % = niveaux de gris (N&B).
          {saturationSaved && (
            <span className="ml-1 font-medium text-green-600">Enregistré ✓</span>
          )}
        </p>
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
      <p className="mb-4 text-sm text-gray-500">
        Deux options : un <strong>PDF chargé</strong> (recommandé — ajouté en dernière page
        des devis et factures) ou le <strong>texte</strong> ci-dessous (repli).
      </p>

      {/* PDF de CGV */}
      <div className="mb-5 rounded-lg border border-gray-200 p-4">
        <h3 className="mb-2 text-sm font-semibold text-gray-800">PDF de CGV</h3>
        {pdfInfo?.exists ? (
          <p className="mb-2 text-sm text-gray-600">
            <span className="font-medium text-green-700">PDF chargé ✓</span>
            {pdfInfo.size ? ` — ${(pdfInfo.size / 1024).toFixed(0)} Ko` : ""}
          </p>
        ) : (
          <p className="mb-2 text-sm text-gray-500">Aucun PDF chargé.</p>
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
        {pdfMsg && <p className="mt-2 text-xs text-gray-600">{pdfMsg}</p>}
      </div>

      {/* Texte CGV (repli) */}
      <h3 className="mb-2 text-sm font-semibold text-gray-800">Texte des CGV (repli)</h3>
      <p className="mb-2 text-xs text-gray-500">
        Utilisé uniquement si aucun PDF n'est chargé. Affiché en dernière page des
        devis et factures.
      </p>
      <textarea
        className="min-h-[140px] w-full rounded-md border border-gray-300 p-3 text-sm"
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
