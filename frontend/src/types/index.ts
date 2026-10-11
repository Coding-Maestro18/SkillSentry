// Mirrors backend/app/schemas.py — keep in sync.

export type Severity = "informational" | "low" | "medium" | "high";
export type Decision = "ALLOW" | "BLOCK" | "FLAG";
export type ScanState =
  | "queued" | "validating" | "parsing" | "analyzing" | "generating_tests"
  | "simulating" | "reporting" | "completed" | "failed";

export interface ApiErrorBody {
  error: { code: string; message: string; details: Record<string, unknown>; request_id: string };
}

export interface FileEntry {
  file_id: string;
  relative_path: string;
  size_bytes: number;
  scanned: boolean;
  skip_reason: string | null;
  role: string;
  encoding: string | null;
  line_ending: string | null;
  sha256: string;
  warnings: string[];
}

export interface FileAnnotation {
  annotation_id: string;
  file_id: string;
  relative_path: string;
  line: number;
  column: number;
  end_line: number;
  end_column: number;
  start_offset: number;
  end_offset: number;
  annotation_type: string;
  code_point: string | null;
  unicode_name: string | null;
  escaped_excerpt: string;
  detector_id: string;
  severity: Severity;
  notes: string;
  skeleton: string | null;
}

export interface Finding {
  finding_id: string;
  rule_id: string;
  category: string;
  severity: Severity;
  title: string;
  source_file: string;
  line_start: number;
  column_start: number;
  line_end: number;
  column_end: number;
  evidence: string;
  observed_fact: string;
  interpretation: string;
  remediation: string;
  detector: string;
  evidence_type: string;
  model_interpretation: string | null;
  model_confidence: string | null;
  status: string;
  related_test_ids: string[];
  annotation_ids: string[];
  decoded_payload: string | null;
  decoder: string | null;
  extra: Record<string, unknown>;
}

export interface ToolCall { tool: string; args: Record<string, string> }

export interface TestCase {
  test_id: string;
  suite_version: string;
  name: string;
  purpose: string;
  kind: "benign_control" | "adversarial";
  origin: "fixed_suite" | "model_proposed";
  source_finding_ids: string[];
  setup_fixture: string;
  trigger: { type: string; rule_ids: string[]; min_severity: Severity; excerpt: string | null };
  tool_sequence: ToolCall[];
  expected_policy_decisions: Decision[];
  expected_outcome: string;
  validation_status: "valid" | "rejected";
  validation_notes: string[];
}

export interface TraceEvent {
  event_id: string;
  test_id: string;
  sequence_number: number;
  tool_name: string;
  sanitized_arguments: Record<string, string>;
  policy_decision: Decision;
  decision_reason: string;
  mock_result_summary: string;
  timestamp: string;
}

export interface TestResult {
  test_id: string;
  status: "pass" | "fail" | "needs_review" | "skipped";
  triggered: boolean;
  summary: string;
  events: TraceEvent[];
  ran_at: string;
}

export interface ModelInfo {
  provider: string;
  name: string;
  revision: string;
  license: string;
  inference_mode: string;
  adapter_version: string;
  status: string;
  status_detail: string;
  schema_valid_responses: number;
  total_responses: number;
  latency_ms: number | null;
}

export interface Passport {
  skill_name: string | null;
  description: string | null;
  files_discovered: string[];
  references: string[];
  declared_capabilities: string[];
  inferred_capabilities_model: string[];
  inferred_capabilities_rules: string[];
  observed_simulated_actions: string[];
  sensitive_items_mentioned: string[];
  destinations_mentioned: string[];
  unresolved_concerns: string[];
  unscanned_files: string[];
}

export interface Summary {
  files_scanned: number;
  files_skipped: number;
  findings_by_severity: Record<string, number>;
  findings_by_category: Record<string, number>;
  hidden_content_counts: Record<string, number>;
  tests_total: number;
  tests_by_status: Record<string, number>;
  headline: string;
}

export interface ScanReport {
  scan_id: string;
  parent_scan_id: string | null;
  created_at: string;
  input_kind: string;
  status: ScanState;
  stage_detail: string;
  error: { code: string; message: string } | null;
  skill_name: string | null;
  skill_description: string | null;
  files: FileEntry[];
  findings: Finding[];
  annotations: FileAnnotation[];
  tests: TestCase[];
  rejected_tests: TestCase[];
  results: TestResult[];
  passport: Passport | null;
  summary: Summary | null;
  model: ModelInfo | null;
  analyzer_version: string;
  ruleset_version: string;
  unicode_version: string;
  confusables_version: string;
  suite_version: string;
  timings_ms: Record<string, number>;
  limitations: string[];
}

export interface ScanStatus {
  scan_id: string;
  status: ScanState;
  stage_detail: string;
  error: { code: string; message: string } | null;
  parent_scan_id: string | null;
}

export interface Segment { text: string; kind: string; label: string }

export interface FileView {
  file_id: string;
  relative_path: string;
  raw: string;
  reveal: Segment[][];
  preview: string;
  annotations: FileAnnotation[];
  preview_note: string;
}

export interface FixSuggestion {
  origin: "model" | "deterministic";
  model_status: string;
  finding_ids: string[];
  rationale: string[];
  revised_files: Record<string, string>;
  diffs: Record<string, string>;
}

export interface Comparison {
  original_scan_id: string;
  revised_scan_id: string;
  suite_version: string;
  same_suite: boolean;
  tests: { test_id: string; name: string; before: string | null; after: string | null; change: string; after_summary: string }[];
  findings_before: Record<string, number>;
  findings_after: Record<string, number>;
  resolved_findings: string[];
  remaining_findings: string[];
  new_findings: string[];
  verdict: string;
}

export interface Health {
  api: string;
  analyzer_version: string;
  suite_version: string;
  detectors: Record<string, string>;
  model: ModelInfo;
  limits: Record<string, number>;
}
