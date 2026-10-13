/**
 * Point d'entrée public du système de confirmation.
 */
export { ConfirmContext } from "./ConfirmContext";
export { ConfirmProvider } from "./ConfirmProvider";
export {
  confirmBackToDraftOptions,
  confirmCloseOptions,
  confirmDeleteOptions,
  confirmHardDeleteOptions,
  confirmPostOptions,
} from "./confirmPresets";
export type {
  ConfirmFn,
  ConfirmOptions,
  ConfirmReason,
  ConfirmRequest,
  ConfirmResult,
  ConfirmTone,
} from "./types";
export { useConfirm } from "./useConfirm";
