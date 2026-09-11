/**
 * Page des paramètres système.
 *
 * - Général       : informations de l'application
 * - Modules       : activation / désactivation des modules (superadmin)
 * - Utilisateurs  : création de comptes avec rôles/permissions (RBAC)
 */
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import {
  Building2,
  ImagePlus,
  Power,
  PowerOff,
  Users,
  Boxes,
  Loader2,
  Lock,
  Pencil,
  ShieldCheck,
  Trash2,
  UserRound,
  X,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiClient } from "@/lib/api/client";
import { COMPANY_KEY, useCurrentCompany, useCurrentUser } from "@/hooks/useAuth";
import { useModules, useModuleActions } from "@/hooks/useModules";
import type { Company, ModuleInfo } from "@/lib/types";

interface SystemUser {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  phone?: string | null;
  is_active: boolean;
  is_superuser: boolean;
  company_id: number;
  created_at: string;
}

interface Paginated<T> {
  items: T[];
  total: number;
}

interface CompanyLite {
  id: number;
  name: string;
  code: string;
}

interface RoleLite {
  id: number;
  name: string;
  code: string;
  description?: string;
  is_system: boolean;
}

const MODULES_KEY = ["settings", "modules"];
const USERS_KEY = ["settings", "users"];
const ROLES_KEY = ["settings", "roles"];
const COMPANIES_KEY = ["settings", "companies"];

