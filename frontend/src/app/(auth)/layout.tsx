/**
 * Layout de la page de connexion — police Poppins, plein écran
 * (la page gère son propre layout en deux panneaux).
 */
import type { ReactNode } from "react";
import { Poppins } from "next/font/google";

const poppins = Poppins({
  weight: ["300", "400", "500", "600", "700"],
  subsets: ["latin"],
  display: "swap",
});

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className={`${poppins.className} min-h-screen bg-white`}>
      {children}
    </div>
  );
}
