/**
 * Types partagés entre le frontend et le backend.
 */

export interface User {
  id: number;
  email: string;
  phone?: string;
  first_name: string;
  last_name: string;
  full_name?: string;
  is_active: boolean;
  is_verified: boolean;
  is_superuser: boolean;
  company_id: number;
  agency_id?: number;
  created_at: string;
  updated_at: string;
}

export interface UserWithRoles extends User {
  roles: Role[];
  permissions: string[];
}

export interface Company {
  id: number;
  name: string;
  code: string;
  domain?: string;
  phone?: string;
  email?: string;
  website?: string;
  address: Record<string, unknown>;
  /** Logo encodé en data URL (base64) */
  logo?: string | null;
  /** Établissement / agence principale (affiché à côté du nom) */
  establishment?: string | null;
  /** Slogan affiché sur les documents */
  slogan?: string | null;
  /** Numéro Compte Contribuable (NCC) */
  ncc?: string | null;
  /** RCCM */
  rccm?: string | null;
  /** Capital social */
  share_capital?: string | null;
  currency_code: string;
  tax_country?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Agency {
  id: number;
  company_id: number;
  name: string;
  code?: string;
  address: Record<string, unknown>;
  phone?: string;
  email?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Role {
  id: number;
  name: string;
  code: string;
  description?: string;
  is_system: boolean;
  is_global: boolean;
  company_id: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  permissions: Permission[];
}

export interface Permission {
  id: number;
  resource: string;
  action: string;
  description?: string;
  company_id: number;
}

export interface Token {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface LoginRequest {
  email: string;
  password: string;
  company_code?: string;
}

export interface ModuleInfo {
  name: string;
  version: string;
  status: string;
  is_active: boolean;
  config: Record<string, unknown>;
  installed_at?: string;
  activated_at?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
  has_more: boolean;
}

export interface Tax {
  id: number;
  name: string;
  code?: string;
  rate: number;
  type: string;
  is_exempt: boolean;
  is_active: boolean;
  is_default: boolean;
}

export interface Currency {
  code: string;
  name: string;
  symbol: string;
  decimal_places: number;
  is_active: boolean;
}

// Module status enum
export type ModuleStatus = "installed" | "active" | "inactive" | "not_installed";

// Catalogue types
export interface ProductCategory {
  id: number;
  name: string;
  code: string | null;
  description: string | null;
  parent_id: number | null;
  sale_mode: string;
  is_active: boolean;
  company_id: number;
}

export interface ProductUnit {
  id: number;
  name: string;
  code: string;
  symbol: string | null;
  is_active: boolean;
  company_id: number;
}

export interface Product {
  id: number;
  variants_count?: number;
  reference: string;
  barcode: string | null;
  name: string;
  description: string | null;
  category_id: number | null;
  brand: string | null;
  storage_type: string;
  purchase_unit_id: number | null;
  sale_unit_id: number | null;
  conversion_factor: number;
  sell_by_length: boolean;
  sale_mode: "unit" | "length" | "dual";
  is_bac_sheet: boolean;
  unit_length: number | null;
  price_per_meter: number | null;
  purchase_price: number | null;
  selling_price: number | null;
  margin_percent: number | null;
  tax_id: number | null;
  lead_time_days: number | null;
  reorder_point: number | null;
  primary_supplier_id: number | null;
  status: string;
  attributes: Record<string, any>;
  company_id: number;
  created_at: string;
  updated_at: string;
}

// Sales types
export interface QuoteLine {
  id: number;
  quote_id: number;
  product_id: number | null;
  variant_id: number | null;
  variant_name: string | null;
  description: string | null;
  quantity: number;
  unit: string | null;
  sell_by_length: boolean;
  unit_price: number;
  discount_percent: number;
  total_length: number;
  subtotal: number;
  cuts: QuoteCut[];
}

export interface QuoteCut {
  id: number;
  quantity: number;
  length: number;
  unit_price: number | null;
  total_length: number;
  subtotal: number;
}

export interface Quote {
  id: number;
  reference: string;
  partner_id: number;
  site_id: number | null;
  salesperson_id?: number | null;
  status: string;
  quote_date: string;
  valid_until: string | null;
  currency_code: string;
  amount_untaxed: number;
  discount_amount: number;
  tax_amount: number;
  amount_total: number;
  expected_margin: number | null;
  created_at: string;
  notes?: string | null;
  terms?: string | null;
  metadata_json?: {
    payment_term?: string;
    customer_reference?: string;
    tax_percent?: number;
    [key: string]: unknown;
  };
  lines: QuoteLine[];
}

export interface SalesOrder {
  id: number;
  reference: string;
  partner_id: number;
  site_id: number | null;
  notes?: string | null;
  quote_id: number | null;
  fulfillment_mode: string;
  status: string;
  order_date: string;
  currency_code: string;
  amount_untaxed: number;
  tax_amount: number;
  shipping_amount: number;
  amount_total: number;
  paid_amount: number;
  created_at: string;
  lines: OrderLine[];
}

export interface OrderLine {
  id: number;
  order_id: number;
  product_id: number | null;
  variant_id: number | null;
  variant_name: string | null;
  description: string | null;
  quantity_ordered: number;
  quantity_reserved: number;
  quantity_available: number;
  quantity_to_purchase: number;
  quantity_purchased: number;
  quantity_delivered: number;
  sell_by_length: boolean;
  unit_price: number;
  total_length: number;
  subtotal: number;
  remaining_to_supply: number;
  cuts: OrderCut[];
}

export interface OrderCut {
  id: number;
  quantity: number;
  length: number;
  unit_price: number | null;
  total_length: number;
  subtotal: number;
}

// Stock types
export interface Warehouse {
  id: number;
  name: string;
  code: string | null;
  warehouse_type: string;
  is_active: boolean;
}

export interface WarehouseCreate {
  name: string;
  code?: string;
  warehouse_type?: string;
  address?: Record<string, any>;
}

export interface StockLevel {
  id: number;
  warehouse_id: number;
  product_id: number;
  quantity_on_hand: number;
  quantity_reserved: number;
  quantity_incoming: number;
  available: number;
}

export interface StockMovement {
  id: number;
  movement_type: string;
  warehouse_id: number;
  target_warehouse_id: number | null;
  product_id: number;
  quantity: number;
  unit_cost: number | null;
  created_at: string;
}

export interface MovementCreate {
  movement_type: string;
  warehouse_id: number;
  target_warehouse_id?: number;
  product_id: number;
  quantity: number;
  unit_cost?: number;
  reference_document?: string;
  reference_id?: number;
  notes?: string;
}

// Dashboard types
export interface DashboardStats {
  total_quotes: number;
  total_orders: number;
  total_products: number;
  total_partners: number;
  total_stock_value: number;
  revenue_today: number;
  revenue_month: number;
  pending_deliveries: number;
  orders_in_production: number;
}

// CRM types
export interface Contact {
  id: number;
  partner_id: number;
  first_name: string;
  last_name: string;
  phone: string | null;
  email: string | null;
  job_title: string | null;
  is_primary: boolean;
  full_name: string;
  company_id: number;
}

export interface PartnerAddress {
  id: number;
  partner_id: number;
  address_type: string;
  label: string | null;
  line_1: string | null;
  line_2: string | null;
  city: string | null;
  state: string | null;
  postal_code: string | null;
  country: string;
  latitude: number | null;
  longitude: number | null;
  is_primary: boolean;
  company_id: number;
}

export interface Partner {
  id: number;
  company_id: number;
  name: string;
  code: string | null;
  role: string;
  entity_type: string;
  gender: string;
  phone: string | null;
  email: string | null;
  website: string | null;
  tax_number: string | null;
  registration_number: string | null;
  credit_limit: number | null;
  payment_terms_days: number | null;
  default_discount: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  contacts: Contact[];
  addresses: PartnerAddress[];
}

export interface PartnerCreate {
  name: string;
  code?: string;
  role?: string;
  entity_type?: string;
  gender?: string;
  phone?: string;
  email?: string;
  website?: string;
  tax_number?: string;
  registration_number?: string;
  credit_limit?: number;
  payment_terms_days?: number;
  default_discount?: number;
  contacts?: ContactCreate[];
  addresses?: PartnerAddressCreate[];
}

export interface ContactCreate {
  first_name: string;
  last_name: string;
  phone?: string;
  email?: string;
  job_title?: string;
  is_primary?: boolean;
}

export interface PartnerAddressCreate {
  address_type?: string;
  label?: string;
  line_1?: string;
  line_2?: string;
  city?: string;
  state?: string;
  postal_code?: string;
  country?: string;
  latitude?: number;
  longitude?: number;
  is_primary?: boolean;
}

export interface Site {
  id: number;
  partner_id: number;
  company_id: number;
  name: string;
  code: string | null;
  address: Record<string, any>;
  city: string | null;
  region: string | null;
  country: string;
  start_date: string | null;
  end_date: string | null;
  budget: number | null;
  status: string;
  manager_name: string | null;
  manager_phone: string | null;
  description: string | null;
  is_active: boolean;
  created_at: string;
}

export interface SiteCreate {
  name: string;
  code?: string;
  address?: Record<string, any>;
  city?: string;
  region?: string;
  country?: string;
  start_date?: string;
  end_date?: string;
  budget?: number;
  status?: string;
  manager_name?: string;
  manager_phone?: string;
  description?: string;
}

// Sales create types
export interface QuoteCreate {
  partner_id: number;
  site_id?: number | null;
  /** Contact commercial — choisi par admin/manager, sinon = créateur. */
  salesperson_id?: number | null;
  quote_date?: string;
  valid_until?: string | null;
  currency_code?: string;
  notes?: string | null;
  terms?: string | null;
  discount_amount?: number;
  tax_percent?: number;
  payment_term?: string | null;
  customer_reference?: string | null;
  lines: QuoteLineCreate[];
}

export interface QuoteLineCreate {
  product_id?: number;
  variant_id?: number | null;
  description?: string;
  quantity?: number;
  unit?: string;
  sell_by_length?: boolean;
  unit_price?: number;
  discount_percent?: number;
  cuts?: QuoteCutCreate[];
}

export interface QuoteCutCreate {
  quantity?: number;
  length: number;
  unit_price?: number;
}

export interface QuoteUpdate {
  partner_id?: number;
  site_id?: number | null;
  salesperson_id?: number | null;
  quote_date?: string;
  valid_until?: string | null;
  currency_code?: string;
  notes?: string | null;
  terms?: string | null;
  discount_amount?: number | null;
  tax_percent?: number | null;
  payment_term?: string | null;
  customer_reference?: string | null;
  status?: string;
  lines?: QuoteLineCreate[];
}

export interface SalesOrderUpdate {
  partner_id?: number;
  site_id?: number | null;
  delivery_date_planned?: string | null;
  currency_code?: string;
  notes?: string | null;
  status?: string;
  lines?: OrderLineCreate[];
}

export interface SalesOrderCreate {
  partner_id: number;
  site_id?: number;
  quote_id?: number;
  fulfillment_mode?: string;
  delivery_date_planned?: string;
  currency_code?: string;
  notes?: string;
  lines: OrderLineCreate[];
}

export interface OrderLineCreate {
  product_id?: number;
  variant_id?: number | null;
  description?: string;
  quantity_ordered?: number;
  unit?: string;
  sell_by_length?: boolean;
  unit_price?: number;
  purchase_price?: number;
  discount_percent?: number;
  cuts?: OrderCutCreate[];
}

export interface OrderCutCreate {
  quantity?: number;
  length: number;
  unit_price?: number;
}

// Catégories — arbre avec modes de vente résolus
export interface CategoryTreeNode {
  id: number;
  name: string;
  code: string | null;
  description: string | null;
  parent_id: number | null;
  sale_mode: string;
  is_active: boolean;
  company_id: number;
  resolved_sale_mode: "unit" | "length" | "dual";
  sells_by_length: boolean;
  children: CategoryTreeNode[];
}
export interface PropertyValue {
  id: number;
  value: string;
  position: number;
}

export interface ProductProperty {
  id: number;
  name: string;
  position: number;
  is_active: boolean;
  values: PropertyValue[];
}

export interface VariantPropertyInfo {
  property_id: number;
  property_name: string;
  value_id: number;
  value: string;
}

export interface ProductVariant {
  id: number;
  product_id: number;
  reference: string | null;
  name_suffix: string;
  selling_price: number | null;
  purchase_price: number | null;
  price_per_meter: number | null;
  is_default: boolean;
  is_active: boolean;
  properties: VariantPropertyInfo[];
}

// ---------------------------------------------------------------------------
// Module Achats
// ---------------------------------------------------------------------------
export interface Supplier {
  id: number;
  company_id: number;
  name: string;
  code: string | null;
  phone: string | null;
  email: string | null;
  website: string | null;
  tax_number: string | null;
  registration_number: string | null;
  payment_terms_days: number | null;
  is_active: boolean;
  role: string;
  rating: number | null;
  delivery_days: number | null;
  category_ids: number[];
  created_at: string;
  updated_at: string;
}

export interface SupplierCreate {
  name: string;
  code?: string | null;
  phone?: string | null;
  email?: string | null;
  website?: string | null;
  tax_number?: string | null;
  registration_number?: string | null;
  payment_terms_days?: number | null;
  is_active?: boolean;
  rating?: number | null;
  delivery_days?: number | null;
  category_ids?: number[];
}

export type SupplierUpdate = Partial<SupplierCreate>;

export interface SupplierSuggest {
  id: number;
  name: string;
  rating: number | null;
  delivery_days: number | null;
  last_price: number | null;
}

export interface PurchaseRequestLine {
  id: number;
  request_id: number;
  product_id: number | null;
  description: string | null;
  quantity: number;
  unit: string | null;
  estimated_unit_price: number;
  subtotal: number;
}

export interface PurchaseRequest {
  id: number;
  company_id: number;
  number: string;
  requester_id: number | null;
  validator_id: number | null;
  supplier_id: number | null;
  status: string;
  priority: string;
  request_date: string;
  needed_by: string | null;
  submitted_at: string | null;
  validated_at: string | null;
  rejection_reason: string | null;
  estimated_total: number;
  notes: string | null;
  lines: PurchaseRequestLine[];
  created_at: string;
  updated_at: string;
}

export interface PurchaseRequestLineCreate {
  product_id?: number | null;
  description?: string | null;
  quantity?: number;
  unit?: string | null;
  estimated_unit_price?: number;
}

export interface PurchaseRequestCreate {
  supplier_id?: number | null;
  priority?: string;
  request_date?: string | null;
  needed_by?: string | null;
  notes?: string | null;
  lines?: PurchaseRequestLineCreate[];
}

export interface PurchaseRequestUpdate {
  supplier_id?: number | null;
  priority?: string;
  needed_by?: string | null;
  notes?: string | null;
  lines?: PurchaseRequestLineCreate[];
}

export interface PurchaseOrderLine {
  id: number;
  order_id: number;
  product_id: number | null;
  description: string | null;
  quantity: number;
  quantity_received: number;
  unit: string | null;
  unit_price: number;
  tax_rate: number;
  discount_percent: number;
  subtotal: number;
  tax_amount: number;
  total: number;
  quantity_remaining: number;
}

export interface PurchaseOrder {
  id: number;
  company_id: number;
  number: string;
  supplier_id: number;
  origin_request_id: number | null;
  status: string;
  order_date: string;
  expected_date: string | null;
  currency_code: string;
  amount_untaxed: number;
  tax_amount: number;
  amount_total: number;
  payment_terms_days: number | null;
  notes: string | null;
  confirmed_at: string | null;
  cancelled_at: string | null;
  lines: PurchaseOrderLine[];
  created_at: string;
  updated_at: string;
}

export interface PurchaseOrderLineCreate {
  product_id?: number | null;
  description?: string | null;
  quantity?: number;
  unit?: string | null;
  unit_price?: number;
  tax_rate?: number;
  discount_percent?: number;
}

export interface PurchaseOrderCreate {
  supplier_id: number;
  origin_request_id?: number | null;
  order_date?: string | null;
  expected_date?: string | null;
  currency_code?: string;
  payment_terms_days?: number | null;
  tax_percent?: number;
  notes?: string | null;
  lines?: PurchaseOrderLineCreate[];
}

export interface PurchaseReceptionLine {
  id: number;
  reception_id: number;
  order_line_id: number | null;
  product_id: number | null;
  description: string | null;
  quantity: number;
  unit_cost: number | null;
}

export interface PurchaseReception {
  id: number;
  company_id: number;
  number: string;
  order_id: number;
  warehouse_id: number;
  status: string;
  reception_date: string;
  validated_at: string | null;
  received_by: number | null;
  notes: string | null;
  lines: PurchaseReceptionLine[];
  created_at: string;
  updated_at: string;
}


export interface PurchaseReceptionLineCreate {
  order_line_id?: number | null;
  product_id?: number | null;
  description?: string | null;
  quantity?: number;
  unit_cost?: number | null;
}

export interface PurchaseReceptionCreate {
  order_id: number;
  warehouse_id: number;
  reception_date?: string | null;
  notes?: string | null;
  lines?: PurchaseReceptionLineCreate[];
}

export interface SupplierInvoiceLine {
  id: number;
  invoice_id: number;
  order_line_id: number | null;
  product_id: number | null;
  description: string | null;
  quantity: number;
  unit_price: number;
  tax_rate: number;
  subtotal: number;
  tax_amount: number;
}

export interface SupplierInvoice {
  id: number;
  company_id: number;
  reference: string;
  supplier_invoice_number: string | null;
  supplier_id: number;
  order_id: number | null;
  reception_id: number | null;
  status: string;
  invoice_date: string;
  due_date: string | null;
  currency_code: string;
  amount_untaxed: number;
  tax_amount: number;
  amount_total: number;
  paid_amount: number;
  amount_due: number;
  matching_status: string | null;
  matching_details: Record<string, unknown> | null;
  posted_at: string | null;
  notes: string | null;
  lines: SupplierInvoiceLine[];
  created_at: string;
  updated_at: string;
}

export interface SupplierInvoiceLineCreate {
  order_line_id?: number | null;
  product_id?: number | null;
  description?: string | null;
  quantity?: number;
  unit_price?: number;
  tax_rate?: number;
}

export interface SupplierInvoiceCreate {
  supplier_id: number;
  supplier_invoice_number?: string | null;
  order_id?: number | null;
  reception_id?: number | null;
  invoice_date?: string | null;
  due_date?: string | null;
  currency_code?: string;
  notes?: string | null;
  lines?: SupplierInvoiceLineCreate[];
}

export interface SupplierInvoicePay {
  amount: number;
  payment_date?: string | null;
  method?: string;
}

export interface MatchingLineDetail {
  product_id?: number | null;
  description?: string | null;
  ordered_qty?: number;
  received_qty?: number;
  invoiced_qty?: number;
  po_unit_price?: number | null;
  invoice_unit_price?: number | null;
  issues?: string[];
}

export interface MatchingResult {
  status: string;
  lines?: MatchingLineDetail[];
  ordered_total?: number | null;
  invoiced_total?: number | null;
}

// --- Avoirs / notes de crédit (comptabilité) ---
export interface CreditNote {
  id: number;
  company_id: number;
  reference: string;
  original_invoice_id: number | null;
  partner_id: number | null;
  type: "customer" | "supplier";
  amount_untaxed: number;
  tax_amount: number;
  amount_total: number;
  currency_code: string;
  status: "draft" | "issued" | "applied";
  credit_date: string;
  reason: string | null;
  notes: string | null;
  journal_entry_id: number | null;
  amount_due: number;
}

export interface CreditNoteCreate {
  original_invoice_id?: number | null;
  partner_id?: number | null;
  type: "customer" | "supplier";
  amount_untaxed?: number;
  tax_amount?: number;
  amount_total?: number;
  currency_code?: string;
  credit_date?: string | null;
  reason?: string | null;
  notes?: string | null;
}

export interface CreditNoteIssue {
  credit_date?: string | null;
  notes?: string | null;
}

export interface CreditNoteApply {
  invoice_id: number;
  amount_to_apply?: number | null;
}

