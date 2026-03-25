export type ID = string;

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
}

export type AuthMode = "local_open" | "password" | string;

export interface PaginatedResponse<T> {
  success: boolean;
  data: T[];
  meta: {
    total: number;
  };
}

export interface User {
  id: ID;
  email: string;
  full_name: string;
}

export interface AppConfig {
  auth_mode: AuthMode;
  default_workspace_id?: ID | null;
  runtime_types: string[];
  feature_flags: Record<string, boolean>;
  environment_profile?: EnvironmentProfile | null;
}

export interface EnvironmentCapability {
  name: string;
  installed: boolean;
  version?: string | null;
  required: boolean;
  status: "ready" | "degraded" | "missing" | string;
  source: string;
  message?: string | null;
  install_hint?: string | null;
}

export interface EnvironmentSummary {
  status: "ready" | "degraded" | "missing" | string;
  ready_count: number;
  degraded_count: number;
  missing_count: number;
  missing_required: string[];
  warnings: string[];
}

export interface EnvironmentProfile {
  slug: string;
  name: string;
  required_capabilities: string[];
  optional_capabilities: string[];
  workspace_capabilities: string[];
  default_shell?: string | null;
}

export interface WorkspaceEnvironmentStatus {
  workspace_id: ID;
  workspace_name: string;
  root_path?: string | null;
  status: "ready" | "degraded" | "missing" | string;
  capabilities: EnvironmentCapability[];
  summary: EnvironmentSummary;
}

export interface CapabilityRequirement {
  name: string;
  scope: "machine" | "workspace" | string;
  required: boolean;
  reason?: string | null;
}

export interface SkillCompatibilityStatus {
  status: "ready" | "warn" | "blocked" | string;
  message?: string | null;
  missing_required_capabilities: string[];
  missing_workspace_requirements: string[];
  missing_recommended_capabilities: string[];
}

export interface RuntimeDoctorSnapshot {
  runtime_id: ID;
  runtime_name: string;
  runtime_type: string;
  status: string;
  doctor_status?: string | null;
  last_capability_check_at?: string | null;
}

export interface DoctorCheckResult {
  profile: EnvironmentProfile;
  default_workspace_id?: ID | null;
  machine_capabilities: EnvironmentCapability[];
  machine_summary: EnvironmentSummary;
  workspace?: WorkspaceEnvironmentStatus | null;
  runtimes: RuntimeDoctorSnapshot[];
  install_guidance: string[];
  skill_compatibility: Record<string, number>;
}

export interface EnvironmentOverview {
  profile: EnvironmentProfile;
  default_workspace_id?: ID | null;
  runtime_types: string[];
  runtimes: RuntimeDoctorSnapshot[];
}

