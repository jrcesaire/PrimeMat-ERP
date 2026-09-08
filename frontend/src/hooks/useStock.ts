/**
 * Hooks pour le module Stock — entrepôts, niveaux, mouvements.
 */
"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import {
  MovementCreate,
  Warehouse,
  WarehouseCreate,
  StockLevel,
  StockMovement,
} from "@/lib/types";

export const STOCK_KEYS = {
  warehouses: "stock-warehouses",
  levels: "stock-levels",
  movements: "stock-movements",
};

export function useWarehouses() {
  return useQuery({
    queryKey: [STOCK_KEYS.warehouses],
    queryFn: async (): Promise<Warehouse[]> => {
      const res = await apiClient.get("/stock/warehouses");
      return res.data;
    },
  });
}

export function useStockLevels(productId?: number, warehouseId?: number) {
  return useQuery({
    queryKey: [STOCK_KEYS.levels, productId, warehouseId],
    queryFn: async (): Promise<StockLevel[]> => {
      const params = new URLSearchParams();
      if (productId) params.append("product_id", String(productId));
      if (warehouseId) params.append("warehouse_id", String(warehouseId));
      const res = await apiClient.get(`/stock/levels?${params.toString()}`);
      return res.data;
    },
  });
}

export function useStockMovements(skip = 0, limit = 50, productId?: number) {
  return useQuery({
    queryKey: [STOCK_KEYS.movements, skip, limit, productId],
    queryFn: async (): Promise<StockMovement[]> => {
      const params = new URLSearchParams({
        skip: String(skip),
        limit: String(limit),
      });
      if (productId) params.append("product_id", String(productId));
      const res = await apiClient.get(`/stock/movements?${params.toString()}`);
      return res.data;
    },
  });
}

export function useCreateWarehouse() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: WarehouseCreate): Promise<Warehouse> => {
      const res = await apiClient.post("/stock/warehouses", data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [STOCK_KEYS.warehouses] });
    },
  });
}

export function useCreateMovement() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: MovementCreate): Promise<StockMovement> => {
      const res = await apiClient.post("/stock/movements", data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [STOCK_KEYS.movements] });
      queryClient.invalidateQueries({ queryKey: [STOCK_KEYS.levels] });
    },
  });
}
