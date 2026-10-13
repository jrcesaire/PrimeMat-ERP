/**
 * Télécharge un document PDF protégé par JWT et l'ouvre dans un nouvel
 * onglet (aperçu + impression navigateur).
 *
 * Un simple lien <a href> échouerait en 401 : il faut passer le token
 * via axios puis diffuser le blob.
 *
 * Le fichier est enregistré sous le nom du rapport
 * (« Devis - DEV-000019.pdf ») puis affiché dans un nouvel onglet : ce nom
 * provient de l'en-tête Content-Disposition construit par le backend
 * (app/core/documents/naming.py) et exposé au JS par `expose_headers` (CORS).
 */
import { apiClient } from "@/lib/api/client";
import { filenameFromDisposition, saveBlob } from "@/lib/api/download";
import { withLoader } from "@/lib/loader";

export function openPdf(path: string, fallbackName = "document.pdf"): Promise<void> {
  return withLoader(openPdfTask(path, fallbackName), "Génération du PDF…");
}

async function openPdfTask(path: string, fallbackName: string): Promise<void> {
  const res = await apiClient.get(path, { responseType: "blob" });
  const filename =
    filenameFromDisposition(res.headers["content-disposition"]) ?? fallbackName;
  const blob: Blob = res.data;

  // Aperçu + impression d'abord : l'activation utilisateur du clic est encore
  // valide pour window.open() (l'onglet la consomme, pas le téléchargement).
  const previewUrl = URL.createObjectURL(blob);
  window.open(previewUrl, "_blank", "noopener");
  // Libère l'URL après un délai suffisant pour l'affichage
  setTimeout(() => URL.revokeObjectURL(previewUrl), 60_000);

  // Enregistrement nommé du même PDF (« Devis - DEV-000019.pdf »)
  saveBlob(blob, filename);
}

export function printQuote(quoteId: number | string): Promise<void> {
  return openPdf(`/sales/quotes/${quoteId}/print`);
}

export function printInvoice(invoiceId: number | string): Promise<void> {
  return openPdf(`/invoicing/invoices/${invoiceId}/print`);
}

export function printDelivery(deliveryId: number | string): Promise<void> {
  return openPdf(`/delivery/notes/${deliveryId}/print`);
}

export function printReceipt(paymentId: number | string): Promise<void> {
  return openPdf(`/payments/payments/${paymentId}/receipt`);
}

export function printPosTicket(orderId: number | string): Promise<void> {
  return printPosHtml(orderId);
}

/**
 * Impression ticket POS sur imprimante thermique 80 mm :
 * récupère le HTML du ticket et l'envoie dans une fenêtre d'impression
 * ( dialogue d'impression système → choisir l'imprimante POS ).
 * Aucun PDF n'est téléchargé pour les tickets.
 *
 * NB : sans `noopener` dans les features de window.open(), sinon la
 * référence renvoyée est null et le document ne peut pas être écrit
 * (popup vide). Fallback : impression via iframe cachée si les pop-ups
 * sont bloquées.
 */
export function printPosHtml(orderId: number | string): Promise<void> {
  return withLoader(printPosHtmlTask(orderId), "Préparation du ticket…");
}

async function printPosHtmlTask(orderId: number | string): Promise<void> {
  const res = await apiClient.get(`/sales/pos/sales/${orderId}/ticket-html`, {
    responseType: "text",
  });
  const html: string = typeof res.data === "string" ? res.data : String(res.data);

  const win = window.open("", "_blank", "width=320,height=600");
  if (!win) {
    printHtmlInIframe(html);
    return;
  }

  win.document.open();
  win.document.write(html);
  win.document.close();
  win.focus();

  // Attend le chargement complet du document avant le dialogue d'impression
  const doPrint = () => {
    try {
      win.focus();
      win.print();
    } catch {
      printHtmlInIframe(html);
    }
    // Ferme la popup automatiquement une fois le dialogue passé
    win.onafterprint = () => win.close();
  };
  if (win.document.readyState === "complete") {
    setTimeout(doPrint, 400);
  } else {
    win.addEventListener("load", () => setTimeout(doPrint, 400), { once: true });
    // Filet de sécurité si l'événement load a déjà été manqué
    setTimeout(() => {
      if (win.document.readyState === "complete") doPrint();
    }, 1500);
  }
}

/** Impression de secours sans popup : iframe caché → dialogue système. */
function printHtmlInIframe(html: string): void {
  const existing = document.getElementById("pos-print-iframe");
  if (existing) existing.remove();
  const iframe = document.createElement("iframe");
  iframe.id = "pos-print-iframe";
  iframe.style.position = "fixed";
  iframe.style.right = "0";
  iframe.style.bottom = "0";
  iframe.style.width = "0";
  iframe.style.height = "0";
  iframe.style.border = "0";
  document.body.appendChild(iframe);
  const doc = iframe.contentWindow?.document;
  if (!doc) throw new Error("Impression impossible dans ce navigateur");
  doc.open();
  doc.write(html);
  doc.close();
  iframe.contentWindow!.focus();
  const print = () => {
    iframe.contentWindow!.print();
    iframe.contentWindow!.addEventListener("afterprint", () => iframe.remove());
    // Nettoyage tardif si afterprint n'est pas déclenché
    setTimeout(() => iframe.remove(), 60_000);
  };
  if (doc.readyState === "complete") {
    setTimeout(print, 300);
  } else {
    iframe.onload = () => setTimeout(print, 300);
  }
}

/**
 * PDF d'une commande :
 * - vente comptoir → ticket de caisse
 * - autre commande → facture (auto-générée côté serveur si absente)
 */
export function printOrder(orderId: number | string): Promise<void> {
  return openPdf(`/sales/orders/${orderId}/print`);
}