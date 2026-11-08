/**
 * API client — wrapper Axios autour de l'ERP backend.
 *
 * Gère automatiquement :
 * - l'ajout du token JWT (Authorization: Bearer)
 * - le rafraîchissement du token
 * - les réponses d'erreur
 */
import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";

export const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1",
  timeout: 30000,
});

/** Code machine renvoyé par le serveur quand le profil est incomplet. */
export const COMPANY_INCOMPLETE = "company_incomplete";

/** Écran vers lequel ramener l'utilisateur dans ce cas. */
export const COMPANY_SETUP_PATH = "/setup/company";

// Intercepteur requête — ajoute le token
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = typeof window !== "undefined" ? localStorage.getItem("accessToken") : null;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error: AxiosError) => Promise.reject(error),
);

// Intercepteur réponse — rafraîchit le token si expiré
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value: unknown) => void;
  reject: (error: unknown) => void;
}> = [];

function processQueue(error: unknown) {
  failedQueue.forEach((prom) => {
    if (error) prom.reject(error);
    else prom.resolve(null);
  });
  failedQueue = [];
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        // Attend le rafraîchissement en cours
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then(() => apiClient(originalRequest));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const refreshToken = localStorage.getItem("refreshToken");
        if (refreshToken) {
          const res = await apiClient.post("/core/auth/refresh", {
            refresh_token: refreshToken,
          });
          const { access_token, refresh_token: newRefresh } = res.data;
          localStorage.setItem("accessToken", access_token);
          if (newRefresh) localStorage.setItem("refreshToken", newRefresh);
          processQueue(null);
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return apiClient(originalRequest);
        }
      } catch (refreshError) {
        processQueue(refreshError);
        localStorage.removeItem("accessToken");
        localStorage.removeItem("refreshToken");
        window.location.href = "/login";
      } finally {
        isRefreshing = false;
      }
    }

    // 409 « profil incomplet » : le serveur refuse la création d'un document
    // tant que les mentions obligatoires de l'entreprise manquent. On ramène
    // l'utilisateur au formulaire au lieu de le laisser devant un échec
    // inexpliqué — c'est le comportement demandé pour l'étape reportée.
    const failure = error.response?.data as { detail?: unknown } | undefined;
    const detail = failure?.detail;
    if (
      error.response?.status === 409 &&
      detail !== null &&
      typeof detail === "object" &&
      (detail as { code?: string }).code === COMPANY_INCOMPLETE &&
      typeof window !== "undefined" &&
      !window.location.pathname.startsWith(COMPANY_SETUP_PATH)
    ) {
      window.location.href = COMPANY_SETUP_PATH;
    }

    return Promise.reject(error);
  },
);

export type ApiResponse<T = unknown> = {
  data: T;
  status: number;
  statusText: string;
};

export type ApiError = {
  message: string;
  status?: number;
  detail?: string;
};

export function handleApiError(error: unknown): ApiError {
  if (error instanceof AxiosError) {
    return {
      message: error.response?.data?.detail || error.message,
      status: error.response?.status,
      detail: error.response?.data?.detail,
    };
  }
  if (error instanceof Error) {
    return { message: error.message };
  }
  return { message: "Erreur inconnue" };
}
