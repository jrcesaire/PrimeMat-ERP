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
} from "@/lib/types";

export const CATALOGUE_KEYS = {
  products: "catalogue-products",
  categories: "catalogue-categories",
  units: "catalogue-units",
};

// --- Products ---
export function useProducts() {
  return useQuery({
    queryKey: [CATALOGUE_KEYS.products],
    queryFn: async (): Promise<Product[]> => {
      const res = await apiClient.get("/catalogue/products");
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
