/**
 * Hooks du module Paie — employés, contrats, périodes/lots, bulletins,
 * paramètres (taux) et déclarations CNPS / ITS.
 */
"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import {
  CnpsDeclaration,
  ItsDeclaration,
  PayrollEmployee,
  PayrollEmployeeCreate,
  PayrollPayslip,
  PayrollPeriod,
  PayrollRun,
  PayrollSettings,
  PayrollStructure,
} from "@/lib/types";

export const PAYROLL_KEYS = {
  employees: "payroll-employees",
  structures: "payroll-structures",
  periods: "payroll-periods",
  payslips: "payroll-payslips",
  settings: "payroll-settings",
  cnps: "payroll-cnps",
  its: "payroll-its",
};

// --- Employés ------------------------------------------------------- #
export function useEmployees(search?: string) {
  return useQuery({
    queryKey: [PAYROLL_KEYS.employees, search ?? ""],
    queryFn: async (): Promise<PayrollEmployee[]> => {
      const res = await apiClient.get("/payroll/employees", {
        params: search ? { search, limit: 200 } : { limit: 200 },
      });
      return res.data;
    },
  });
}

export function useCreateEmployee() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: PayrollEmployeeCreate): Promise<PayrollEmployee> => {
      const res = await apiClient.post("/payroll/employees", data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PAYROLL_KEYS.employees] });
    },
  });
}

export function useDeleteEmployee() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number): Promise<void> => {
      await apiClient.delete(`/payroll/employees/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PAYROLL_KEYS.employees] });
    },
  });
}

// --- Structures ----------------------------------------------------- #
export function usePayrollStructures() {
  return useQuery({
    queryKey: [PAYROLL_KEYS.structures],
    queryFn: async (): Promise<PayrollStructure[]> => {
      const res = await apiClient.get("/payroll/structures");
      return res.data;
    },
  });
}

// --- Périodes & lots ------------------------------------------------ #
export function usePayrollPeriods() {
  return useQuery({
    queryKey: [PAYROLL_KEYS.periods],
    queryFn: async (): Promise<PayrollPeriod[]> => {
      const res = await apiClient.get("/payroll/periods");
      return res.data;
    },
  });
}

export function useCreatePeriod() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: {
      name: string;
      date_start: string;
      date_end: string;
      payment_date?: string | null;
    }): Promise<PayrollPeriod> => {
      const res = await apiClient.post("/payroll/periods", data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PAYROLL_KEYS.periods] });
    },
  });
}

export function useGenerateRun() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (periodId: number): Promise<PayrollRun> => {
      const res = await apiClient.post(`/payroll/periods/${periodId}/runs`);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PAYROLL_KEYS.payslips] });
    },
  });
}

export function useValidateRun() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (runId: number): Promise<PayrollRun> => {
      const res = await apiClient.post(`/payroll/runs/${runId}/validate`);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PAYROLL_KEYS.payslips] });
    },
  });
}

export function usePayRun() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (runId: number): Promise<PayrollRun> => {
      const res = await apiClient.post(`/payroll/runs/${runId}/pay`);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PAYROLL_KEYS.payslips] });
    },
  });
}

// --- Bulletins ------------------------------------------------------ #
export function usePayslips(periodId?: number | null) {
  return useQuery({
    queryKey: [PAYROLL_KEYS.payslips, periodId ?? null],
    queryFn: async (): Promise<PayrollPayslip[]> => {
      const res = await apiClient.get("/payroll/payslips", {
        params: { limit: 500, ...(periodId ? { run_id: periodId } : {}) },
      });
      return res.data;
    },
  });
}

export function useComputePayslip() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number): Promise<PayrollPayslip> => {
      const res = await apiClient.post(`/payroll/payslips/${id}/compute`);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PAYROLL_KEYS.payslips] });
    },
  });
}

export function useValidatePayslip() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number): Promise<PayrollPayslip> => {
      const res = await apiClient.post(`/payroll/payslips/${id}/validate`);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PAYROLL_KEYS.payslips] });
    },
  });
}

export function useAddPayslipInput() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (args: {
      id: number;
      input_code: string;
      name: string;
      amount: number;
    }): Promise<PayrollPayslip> => {
      const { id, ...body } = args;
      const res = await apiClient.post(`/payroll/payslips/${id}/inputs`, body);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PAYROLL_KEYS.payslips] });
    },
  });
}

// --- Paramètres de paie (taux) -------------------------------------- #
export function usePayrollSettings() {
  return useQuery({
    queryKey: [PAYROLL_KEYS.settings],
    queryFn: async (): Promise<PayrollSettings> => {
      const res = await apiClient.get("/payroll/settings");
      return res.data;
    },
  });
}

export function useUpdatePayrollSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: Partial<PayrollSettings>): Promise<PayrollSettings> => {
      const res = await apiClient.put("/payroll/settings", data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PAYROLL_KEYS.settings] });
    },
  });
}

export function useApplyPayrollSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (): Promise<{ status: string }> => {
      const res = await apiClient.post("/payroll/settings/apply");
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PAYROLL_KEYS.settings] });
    },
  });
}

// --- Déclarations --------------------------------------------------- #
export function useCnpsDeclaration(periodId: number | null) {
  return useQuery({
    queryKey: [PAYROLL_KEYS.cnps, periodId],
    enabled: !!periodId,
    queryFn: async (): Promise<CnpsDeclaration> => {
      const res = await apiClient.get("/payroll/declarations/cnps", {
        params: { period_id: periodId },
      });
      return res.data;
    },
  });
}

export function useItsDeclaration(periodId: number | null) {
  return useQuery({
    queryKey: [PAYROLL_KEYS.its, periodId],
    enabled: !!periodId,
    queryFn: async (): Promise<ItsDeclaration> => {
      const res = await apiClient.get("/payroll/declarations/its", {
        params: { period_id: periodId },
      });
      return res.data;
    },
  });
}

