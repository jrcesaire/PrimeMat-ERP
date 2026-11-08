/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  trailingSlash: false,
  productionBrowserSourceMaps: false,
  experimental: {
    webpackBuildWorker: true,
  },
  /**
   * Réglages métier rapatriés dans le module Paramètres : les anciennes routes
   * restent valides pour les signets et les liens partagés.
   *
   * Redirections **temporaires** (307) : le cache des navigateurs ne fige pas la
   * nouvelle destination si la nomenclature évolue encore.
   */
  async redirects() {
    return [
      {
        source: "/dashboard/accounting/setup",
        destination: "/dashboard/settings/comptabilite/assistant",
        permanent: false,
      },
      {
        source: "/dashboard/accounting/settings",
        destination: "/dashboard/settings/comptabilite/parametres",
        permanent: false,
      },
    ];
  },
};

export default nextConfig;