export interface Workspace {
  id: ID;
  name: string;
  slug: string;
  description?: string | null;
  owner_id: ID;
  workspace_root_path?: string | null;
  default_provider_id?: ID | null;
  default_model_id?: ID | null;
  default_provider_connection_id?: ID | null;
  default_model_name?: string | null;
  default_embedding_model_name?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConversationModelBinding {
  provider_connection_id?: ID | null;
  provider_connection_name?: string | null;
  model_name?: string | null;
}

export interface Conversation extends ConversationModelBinding {
  id: ID;
  workspace_id: ID;
  title: string;
  created_by_id: ID;
  provider_id?: ID | null;
  model_id?: ID | null;
  use_knowledge: boolean;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeChunkReference {
  document_id: ID;
  document_name: string;
  chunk_id: ID;
  excerpt: string;
  score: number;
}

export interface Message {
  id: ID;
  conversation_id: ID;
  runtime_execution_id?: ID | null;
  role: "system" | "user" | "assistant";
  content: string;
  sources_json?: KnowledgeChunkReference[] | null;
  created_at: string;
  updated_at: string;
}

export type ChatMode =
  | "understand_repo"
  | "inspect_repo"
  | "verify_repo"
  | "propose_fix"
  | "inspect_desktop"
  | "verify_desktop"
  | "operate_desktop";

export interface ChatModeSummary {
  active_mode: ChatMode;
  requested_mode?: ChatMode | null;
  inferred_from: "user_selection" | "auto_router" | string;
  rationale: string;
}

export interface SkillInvocationSummary {
  kind: "doctor" | "cli" | "browser" | string;
  title: string;
  summary: string;
  status: "queued" | "succeeded" | "failed" | "ready" | string;
  runtime_execution_id?: ID | null;
  runtime_session_id?: ID | null;
  command_preview?: string | Array<Record<string, unknown>> | null;
  output_excerpt?: string | null;
  exit_code?: number | null;
  current_url?: string | null;
  artifact_summaries?: Array<Record<string, unknown>>;
  is_read_only?: boolean;
}

export interface ChatEvidenceItem {
  title: string;
  type: "doctor" | "command_output" | "browser_capture" | "knowledge" | string;
  runtime_execution_id?: ID | null;
  content: string;
  label?: string | null;
  path?: string | null;
  current_url?: string | null;
  command_preview?: string | null;
  exit_code?: number | null;
  stderr_excerpt?: string | null;
  source_names?: string[] | null;
  artifact_summaries?: Array<Record<string, unknown>>;
  metadata?: Record<string, unknown> | null;
}

export type ScenarioTag =
  | "repo_onboarding"
  | "verify_local_readiness"
  | "trace_feature_or_bug"
  | "run_verification_workflow"
  | "knowledge_assisted_troubleshooting"
  | string;

export interface ChatRecommendedAction {
  label: string;
  reason?: string | null;
}

export interface GroundingSignal {
  id: string;
  kind: string;
  label: string;
  value: string;
  source_layer: "request" | "workspace" | "repo" | "runtime" | "browser" | "desktop" | "knowledge" | string;
  status?: "ready" | "observed" | "warning" | string;
  reason?: string | null;
}

export interface GroundedTarget {
  type:
    | "workspace"
    | "route"
    | "module"
    | "command"
    | "runtime"
    | "file"
    | "browser"
    | "desktop"
    | "app"
    | "window"
    | "control"
    | "process"
    | "system"
    | string;
  label: string;
  value: string;
  reason: string;
  source_signal_ids?: string[];
  status?: "primary" | "candidate" | "observed" | string;
}

export interface ChatGroundingSummary {
  headline: string;
  summary: string;
  signals: GroundingSignal[];
}

export interface ChatReflectionSummary {
  triggered: boolean;
  summary: string;
  reason?: string | null;
  next_probe?: string | null;
  confidence?: number | null;
}

export interface ChatProposalTarget {
  file_path: string;
  reason: string;
}

export interface ChatProposal {
  status: "proposal_only" | string;
  summary: string;
  targets: ChatProposalTarget[];
  suggested_commands: string[];
  patch_summary?: string | null;
  diff_preview?: string | null;
  prerequisites: string[];
  risks: string[];
  not_applied: boolean;
}

export interface DesktopActionRequest {
  id: string;
  action: string;
  title: string;
  target_label?: string | null;
  target_app?: string | null;
  target_window?: string | null;
  risk_note?: string | null;
  arguments?: Record<string, unknown> | null;
  requires_confirmation: boolean;
}

export interface DesktopActionStep {
  id: string;
  action: string;
  title: string;
  status: "planned" | "approved" | "blocked" | "executed" | string;
  target_label?: string | null;
  summary?: string | null;
}

export interface DesktopActionApproval {
  status: "not_required" | "approval_required" | "approved" | "denied" | string;
  summary: string;
  requested_actions: DesktopActionRequest[];
  next_step_label?: string | null;
  reason?: string | null;
}

export interface DesktopExecutionArtifact {
  kind: string;
  name?: string | null;
  mime_type?: string | null;
  data_url?: string | null;
  text?: string | null;
  metadata?: Record<string, unknown> | null;
}

export interface ExecutionEvidenceRef {
  runtime_execution_id?: ID | null;
  document_id?: ID | null;
  document_name?: string | null;
  chunk_id?: ID | null;
}

export interface ExecutionAnnotation {
  id: string;
  kind: string;
  title: string;
  summary: string;
  status: "ready" | "queued" | "running" | "succeeded" | "failed" | string;
  timestamp?: string | null;
  source_layer: "chat" | "runtime" | "knowledge" | "model" | string;
  runtime_execution_id?: ID | null;
  runtime_session_id?: ID | null;
  evidence_refs?: ExecutionEvidenceRef[] | null;
  payload_preview?: Record<string, unknown> | string | null;
  raw_payload?: Record<string, unknown> | null;
  target_label?: string | null;
  duration_ms?: number | null;
}

export interface ExecutionTraceSummary {
  headline: string;
  summary: string;
  status: "queued" | "running" | "succeeded" | "failed" | string;
  timeline_count: number;
  has_artifacts: boolean;
}

export interface ChatExecutionTrace {
  mode?: ChatMode | null;
  mode_summary?: ChatModeSummary | null;
  scenario_tag: ScenarioTag;
  scenario_label: string;
  router_reason: string;
  intent_plan: string[];
  grounding_summary?: ChatGroundingSummary | null;
  grounded_targets?: GroundedTarget[];
  primary_grounded_target?: GroundedTarget | null;
  desktop_grounding_summary?: ChatGroundingSummary | null;
  reflection_summary?: ChatReflectionSummary | null;
  reflection_reason?: string | null;
  reflection_next_probe?: string | null;
  workflow_stage?: "grounding" | "approval" | "execution" | "reflection" | "complete" | string;
  operator_plan_id?: ID | null;
  operator_plan_status?: string | null;
  operator_stage?: string | null;
  active_step_id?: string | null;
  pending_approval_count?: number | null;
  latest_artifact_summaries?: Array<Record<string, unknown>>;
  step_verification_summary?: string | null;
  primary_failure_target?: string | null;
  failure_summary?: string | null;
  failure_classification?: string | null;
  stderr_highlights?: string[];
  grounded_next_step_reasoning?: string[];
  steps: SkillInvocationSummary[];
  evidence: ChatEvidenceItem[];
  evidence_items?: ChatEvidenceItem[];
  execution_bundle_id?: ID | null;
  child_execution_ids?: ID[];
  planned_actions?: ExecutionAnnotation[];
  actual_events?: ExecutionAnnotation[];
  timeline?: ExecutionAnnotation[];
  trace_summary?: ExecutionTraceSummary | null;
  desktop_action_approval?: DesktopActionApproval | null;
  requested_desktop_actions?: DesktopActionRequest[];
  desktop_action_steps?: DesktopActionStep[];
  safety_summary?: Record<string, unknown> | null;
  machine_summary?: EnvironmentSummary | Record<string, unknown> | null;
  workspace_readiness?: WorkspaceEnvironmentStatus | Record<string, unknown> | null;
  install_guidance?: string[];
  recommended_next_actions?: ChatRecommendedAction[];
  runtime_execution_ids: ID[];
  artifact_summaries?: Array<Record<string, unknown>>;
  desktop_artifacts?: DesktopExecutionArtifact[] | null;
  proposal?: ChatProposal | null;
}

export interface Provider {
  id: ID;
  slug: string;
  name: string;
  type: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface Model {
  id: ID;
  provider_id: ID;
  slug: string;
  name: string;
  kind: "chat" | "embedding" | string;
  context_window: number;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export type ProviderConnectionStatus =
  | "active"
  | "pending"
  | "requires_config"
  | "manual_entry_required"
  | "error"
  | "disabled"
  | string;

export interface MaskedSecretMeta {
  masked_value?: string | null;
  configured: boolean;
}

export interface DiscoveredModel {
  name: string;
  kind: "chat" | "embedding" | string;
  source: "discovered" | "manual" | string;
  metadata?: Record<string, unknown> | null;
}

export interface ProviderConnection {
  id: ID;
  user_id: ID;
  provider_id?: ID | null;
  provider_type: string;
  name: string;
  base_url: string;
  model_discovery_mode: string;
  status: ProviderConnectionStatus;
  is_enabled: boolean;
  default_model_name?: string | null;
  default_embedding_model_name?: string | null;
  secret: MaskedSecretMeta;
  models: DiscoveredModel[];
  last_checked_at?: string | null;
  last_error?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProviderConnectionTestResult {
  ok: boolean;
  status: ProviderConnectionStatus;
  message: string;
  last_checked_at?: string | null;
  discovered_model_count: number;
}

export interface KnowledgeDocument {
  id: ID;
  workspace_id: ID;
  file_name: string;
  title?: string | null;
  file_type: string;
  status: "processing" | "ready" | "failed" | string;
  source_type: "user_upload" | "builtin_pack" | "git_repo" | "web_capture" | string;
  source_ref?: string | null;
  knowledge_pack_slug?: string | null;
  storage_path: string;
  content_length: number;
  chunk_count: number;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
}

export interface KnowledgePack {
  id: ID;
  workspace_id: ID;
  slug: string;
  name: string;
  version: string;
  description: string;
  source_type: string;
  source_ref?: string | null;
  manifest_path?: string | null;
  is_builtin: boolean;
  status: string;
  last_synced_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeSource {
  id: ID;
  kind: string;
  title: string;
  source_ref?: string | null;
  pack_slug?: string | null;
}

export interface SkillDefinition extends ConversationModelBinding {
  id: ID;
  workspace_id: ID;
  name: string;
  slug: string;
  description: string;
  prompt_template: string;
  input_schema?: Record<string, unknown> | null;
  tool_capabilities?: string[] | Record<string, unknown> | null;
  knowledge_scope?: string[] | Record<string, unknown> | null;
  required_capabilities?: string[] | null;
  recommended_capabilities?: string[] | null;
  workspace_requirements?: string[] | null;
  enabled: boolean;
  skill_mode: SkillExecutionMode;
  required_runtime_type?: string | null;
  session_mode: "new" | "reuse" | string;
  command_template?: string | null;
  working_directory?: string | null;
  agent_role_slug?: string | null;
  pack_slug?: string | null;
  pack_version?: string | null;
  is_builtin: boolean;
  provider_id?: ID | null;
  model_id?: ID | null;
  provider_connection_id?: ID | null;
  provider_connection_name?: string | null;
  model_name?: string | null;
  allow_model_override: boolean;
  use_knowledge: boolean;
  chat_callable: boolean;
  chat_modes?: ChatMode[];
  safety_level: string;
  scenario_tags: string[];
  is_read_only: boolean;
  supports_proposal_output?: boolean;
  compatibility?: SkillCompatibilityStatus | null;
  created_at: string;
  updated_at: string;
}

export interface SkillPack {
  id: ID;
  workspace_id: ID;
  slug: string;
  name: string;
  version: string;
  description: string;
  source_type: string;
  source_ref?: string | null;
  manifest_path?: string | null;
  is_builtin: boolean;
  status: string;
  tool_capabilities_json?: string[] | Record<string, unknown> | null;
  last_synced_at?: string | null;
  created_at: string;
  updated_at: string;
}

export type SkillExecutionMode = "prompt" | "cli" | "browser" | string;

export interface RuntimeHost {
  id: ID;
  name: string;
  runtime_type: "cli" | "browser" | "desktop" | string;
  endpoint_url: string;
  capabilities_json?: Record<string, unknown> | null;
  scope_type: string;
  scope_ref_id: ID;
  status: "online" | "online_ready" | "online_degraded" | "offline" | "degraded" | string;
  doctor_status?: "ready" | "degraded" | "missing" | string | null;
  last_error?: string | null;
  last_heartbeat_at?: string | null;
  last_capability_check_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface RuntimeSessionContext {
  cwd?: string | null;
  shell?: string | null;
  env_whitelist?: string[] | null;
  repo_root?: string | null;
  last_command_at?: string | null;
}

export interface RuntimeSession {
  id: ID;
  session_type: "cli" | "browser" | "desktop" | string;
  runtime_id: ID;
  runtime_name?: string | null;
  workspace_id: ID;
  created_by_id: ID;
  status: "idle" | "busy" | "closed" | "error" | string;
  reusable: boolean;
  context_json?: RuntimeSessionContext | null;
  last_activity_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface RuntimeSessionEvent {
  id: ID;
  runtime_session_id: ID;
  event_type: string;
  message?: string | null;
  payload_json?: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface CliExecutionResult {
  runtime_id: ID;
  runtime_session_id: ID;
  command: string;
  cwd?: string | null;
  stdout: string;
  stderr: string;
  exit_code: number;
  duration_ms?: number | null;
  artifacts_json?: Record<string, unknown> | Array<Record<string, unknown>> | null;
}

export interface BrowserExecutionArtifact {
  kind: string;
  name?: string;
  mime_type?: string;
  data_url?: string;
  tabs?: Array<Record<string, unknown>>;
}

export interface BrowserExecutionResult {
  runtime_id: ID;
  runtime_session_id: ID;
  actions: Array<Record<string, unknown>>;
  current_url?: string | null;
  title?: string | null;
  extracted_text: string;
  duration_ms?: number | null;
  artifacts_json?: BrowserExecutionArtifact[] | Record<string, unknown> | null;
}

export interface AgentRole {
  slug: string;
  name: string;
  system_prompt: string;
  allowed_skill_modes?: SkillExecutionMode[] | null;
  allowed_runtime_types?: string[] | null;
  default_model_binding?: Record<string, unknown> | null;
  default_skill_pack_slugs?: string[] | null;
  default_knowledge_pack_slugs?: string[] | null;
  created_at: string;
  updated_at: string;
}

export interface RuntimeExecution {
  id: ID;
  workspace_id: ID;
  conversation_id?: ID | null;
  skill_id?: ID | null;
  runtime_id?: ID | null;
  runtime_name?: string | null;
  runtime_session_id?: ID | null;
  provider_id?: ID | null;
  model_id?: ID | null;
  provider_connection_id?: ID | null;
  provider_connection_name?: string | null;
  user_id: ID;
  source: "chat" | "skill" | string;
  execution_kind: "chat" | "skill_prompt" | "skill_cli" | "skill_browser" | "desktop_inspect" | "desktop_operate" | string;
  status: "queued" | "running" | "succeeded" | "failed" | string;
  prompt_preview?: string | null;
  command_preview?: string | null;
  response_preview?: string | null;
  error_message?: string | null;
  resolved_model_name?: string | null;
  resolved_base_url?: string | null;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  duration_ms?: number | null;
  artifacts_json?: Record<string, unknown> | Array<Record<string, unknown>> | null;
  details_json?: Record<string, unknown> | null;
  trace_summary?: ExecutionTraceSummary | null;
  execution_bundle_id?: ID | null;
  parent_execution_id?: ID | null;
  child_execution_ids?: ID[];
  operator_plan_id?: ID | null;
  operator_stage?: string | null;
  mode?: ChatMode | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface RuntimeExecutionTimeline {
  execution_id: ID;
  trace_summary: ExecutionTraceSummary;
  timeline: ExecutionAnnotation[];
}

export interface DesktopApprovalReviewResult {
  execution: RuntimeExecution;
  child_execution?: RuntimeExecution | null;
  execution_trace?: ChatExecutionTrace | null;
}

export interface OperatorPlanTemplate {
  slug: string;
  title: string;
  description: string;
  mode: ChatMode;
  prompt: string;
  tags: string[];
}

export interface OperatorPlan {
  id: ID;
  workspace_id: ID;
  conversation_id?: ID | null;
  parent_execution_id?: ID | null;
  created_by_id: ID;
  title: string;
  mode: ChatMode | string;
  status: string;
  operator_stage: string;
  requested_prompt: string;
  template_slug?: string | null;
  primary_target_label?: string | null;
  primary_target_value?: string | null;
  pending_approval_count: number;
  summary_json?: Record<string, unknown> | null;
  steps_json?: Array<Record<string, unknown>> | null;
  approvals_json?: Array<Record<string, unknown>> | null;
  artifacts_json?: Array<Record<string, unknown>> | null;
  child_execution_ids_json?: ID[] | null;
  trace_json?: ChatExecutionTrace | Record<string, unknown> | null;
  last_failure_summary?: string | null;
  created_at: string;
  updated_at: string;
}

export interface OperatorPlanListResponse {
  items: OperatorPlan[];
  templates: OperatorPlanTemplate[];
}

export interface ModelUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

export interface LoginResponse {
  access_token: string;
  token_type: "bearer";
  user: User;
}

export interface MessageCreateInput {
  conversation_id: ID;
  content: string;
  use_knowledge?: boolean;
  mode?: ChatMode;
}

export interface SkillRunInput {
  workspace_id: ID;
  conversation_id?: ID;
  variables?: Record<string, string>;
  use_knowledge?: boolean;
}

export interface SkillRunResult {
  conversation: Conversation;
  execution: RuntimeExecution;
  user_message: Message;
  assistant_message: Message;
}

export interface StreamEvent {
  event: "message_start" | "delta" | "finish" | "error" | "done";
  data: Record<string, unknown>;
}
