/**
 * Télécharge un document PDF protégé par JWT et l'ouvre dans un nouvel
 * onglet (aperçu + impression navigateur).
 *
 * Un simple lien <a href> échouerait en 401 : il faut passer le token
 * via axios puis diffuser le blob.
 */
import { apiClient } from "@/lib/api/client";

export async function openPdf(path: string): Promise<void> {
  const res = await apiClient.get(path, { responseType: "blob" });
  const url = URL.createObjectURL(res.data);
  window.open(url, "_blank", "noopener");
  // Libère l'URL après un délai suffisant pour l'affichage
  setTimeout(() => URL.revokeObjectURL(url), 60_000);
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
  return openPdf(`/sales/pos/sales/${orderId}/ticket`);
}

/**
 * PDF d'une commande :
 * - vente comptoir → ticket de caisse
 * - autre commande → facture (auto-générée côté serveur si absente)
 */
export function printOrder(orderId: number | string): Promise<void> {
  return openPdf(`/sales/orders/${orderId}/print`);
}