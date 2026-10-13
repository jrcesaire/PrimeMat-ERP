/**
 * Hooks pour le module Catalogue — produits, catégories, unités.
 */
"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import {
  CategoryTreeNode,
  Product,
  ProductCategory,
  ProductUnit,
  ProductProperty,
  ProductVariant,
} from "@/lib/types";

export const CATALOGUE_KEYS = {
  products: "catalogue-products",
  categories: "catalogue-categories",
  units: "catalogue-units",
};

// --- Products ---
export function useProducts(search?: string, limit = 100, categoryId?: number | null) {
  return useQuery({
    queryKey: [CATALOGUE_KEYS.products, search ?? null, limit, categoryId ?? null],
    queryFn: async (): Promise<Product[]> => {
      const params = new URLSearchParams({ limit: String(limit) });
      if (search && search.trim()) params.set("search", search.trim());
      if (categoryId) params.set("category_id", String(categoryId));
      const res = await apiClient.get(`/catalogue/products?${params.toString()}`);
      return res.data;
    },
  });
}

export function useProduct(productId: number) {
  return useQuery({
    queryKey: [CATALOGUE_KEYS.products, productId],
    queryFn: async (): Promise<Product> => {
      const res = await apiClient.get(`/catalogue/products/${productId}`);
      return res.data;
    },
    enabled: !!productId,
  });
}

// --- Categories ---
export function useCategories() {
  return useQuery({
    queryKey: [CATALOGUE_KEYS.categories],
    queryFn: async (): Promise<ProductCategory[]> => {
      const res = await apiClient.get("/catalogue/categories");
      return res.data;
    },
  });
}

/** Arborescence des catégories avec modes de vente résolus. */
export function useCategoryTree() {
  return useQuery({
    queryKey: ["catalogue-category-tree"],
    queryFn: async (): Promise<CategoryTreeNode[]> => {
      const res = await apiClient.get("/catalogue/categories/tree");
      return res.data;
    },
  });
}

// --- Mutations ---
export function useCreateProduct() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: Partial<Product>): Promise<Product> => {
      const res = await apiClient.post("/catalogue/products", data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [CATALOGUE_KEYS.products] });
    },
  });
}

export function useUpdateProduct() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      data,
    }: {
      id: number;
      data: Partial<Product>;
    }): Promise<Product> => {
      const res = await apiClient.put(`/catalogue/products/${id}`, data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [CATALOGUE_KEYS.products] });
    },
  });
}

export function useCreateCategory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: {
      name: string;
      code?: string;
      parent_id?: number;
      sale_mode?: string;
    }): Promise<ProductCategory> => {
      const res = await apiClient.post("/catalogue/categories", data);
      queryClient.invalidateQueries({ queryKey: [CATALOGUE_KEYS.categories] });
      queryClient.invalidateQueries({ queryKey: ["catalogue-category-tree"] });
      return res.data;
    },
  });
}

// --- Units ---
export function useUnits() {
  return useQuery({
    queryKey: [CATALOGUE_KEYS.units],
    queryFn: async (): Promise<ProductUnit[]> => {
      const res = await apiClient.get("/catalogue/units");
      return res.data;
    },
  });
}
// --- Propriétés & variantes ---
export function useProperties() {
  return useQuery({
    queryKey: ["catalogue-properties"],
    queryFn: async (): Promise<ProductProperty[]> => {
      const res = await apiClient.get("/catalogue/properties");
      return res.data;
    },
  });
}

export function useVariants(productId: number) {
  return useQuery({
    queryKey: ["product-variants", productId],
    queryFn: async (): Promise<ProductVariant[]> => {
      const res = await apiClient.get(`/catalogue/products/${productId}/variants`);
      return res.data;
    },
    enabled: !!productId,
  });
}

function invalidateVariants(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: ["product-variants"] });
  qc.invalidateQueries({ queryKey: [CATALOGUE_KEYS.products] });
}

export function useCreateProperty() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: { name: string; values?: string[] }): Promise<ProductProperty> => {
      const res = await apiClient.post("/catalogue/properties", data);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["catalogue-properties"] }),
  });
}

export function useDeleteProperty() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (propertyId: number) => {
      await apiClient.delete(`/catalogue/properties/${propertyId}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["catalogue-properties"] }),
  });
}

export function useAddPropertyValue() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ propertyId, value }: { propertyId: number; value: string }): Promise<unknown> => {
      const res = await apiClient.post(`/catalogue/properties/${propertyId}/values`, { value });
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["catalogue-properties"] }),
  });
}

export function useDeletePropertyValue() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ propertyId, valueId }: { propertyId: number; valueId: number }) => {
      await apiClient.delete(`/catalogue/properties/${propertyId}/values/${valueId}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["catalogue-properties"] }),
  });
}

export function useGenerateVariants() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ productId, values, copyPrices = true }: {
      productId: number;
      values: Record<number, number[]>;
      copyPrices?: boolean;
    }): Promise<ProductVariant[]> => {
      const res = await apiClient.post(`/catalogue/products/${productId}/variants/generate`, {
        values,
        copy_prices: copyPrices,
      });
      return res.data;
    },
    onSuccess: (_d, vars) => invalidateVariants(qc),
  });
}

export function useUpdateVariant() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: number; data: Partial<ProductVariant> }): Promise<ProductVariant> => {
      const res = await apiClient.patch(`/catalogue/variants/${id}`, data);
      return res.data;
    },
    onSuccess: (_d, vars) => invalidateVariants(qc),
  });
}

export function useDeleteVariant() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await apiClient.delete(`/catalogue/variants/${id}`);
    },
    onSuccess: (_d, id) => invalidateVariants(qc),
  });
}

