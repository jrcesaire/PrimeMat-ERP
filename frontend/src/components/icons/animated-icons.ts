/**
 * Icônes **animées** du lanceur.
 *
 * Les visuels fournis au format GIF sont convertis en WebP animé par
 * `scripts/build_animated_icons.py` (voir l'en-tête du script pour la recette :
 * cadrage sur le contenu, boucle infinie, image fixe de repli).
 *
 * Le WebP animé est préféré au GIF d'origine : de 5 à 8 fois plus léger à
 * qualité égale, et sans la limitation de palette 256 couleurs du GIF.
 *
 * `staticSrc` sert la première image aux visiteurs ayant activé
 * `prefers-reduced-motion` : une animation qui tourne en boucle sans fin doit
 * pouvoir être figée (RGAA / WCAG 2.2.2).
 */
export const ANIMATED_APP_ICONS: Record<
  string,
  { src: string; staticSrc: string }
> = {
  // Carnet d'adresses — Contacts.
  crm: { src: "/icons/crm.webp", staticSrc: "/icons/crm-static.webp" },
  // Document / facture — Facturation.
  invoicing: {
    src: "/icons/invoicing.webp",
    staticSrc: "/icons/invoicing-static.webp",
  },
  // Terminal d'encaissement — Point de vente.
  pos: { src: "/icons/pos.webp", staticSrc: "/icons/pos-static.webp" },
};