function moduleName(name: string): string {
  return name.charAt(0).toUpperCase() + name.slice(1);
}

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState("general");
  const { data: currentUser } = useCurrentUser();

  const canManageModules = currentUser?.is_superuser ?? false;
  const permissions = currentUser?.permissions ?? [];
  const canManageUsers =
    currentUser?.is_superuser === true ||
    permissions.includes("user:view") ||
    permissions.includes("user:create");
  const canEditUsers =
    currentUser?.is_superuser === true || permissions.includes("user:edit");
  const canDeleteUsers =
    currentUser?.is_superuser === true || permissions.includes("user:delete");

  const { data: appInfo } = useQuery({
    queryKey: ["core", "system", "info"],
    queryFn: async () => {
      const res = await apiClient.get("/core/system/info");
      return res.data as { name: string; version: string; environment: string; debug: boolean };
    },
  });

  // --- Informations de l'entreprise (onglet Général) ---
  const { data: company, isLoading: loadingCompany } = useCurrentCompany();
  const canEditCompany = currentUser?.is_superuser === true;
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [companyForm, setCompanyForm] = useState({
    name: "",
    code: "",
    establishment: "",
    slogan: "",
    phone: "",
    email: "",
    website: "",
    currency_code: "XOF",
    tax_country: "",
    street: "",
    city: "",
    country: "",
    ncc: "",
    rccm: "",
    share_capital: "",
    logo: null as string | null,
  });
  const [companyError, setCompanyError] = useState("");
  // --- SGAV : Conditions Générales de Vente (page finale des devis/factures) ---
  const [cgv, setCgv] = useState("");
  const [cgvSaved, setCgvSaved] = useState(false);

  // Charge la CGV depuis les paramètres
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
    return () => {
      mounted = false;
    };
  }, []);

  const saveCgv = async () => {
    setCgvSaved(false);
    await apiClient.post(
      "/core/settings/",
      { key: "cgv_content", value: cgv, is_public: true },
    );
    setCgvSaved(true);
    setTimeout(() => setCgvSaved(false), 3000);
  };

  // Pré-remplit le formulaire quand l'entreprise est chargée
  useEffect(() => {
    if (!company) return;
    const addr = (company.address ?? {}) as Record<string, string>;
    setCompanyForm({
      name: company.name ?? "",
      code: company.code ?? "",
      establishment: company.establishment ?? "",
      slogan: company.slogan ?? "",
      phone: company.phone ?? "",
      email: company.email ?? "",
      website: company.website ?? "",
      currency_code: company.currency_code || "XOF",
      tax_country: company.tax_country ?? "",
      street: addr.street ?? "",
      city: addr.city ?? "",
      country: addr.country ?? "",
      ncc: company.ncc ?? "",
      rccm: company.rccm ?? "",
      share_capital: company.share_capital ?? "",
      logo: company.logo ?? null,
    });
  }, [company]);

  const handleLogoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      setCompanyError("Le logo doit être une image (PNG, JPG, SVG...).");
      return;
    }
    if (file.size > 300 * 1024) {
      setCompanyError("Le logo ne doit pas dépasser 300 Ko.");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      setCompanyForm((f) => ({ ...f, logo: reader.result as string }));
      setCompanyError("");
    };
    reader.onerror = () => setCompanyError("Impossible de lire le fichier.");
    reader.readAsDataURL(file);
  };

  const updateCompanyMut = useMutation({
    mutationFn: async () => {
      if (!company) throw new Error("Aucune entreprise chargée.");
      if (!companyForm.name.trim()) throw new Error("Le nom de l'entreprise est obligatoire.");
      if (!companyForm.code.trim()) throw new Error("Le code entreprise est obligatoire.");
      const res = await apiClient.put(`/core/companies/${company.id}`, {
        name: companyForm.name.trim(),
        code: companyForm.code.trim(),
        establishment: companyForm.establishment || null,
        slogan: companyForm.slogan || null,
        phone: companyForm.phone || null,
        email: companyForm.email || null,
        website: companyForm.website || null,
        currency_code: companyForm.currency_code,
        tax_country: companyForm.tax_country || null,
        address: {
          ...(company.address ?? {}),
          street: companyForm.street || null,
          city: companyForm.city || null,
          country: companyForm.country || null,
        },
        ncc: companyForm.ncc || null,
        rccm: companyForm.rccm || null,
        share_capital: companyForm.share_capital || null,
        logo: companyForm.logo,
      });
      return res.data as Company;
    },
    onSuccess: () => {
      setCompanyError("");
      // Rafraîchit l'entreprise partout (sidebar, header, formulaire)
      queryClient.invalidateQueries({ queryKey: COMPANY_KEY });
    },
  });

  const handleSaveCompany = async () => {
    try {
      await updateCompanyMut.mutateAsync();
    } catch (err: unknown) {
      setCompanyError(
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
          (err instanceof Error ? err.message : "Erreur lors de l'enregistrement."),
      );
    }
  };

  // Modules (liste + actions)
  const { data: modules = [], isLoading: loadingModules } = useModules();
  const { activate, deactivate } = useModuleActions();

  // Utilisateurs / rôles / entreprises pour la gestion des comptes
  const { data: usersPage, isLoading: loadingUsers } = useQuery({
    queryKey: USERS_KEY,
    queryFn: async (): Promise<Paginated<SystemUser>> => {
      const res = await apiClient.get("/core/users/", { params: { limit: 200 } });
      return res.data;
    },
    enabled: canManageUsers,
  });
  const users = usersPage?.items ?? [];

  const { data: roles = [] } = useQuery({
    queryKey: ROLES_KEY,
    queryFn: async (): Promise<RoleLite[]> => {
      const res = await apiClient.get("/core/roles/");
      return res.data;
    },
    enabled: canManageUsers,
  });

  const { data: companies = [] } = useQuery({
    queryKey: COMPANIES_KEY,
    queryFn: async (): Promise<CompanyLite[]> => {
      const res = await apiClient.get("/core/companies/");
      return res.data;
    },
    enabled: canManageUsers,
  });

  // --- Formulaire de création d'utilisateur ---
  const [form, setForm] = useState({
    email: "",
    first_name: "",
    last_name: "",
    password: "",
    company_id: 0,
    role_ids: [] as number[],
  });
  const [error, setError] = useState("");

  const createUser = useMutation({
    mutationFn: async () => {
      // Un non-superadmin crée toujours dans sa propre entreprise
      const companyId =
        form.company_id || currentUser?.company_id || 0;
      if (companyId === 0) throw new Error("Veuillez sélectionner une entreprise.");
      if (!form.email || !form.first_name || !form.last_name || form.password.length < 8) {
        throw new Error("Renseignez : email, prénom, nom et un mot de passe (min. 8 caractères).");
      }
      const payload = {
        email: form.email,
        first_name: form.first_name,
        last_name: form.last_name,
        password: form.password,
        is_active: true,
        is_verified: true,
        company_id: companyId,
        role_ids: form.role_ids,
      };
      const res = await apiClient.post("/core/users/", payload);
      return res.data;
    },
    onSuccess: () => {
      setError("");
      setForm({ email: "", first_name: "", last_name: "", password: "", company_id: 0, role_ids: [] });
      queryClient.invalidateQueries({ queryKey: USERS_KEY });
    },
  });

  // --- Édition / activation / suppression d'un utilisateur ---
  const [editingUser, setEditingUser] = useState<SystemUser | null>(null);
  const [editForm, setEditForm] = useState({
    email: "",
    first_name: "",
    last_name: "",
    phone: "",
    password: "",
    role_ids: [] as number[],
  });
  const [editError, setEditError] = useState("");

  const apiDetail = (err: unknown): string =>
    (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
    (err instanceof Error ? err.message : "Erreur inattendue.");

  const openEdit = async (u: SystemUser) => {
    setEditError("");
    setEditingUser(u);
    setEditForm({
      email: u.email,
      first_name: u.first_name,
      last_name: u.last_name,
      phone: u.phone ?? "",
      password: "",
      role_ids: [],
    });
    try {
      const res = await apiClient.get(`/core/users/${u.id}/roles`);
      setEditForm((f) => ({
        ...f,
        role_ids: (res.data as RoleLite[]).map((r) => r.id),
      }));
    } catch {
      // Rôles non pré-chargés : l'utilisateur pourra les sélectionner manuellement.
    }
  };

  const updateUser = useMutation({
    mutationFn: async () => {
      if (!editingUser) throw new Error("Aucun utilisateur sélectionné.");
      if (!editForm.email || !editForm.first_name || !editForm.last_name) {
        throw new Error("Renseignez : email, prénom et nom.");
      }
      if (editForm.password && editForm.password.length < 8) {
        throw new Error("Le mot de passe doit contenir au moins 8 caractères.");
      }
      const payload: Record<string, unknown> = {
        email: editForm.email,
        first_name: editForm.first_name,
        last_name: editForm.last_name,
        phone: editForm.phone || null,
        role_ids: editForm.role_ids,
      };
      if (editForm.password) payload.password = editForm.password;
      const res = await apiClient.put(`/core/users/${editingUser.id}`, payload);
      return res.data;
    },
    onSuccess: () => {
      setEditError("");
      setEditingUser(null);
      queryClient.invalidateQueries({ queryKey: USERS_KEY });
    },
  });

  const toggleUserActive = useMutation({
    mutationFn: async (u: SystemUser) => {
      const res = await apiClient.put(`/core/users/${u.id}`, {
        is_active: !u.is_active,
      });
      return res.data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: USERS_KEY }),
  });

  const deleteUser = useMutation({
    mutationFn: async (u: SystemUser) => {
      await apiClient.delete(`/core/users/${u.id}`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: USERS_KEY }),
  });

  const handleToggleActive = async (u: SystemUser) => {
    try {
      await toggleUserActive.mutateAsync(u);
    } catch (err: unknown) {
      alert(apiDetail(err));
    }
  };

  const handleDelete = async (u: SystemUser) => {
    if (
      !window.confirm(
        `Supprimer définitivement le compte de ${u.first_name} ${u.last_name} (${u.email}) ?\nCette action est irréversible.`,
      )
    ) {
      return;
    }
    try {
      await deleteUser.mutateAsync(u);
    } catch (err: unknown) {
      alert(apiDetail(err));
    }
  };

  const toggleModule = async (mod: ModuleInfo) => {
    if (!canManageModules) return;
    try {
      if (mod.status === "active") {
        await deactivate.mutateAsync(mod.name);
      } else {
        await activate.mutateAsync(mod.name);
      }
      queryClient.invalidateQueries({ queryKey: MODULES_KEY });
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      alert(detail || "Erreur lors de la modification du module.");
    }
  };

  const roleChipsForUser = (u: SystemUser) => {
    if (u.is_superuser) {
      return (
        <span className="inline-flex items-center gap-1 text-xs text-indigo-700">
          <ShieldCheck className="h-3 w-3" /> Accès total (admin)
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 text-xs text-gray-500">
        <Lock className="h-3 w-3 text-gray-400" /> Compte standard
      </span>
    );
  };

  const tabBtn = (label: string, value: string, enabled: boolean) => (
    <button
      disabled={!enabled}
      onClick={() => setActiveTab(value)}
      className={`pb-2 px-4 ${
        !enabled
          ? "cursor-not-allowed text-gray-300"
          : activeTab === value
            ? "border-b-2 border-blue-600 text-blue-600"
            : "text-gray-600"
      }`}
    >
      {label}
    </button>
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Paramètres</h1>
        <p className="text-gray-600">Configuration de l'application et de l'entreprise</p>
      </div>

      <div className="flex gap-4 border-b border-gray-200">
        {tabBtn("Général", "general", true)}
        {tabBtn("Modules", "modules", canManageModules)}
        {tabBtn("Utilisateurs", "users", canManageUsers)}
      </div>

      {activeTab === "general" && (
        <div className="space-y-6">
          <Card className="p-6">
            <h2 className="mb-1 flex items-center gap-2 text-lg font-semibold">
              <Building2 className="h-5 w-5 text-blue-600" />
              Informations de l'entreprise
            </h2>
            <p className="mb-4 text-sm text-gray-500">
              Ces informations identifient l'entreprise dans le tableau de bord et sur les
              documents. Le logo s'affiche dans la barre latérale.
            </p>

            {loadingCompany ? (
              <p className="flex items-center gap-2 text-gray-500">
                <Loader2 className="h-4 w-4 animate-spin" /> Chargement...
              </p>
            ) : !company ? (
              <p className="text-gray-500">Aucune entreprise associée à votre compte.</p>
            ) : (
              <div className="space-y-5">
                {/* Logo */}
                <div className="flex items-center gap-4">
                  {companyForm.logo ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={companyForm.logo}
                      alt="Logo de l'entreprise"
                      className="h-20 w-20 rounded-md border border-gray-200 bg-white object-contain p-1"
                    />
                  ) : (
                    <div className="flex h-20 w-20 items-center justify-center rounded-md border-2 border-dashed border-gray-300 text-gray-400">
                      <ImagePlus className="h-6 w-6" />
                    </div>
                  )}
                  {canEditCompany && (
                    <div className="space-y-2">
                      <div className="flex gap-2">
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => fileInputRef.current?.click()}
                        >
                          <ImagePlus className="mr-1 h-4 w-4" />
                          {companyForm.logo ? "Changer le logo" : "Ajouter un logo"}
                        </Button>
                        {companyForm.logo && (
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={() => setCompanyForm((f) => ({ ...f, logo: null }))}
                          >
                            <Trash2 className="mr-1 h-4 w-4" />
                            Retirer
                          </Button>
                        )}
                      </div>
                      <p className="text-xs text-gray-400">PNG, JPG ou SVG — 300 Ko max.</p>
                      <input
                        ref={fileInputRef}
                        type="file"
                        accept="image/*"
                        className="hidden"
                        onChange={handleLogoChange}
                      />
                    </div>
                  )}
                </div>

                {/* Champs */}
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">
                      Nom de l'entreprise *
                    </label>
                    <Input
                      value={companyForm.name}
                      disabled={!canEditCompany}
                      onChange={(e) => setCompanyForm({ ...companyForm, name: e.target.value })}
                      placeholder="Entreprise ABC"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">Code *</label>
                    <Input
                      value={companyForm.code}
                      disabled={!canEditCompany}
                      onChange={(e) => setCompanyForm({ ...companyForm, code: e.target.value })}
                      placeholder="ABC"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">
                      Établissement
                    </label>
                    <Input
                      value={companyForm.establishment}
                      disabled={!canEditCompany}
                      onChange={(e) =>
                        setCompanyForm({ ...companyForm, establishment: e.target.value })
                      }
                      placeholder="Ex : Agence principale"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">Téléphone</label>
                    <Input
                      value={companyForm.phone}
                      disabled={!canEditCompany}
                      onChange={(e) => setCompanyForm({ ...companyForm, phone: e.target.value })}
                      placeholder="+225 07 00 00 00 00"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">Email</label>
                    <Input
                      type="email"
                      value={companyForm.email}
                      disabled={!canEditCompany}
                      onChange={(e) => setCompanyForm({ ...companyForm, email: e.target.value })}
                      placeholder="contact@entreprise.com"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">Site web</label>
                    <Input
                      value={companyForm.website}
                      disabled={!canEditCompany}
                      onChange={(e) => setCompanyForm({ ...companyForm, website: e.target.value })}
                      placeholder="https://..."
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">
                      Devise (code ISO)
                    </label>
                    <Input
                      value={companyForm.currency_code}
                      disabled={!canEditCompany}
                      maxLength={3}
                      onChange={(e) =>
                        setCompanyForm({ ...companyForm, currency_code: e.target.value.toUpperCase() })
                      }
                      placeholder="XOF"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">
                      Adresse — rue / quartier
                    </label>
                    <Input
                      value={companyForm.street}
                      disabled={!canEditCompany}
                      onChange={(e) => setCompanyForm({ ...companyForm, street: e.target.value })}
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">Ville</label>
                    <Input
                      value={companyForm.city}
                      disabled={!canEditCompany}
                      onChange={(e) => setCompanyForm({ ...companyForm, city: e.target.value })}
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">Pays</label>
                    <Input
                      value={companyForm.country}
                      disabled={!canEditCompany}
                      onChange={(e) => setCompanyForm({ ...companyForm, country: e.target.value })}
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">
                      Pays fiscal (code, ex. CI)
                    </label>
                    <Input
                      value={companyForm.tax_country}
                      disabled={!canEditCompany}
                      maxLength={2}
                      onChange={(e) =>
                        setCompanyForm({ ...companyForm, tax_country: e.target.value.toUpperCase() })
                      }
                    />
                  </div>
                  <div className="sm:col-span-2 lg:col-span-3">
                    <label className="mb-1 block text-sm font-medium text-gray-700">
                      Slogan (affiché sur les documents)
                    </label>
                    <Input
                      value={companyForm.slogan}
                      disabled={!canEditCompany}
                      onChange={(e) => setCompanyForm({ ...companyForm, slogan: e.target.value })}
                      placeholder="Ex : Construisez l'esprit tranquille !"
                    />
                  </div>
                </div>

                {/* Informations fiscales & légales */}
                <div>
                  <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
                    Informations fiscales &amp; légales
                  </h3>
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                    <div>
                      <label className="mb-1 block text-sm font-medium text-gray-700">
                        N° Compte Contribuable (NCC)
                      </label>
                      <Input
                        value={companyForm.ncc}
                        disabled={!canEditCompany}
                        onChange={(e) => setCompanyForm({ ...companyForm, ncc: e.target.value })}
                        placeholder="Ex : 2400195 P"
                      />
                    </div>
                    <div>
                      <label className="mb-1 block text-sm font-medium text-gray-700">RCCM</label>
                      <Input
                        value={companyForm.rccm}
                        disabled={!canEditCompany}
                        onChange={(e) => setCompanyForm({ ...companyForm, rccm: e.target.value })}
                        placeholder="Ex : CI-ABJ-2019-B-12345"
                      />
                    </div>
                    <div>
                      <label className="mb-1 block text-sm font-medium text-gray-700">
                        Capital social
                      </label>
                      <Input
                        value={companyForm.share_capital}
                        disabled={!canEditCompany}
                        onChange={(e) =>
                          setCompanyForm({ ...companyForm, share_capital: e.target.value })
                        }
                        placeholder="Ex : 5 000 000 XOF"
                      />
                    </div>
                  </div>
                </div>

                {/* Conditions Générales de Vente — dernière page des devis et factures */}
                <div>
                  <h3 className="mb-3 mt-6 text-sm font-semibold uppercase tracking-wide text-gray-500">
                    Conditions Générales de Vente (CGV)
                  </h3>
                  <p className="mb-2 text-xs text-gray-500">
                    Affichées en dernière page des devis et factures. Chaque ligne
                    correspond à une clause.
                  </p>
                  <textarea
                    value={cgv}
                    onChange={(e) => setCgv(e.target.value)}
                    disabled={!canEditCompany}
                    rows={8}
                    className="w-full rounded-md border border-gray-300 bg-white p-3 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-60"
                    placeholder={"1. Les commandes sont fermes et définitives après confirmation.\n2. Aucune reprise ni échange sur les marchandises découpées sur mesure.\n3. Les matériaux voyagent aux risques et périls du client."}
                  />
                  {canEditCompany && (
                    <div className="mt-2 flex items-center gap-3">
                      <Button
                        onClick={async () => {
                          try {
                            await saveCgv();
                          } catch (err: unknown) {
                            setCompanyError(
                              (err as { response?: { data?: { detail?: string } } })?.response
                                ?.data?.detail ||
                                "Erreur lors de la sauvegarde des CGV.",
                            );
                          }
                        }}
                        variant="outline"
                        size="sm"
                      >
                        {cgvSaved ? "CGV enregistrées ✓" : "Enregistrer les CGV"}
                      </Button>
                      {cgvSaved && <span className="text-xs text-green-600">Page finale des documents mise à jour.</span>}
                    </div>
                  )}
                </div>

                {!canEditCompany && (
                  <p className="flex items-center gap-1 text-xs text-gray-400">
                    <Lock className="h-3 w-3" /> Lecture seule — modification réservée au
                    superadministrateur.
                  </p>
                )}
                {companyError && <p className="text-sm text-red-600">{companyError}</p>}

                {canEditCompany && (
                  <div className="flex justify-end">
                    <Button onClick={handleSaveCompany} disabled={updateCompanyMut.isPending}>
                      {updateCompanyMut.isPending ? (
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      ) : null}
                      Enregistrer
                    </Button>
                  </div>
                )}
              </div>
            )}
          </Card>

          <Card className="p-6">
            <h2 className="mb-4 text-lg font-semibold">Informations de l'application</h2>
            {appInfo ? (
              <div className="space-y-2">
                <div><span className="font-medium">Nom :</span> {appInfo.name}</div>
                <div><span className="font-medium">Version :</span> {appInfo.version}</div>
                <div><span className="font-medium">Environnement :</span> {appInfo.environment}</div>
                <div><span className="font-medium">Debug :</span> {appInfo.debug ? "Activé" : "Désactivé"}</div>
              </div>
            ) : (
              <p className="text-gray-500">Chargement...</p>
            )}
          </Card>
        </div>
      )}

      {activeTab === "modules" && canManageModules && (
        <ModuleManager
          modules={modules}
          loading={loadingModules}
          onToggle={toggleModule}
          actionPending={activate.isPending || deactivate.isPending}
        />
      )}

      {activeTab === "modules" && !canManageModules && (
        <Card className="p-6"><p className="text-gray-500">Accès réservé au superadministrateur.</p></Card>
      )}
{activeTab === "users" && canManageUsers && (
        <div className="space-y-6">
          {/* Création d'un compte */}
          <Card className="p-6">
            <h2 className="mb-1 flex items-center gap-2 text-lg font-semibold">
              <UserRound className="h-5 w-5 text-blue-600" />
              Nouvel utilisateur
            </h2>
            <p className="mb-4 text-sm text-gray-500">
              Crée un compte avec un niveau d'autorisation précis (rôle).
            </p>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Email</label>
                <Input
                  type="email"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  placeholder="prenom.nom@entreprise.com"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Mot de passe (min. 8 car.)</label>
                <Input
                  type="password"
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  placeholder="••••••••"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Prénom</label>
                <Input
                  value={form.first_name}
                  onChange={(e) => setForm({ ...form, first_name: e.target.value })}
                  placeholder="Jean"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Nom</label>
                <Input
                  value={form.last_name}
                  onChange={(e) => setForm({ ...form, last_name: e.target.value })}
                  placeholder="Dupont"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Entreprise</label>
                <select
                  value={form.company_id || ""}
                  onChange={(e) => setForm({ ...form, company_id: Number(e.target.value) })}
                  className="h-10 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm"
                >
                  <option value="">— Sélectionner —</option>
                  {companies.map((c) => (
                    <option key={c.id} value={c.id}>{c.name} ({c.code})</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Niveau d'autorisation (rôles)
                </label>
                <select
                  multiple
                  className="h-28 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm"
                  value={form.role_ids.map(String)}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      role_ids: Array.from(e.target.selectedOptions).map((o) => Number(o.value)),
                    })
                  }
                >
                  {roles.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.name} ({r.code})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

            <div className="mt-4 flex items-center gap-3">
              <Button
                onClick={() => createUser.mutateAsync().catch((e) => setError(e.message))}
                disabled={createUser.isPending}
              >
                {createUser.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                Créer le compte
              </Button>
              {createUser.isSuccess && <span className="text-sm text-green-600">Compte créé avec succès.</span>}
            </div>
          </Card>
{/* Liste des comptes */}
          <Card className="p-6">
            <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold">
              <Users className="h-5 w-5 text-blue-600" />
              Comptes existants
            </h2>
            {loadingUsers ? (
              <p className="flex items-center gap-2 text-gray-500">
                <Loader2 className="h-4 w-4 animate-spin" /> Chargement...
              </p>
            ) : users.length === 0 ? (
              <p className="text-gray-500">Aucun utilisateur.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-200 text-left text-xs uppercase text-gray-500">
                      <th className="px-3 py-2">Nom</th>
                      <th className="px-3 py-2">Email</th>
                      <th className="px-3 py-2">Statut</th>
                      <th className="px-3 py-2">Droits</th>
                      <th className="px-3 py-2 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((u) => (
                      <tr key={u.id} className="border-b border-gray-100">
                        <td className="px-3 py-2 font-medium text-gray-900">
                          {u.first_name} {u.last_name}
                        </td>
                        <td className="px-3 py-2 text-gray-600">{u.email}</td>
                        <td className="px-3 py-2">
                          <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${u.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                            {u.is_active ? "Actif" : "Inactif"}
                          </span>
                        </td>
                        <td className="px-3 py-2">{roleChipsForUser(u)}</td>
                        <td className="px-3 py-2">
                          <div className="flex items-center justify-end gap-1">
                            {canEditUsers && (
                              <button
                                type="button"
                                title={`Modifier ${u.email}`}
                                onClick={() => void openEdit(u)}
                                className="rounded p-1.5 text-gray-500 transition hover:bg-blue-50 hover:text-blue-600"
                              >
                                <Pencil className="h-4 w-4" />
                              </button>
                            )}
                            {canEditUsers && !u.is_superuser && u.id !== currentUser?.id && (
                              <button
                                type="button"
                                title={u.is_active ? `Désactiver ${u.email}` : `Activer ${u.email}`}
                                disabled={toggleUserActive.isPending}
                                onClick={() => void handleToggleActive(u)}
                                className={`rounded p-1.5 transition hover:bg-amber-50 ${
                                  u.is_active
                                    ? "text-gray-500 hover:text-amber-600"
                                    : "text-green-600 hover:bg-green-50"
                                }`}
                              >
                                {u.is_active ? (
                                  <PowerOff className="h-4 w-4" />
                                ) : (
                                  <Power className="h-4 w-4" />
                                )}
                              </button>
                            )}
                            {canDeleteUsers && !u.is_superuser && u.id !== currentUser?.id && (
                              <button
                                type="button"
                                title={`Supprimer ${u.email}`}
                                disabled={deleteUser.isPending}
                                onClick={() => void handleDelete(u)}
                                className="rounded p-1.5 text-gray-500 transition hover:bg-red-50 hover:text-red-600"
                              >
                                <Trash2 className="h-4 w-4" />
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>

          {/* Modale d'édition d'un utilisateur */}
          {editingUser && (
            <div
              className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
              onClick={() => setEditingUser(null)}
            >
              <div
                className="w-full max-w-lg rounded-lg bg-white p-6 shadow-xl"
                onClick={(e) => e.stopPropagation()}
              >
                <div className="mb-4 flex items-center justify-between">
                  <h3 className="flex items-center gap-2 text-lg font-semibold">
                    <Pencil className="h-5 w-5 text-blue-600" />
                    Modifier {editingUser.first_name} {editingUser.last_name}
                  </h3>
                  <button
                    type="button"
                    onClick={() => setEditingUser(null)}
                    className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                  >
                    <X className="h-5 w-5" />
                  </button>
                </div>

                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">Email</label>
                    <Input
                      type="email"
                      value={editForm.email}
                      onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">Téléphone</label>
                    <Input
                      value={editForm.phone}
                      onChange={(e) => setEditForm({ ...editForm, phone: e.target.value })}
                      placeholder="Optionnel"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">Prénom</label>
                    <Input
                      value={editForm.first_name}
                      onChange={(e) => setEditForm({ ...editForm, first_name: e.target.value })}
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">Nom</label>
                    <Input
                      value={editForm.last_name}
                      onChange={(e) => setEditForm({ ...editForm, last_name: e.target.value })}
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">
                      Nouveau mot de passe (optionnel)
                    </label>
                    <Input
                      type="password"
                      value={editForm.password}
                      onChange={(e) => setEditForm({ ...editForm, password: e.target.value })}
                      placeholder="Laisser vide pour conserver"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">
                      Niveau d'autorisation (rôles)
                    </label>
                    <select
                      multiple
                      className="h-28 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm"
                      value={editForm.role_ids.map(String)}
                      onChange={(e) =>
                        setEditForm({
                          ...editForm,
                          role_ids: Array.from(e.target.selectedOptions).map((o) => Number(o.value)),
                        })
                      }
                    >
                      {roles.map((r) => (
                        <option key={r.id} value={r.id}>
                          {r.name} ({r.code})
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {editError && <p className="mt-3 text-sm text-red-600">{editError}</p>}

                <div className="mt-5 flex justify-end gap-3">
                  <Button variant="outline" onClick={() => setEditingUser(null)}>
                    Annuler
                  </Button>
                  <Button
                    onClick={() =>
                      updateUser
                        .mutateAsync()
                        .then(() => queryClient.invalidateQueries({ queryKey: USERS_KEY }))
                        .catch((e) => setEditError(e.message))
                    }
                    disabled={updateUser.isPending}
                  >
                    {updateUser.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                    Enregistrer
                  </Button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
function ModuleManager({
  modules,
  loading,
  onToggle,
  actionPending,
}: {
  modules: ModuleInfo[];
  loading: boolean;
  onToggle: (m: ModuleInfo) => void;
  actionPending: boolean;
}) {
  return (
    <Card className="p-6">
      <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold">
        <Boxes className="h-5 w-5 text-blue-600" />
        Gestion des modules
      </h2>
      <p className="mb-4 text-sm text-gray-500">
        Activez ou désactivez les modules métier. Le module Core est toujours actif.
      </p>

      {loading ? (
        <p className="flex items-center gap-2 text-gray-500">
          <Loader2 className="h-4 w-4 animate-spin" /> Chargement des modules...
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-left text-xs uppercase text-gray-500">
                <th className="px-3 py-2">Module</th>
                <th className="px-3 py-2">Version</th>
                <th className="px-3 py-2">Statut</th>
                <th className="px-3 py-2 text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {modules.map((m) => {
                const isCore = m.name === "core";
                const active = m.status === "active";
                return (
                  <tr key={m.name} className="border-b border-gray-100">
                    <td className="px-3 py-2 font-medium text-gray-900">
                      {moduleName(m.name)}
                      {isCore && (
                        <span className="ml-2 rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-500">Core</span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-gray-500">{m.version}</td>
                    <td className="px-3 py-2">
                      <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${active ? "bg-green-100 text-green-700" : "bg-red-100 text-red-600"}`}>
                        {active ? "Actif" : m.status === "installed" ? "Installé" : "Inactif"}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-right">
                      <Button
                        variant={active ? "outline" : "default"}
                        size="sm"
                        disabled={isCore || actionPending}
                        onClick={() => onToggle(m)}
                      >
                        {active ? (
                          <>
                            <PowerOff className="mr-1 h-4 w-4" /> Désactiver
                          </>
                        ) : (
                          <>
                            <Power className="mr-1 h-4 w-4" /> Activer
                          </>
                        )}
                      </Button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
