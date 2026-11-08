/**
 * Hub du module Paie — accès aux sous-écrans.
 */
"use client";

import Link from "next/link";
import { Card } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";

const LINKS = [
  {
    href: "/dashboard/payroll/employees",
    title: "Employés & contrats",
    desc: "Registre du personnel, salaires de base et paramètres de paie.",
  },
  {
    href: "/dashboard/payroll/payslips",
    title: "Bulletins de paie",
    desc: "Calculer, valider, imprimer et payer les bulletins.",
  },
  {
    href: "/dashboard/payroll/runs",
    title: "Périodes & lots",
    desc: "Créer une période et générer le lot mensuel de bulletins.",
  },
  {
    href: "/dashboard/payroll/declarations",
    title: "Déclarations CNPS / ITS",
    desc: "Bordereau CNPS et état ITS par période.",
  },
  {
    href: "/dashboard/payroll/settings",
    title: "Paramètres de paie",
    desc: "SMIG, taux CNPS, plafond, RICF et barème ITS.",
  },
];

export default function PayrollHubPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Paie"
        subtitle="Gestion du personnel, des bulletins et des déclarations sociales et fiscales."
      />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {LINKS.map((link) => (
          <Link key={link.href} href={link.href} className="block">
            <Card className="h-full p-5 transition hover:shadow-md">
              <h3 className="text-base font-semibold text-slate-900">
                {link.title}
              </h3>
              <p className="mt-1 text-sm text-slate-500">{link.desc}</p>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
