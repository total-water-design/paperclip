/**
 * Development shim for the package-local runner runtime.
 *
 * Source-mode and deployed server entry points both resolve the runner through
 * its package boundary. This keeps the runner's runtime dependency graph
 * attached to it in filtered and detached installs. The server build replaces
 * the emitted shim with the package's compiled `dist` tree for published
 * packages. Keep server imports pointed at this relative boundary.
 */
type RunnerModule = typeof import("@paperclipai/paperclip-runner");

export type {
  PaperclipJsonValue,
  PaperclipQuestionResponse,
  PaperclipSemanticActionBinding,
  PaperclipSemanticActionId,
  PaperclipSemanticAuthorizationRecord,
  PaperclipSemanticRunContext,
  PaperclipSemanticToolCall,
  PaperclipSemanticToolDefinition,
  PaperclipSemanticToolResult,
  PrpEvent,
  PrpStructuredRunResult,
  PrpTerminalState,
} from "@paperclipai/paperclip-runner";
export type DurablePrpControlPlane =
  import("@paperclipai/paperclip-runner").DurablePrpControlPlane;
export type PaperclipSemanticDispatcher =
  import("@paperclipai/paperclip-runner").PaperclipSemanticDispatcher;

const runner = await import("@paperclipai/paperclip-runner") as RunnerModule;

export const DurablePrpControlPlane = runner.DurablePrpControlPlane;
export const PaperclipSemanticDispatcher = runner.PaperclipSemanticDispatcher;
export const validatePrpEvent = runner.validatePrpEvent;
export const validatePrpStructuredRunResult =
  runner.validatePrpStructuredRunResult;
