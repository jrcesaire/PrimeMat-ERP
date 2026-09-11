/**
 * Header du dashboard — affiche le nom de l'utilisateur et un menu.
 */
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useCurrentUser, useLogout } from "@/hooks/useAuth";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { User, LogOut, Settings, Bell, Paintbrush } from "lucide-react";
import { cn } from "@/lib/utils";
import { ThemeSelector } from "@/components/dashboard/ThemeSelector";
import { ThemeToggle } from "@/components/dashboard/ThemeToggle";
import { useCurrentCompany } from "@/hooks/useAuth";

export function Header({ title = "Tableau de bord" }: { title?: string }) {
  const router = useRouter();
  const { data: user } = useCurrentUser();
  const { data: company } = useCurrentCompany();
  const logoutMutation = useLogout();

  const handleLogout = async () => {
    await logoutMutation.mutateAsync();
  };

  return (
    <header className="flex h-16 items-center justify-between border-b border-gray-200 bg-white px-6">
      <div className="flex items-center gap-4">
        <h2 className="text-lg font-semibold">{title}</h2>
        <div className="flex items-center gap-2 text-sm text-gray-600">
          <span>{company?.name ?? "Entreprise"}</span>
          {company?.establishment && (
            <>
              <span>•</span>
              <span className="text-gray-500">{company.establishment}</span>
            </>
          )}
        </div>
      </div>

      <div className="flex items-center gap-4">
        <ThemeToggle />
        <ThemeSelector />
        <Button variant="ghost" size="sm">
          <Bell className="h-4 w-4" />
        </Button>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm" className="flex items-center gap-2">
              <User className="h-4 w-4" />
              <span>{user?.full_name || "Utilisateur"}</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>Mon compte</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => router.push("/dashboard/settings")}>
              <User className="mr-2 h-4 w-4" />
              Profil
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => router.push("/dashboard/settings")}>
              <Settings className="mr-2 h-4 w-4" />
              Paramètres
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={handleLogout}>
              <LogOut className="mr-2 h-4 w-4" />
              Déconnexion
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
