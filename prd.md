# SkillSentry — Product Requirements Document (PRD)

**Document status:** Draft for hackathon implementation  
**Version:** 1.0  
**Target build:** 10-hour hackathon MVP, four-person team  
**Product type:** Open-source AI security analysis and testing harness for Agent Skills  
**Proposed code license:** Apache-2.0 (confirm team and event requirements before publishing)  
**Primary users:** Agent Skill authors, developers reviewing third-party skills, and teams maintaining internal skill libraries

---

## 1. Executive summary

SkillSentry is an open-source security testing workbench for AI Agent Skills. It helps developers inspect skill packages, uncover suspicious or concealed instructions, generate adversarial test cases, simulate selected tool actions in a controlled environment, review evidence, and compare the result after a proposed fix.

The project combines four complementary techniques:

1. **Deterministic static analysis** to find recognizable risky patterns, malformed or unexpected content, and capability mismatches.
2. **An open-weight language model** to interpret instructions in context, identify semantic conflicts, propose relevant adversarial scenarios, and draft mitigations.
3. **A controlled mock-tool harness** to simulate actions such as reading a fake secret or making a mock outbound request without touching the host filesystem, executing uploaded scripts, or accessing the real network.
4. **Evidence-first reporting** that links each finding to source files, line/column positions, exact text or Unicode code points, test results, and caveats.

A signature feature is the **Invisible Content & Unicode Deception Scanner**. It checks `SKILL.md` and supported text files under `references/` for zero-width/default-ignorable characters, bidi controls, homoglyph/confusable characters, HTML comments, hidden HTML presentation patterns, and anomalous whitespace that may encode or conceal text. It reveals the relevant source in a forensic view and explains what was detected. These indicators are not automatically proof of malicious intent: SkillSentry must distinguish a deterministic observation from an inferred risk and account for legitimate multilingual text and formatting.

### Product promise

> **SkillSentry helps developers see what a skill contains, test how selected instructions could behave, and verify whether a change improves the tested result.**

SkillSentry does **not** certify a skill as universally safe. A scan only evaluates the files and scenarios it can inspect; an agent runtime may parse or load those files differently.

---

## 2. Problem statement

Agent Skills package instructions and optional supporting resources in a reusable directory. The human-readable description is not enough to establish whether all instructions are appropriate, whether supporting files contain conflicting directions, or whether text is visually concealed from a casual reviewer.

Manual review can miss:

- Instructions that conflict with the skill's declared purpose.
- Prompt-injection-like directions placed in reference files rather than the primary `SKILL.md`.
- Text inside Markdown HTML comments that does not appear in a typical rendered Markdown view.
- Unicode format characters or zero-width characters that are difficult to see in an editor.
- Visually confusable homoglyphs that make a token look different from its underlying characters.
- Suspicious runs of tabs, spaces, or unusual Unicode whitespace that may conceal or encode text.
- Instructions that try to expand the skill's authority, reveal secrets, or send data to an unexpected destination.
- Fixes that appear sensible but have not been tested against the same scenario that exposed the concern.

At the same time, hidden-character detection can generate false positives. Zero-width joiners, bidirectional controls, non-breaking spaces, mixed-script text, and Markdown trailing spaces can be legitimate. SkillSentry therefore needs to show **why** a finding was produced, where it appears, and how confident the system is, rather than treating every unusual character as malicious.

---

## 3. Goals and non-goals

### 3.1 Goals

1. Let a user inspect one Agent Skill package through a simple web interface or a documented local CLI/API.
2. Parse `SKILL.md` and supported text files in `references/` without executing their contents.
3. Surface evidence-linked findings from static rules and open-weight model analysis.
4. Detect hidden or visually deceptive content, including the special cases described in Section 8.
5. Generate a small set of adversarial and benign test scenarios appropriate to a skill's instructions.
6. Run scenarios only through an allowlisted mock-tool harness and record an auditable trace.
7. Let a user inspect a proposed fix, apply it to a copy or separately uploaded revision, and rerun the same suite.
8. Produce a reproducible report with source references, test outcomes, model information, coverage, and limitations.
9. Be useful offline or with a local model when practical, while allowing a configurable inference adapter.
10. Publish the project in a public GitHub repository under an open-source license, document the model and its license, and keep the implementation easy to reproduce.

### 3.2 Non-goals for the 10-hour MVP

- Proving that a skill is safe or detecting every prompt injection.
- Running arbitrary uploaded scripts, shell commands, or binaries.
- Testing a skill against a real agent with real credentials or unrestricted tools.
- Making real network requests requested by uploaded content or model output.
- Automatically installing skills into a user's agent environment.
- Automatically applying fixes without user review.
- Full GitHub organization scanning, continuous integration, team accounts, access control, or large-scale skill registry support.
- Complete static analysis of every programming language or binary file.
- Guaranteeing that all AI agent runtimes interpret Markdown, Unicode, HTML, or reference files in the same way.
- A universal numeric safety score that implies formal assurance.

---

## 4. Target users and primary use cases

### 4.1 Primary persona: Skill author

**Need:** Check whether a skill being published or shared contains suspicious instructions or unnecessary capability requests.  
**Success:** The author sees actionable, source-linked findings, makes a targeted edit, and reruns the same tests.

### 4.2 Primary persona: Developer reviewing a third-party skill

**Need:** Inspect a downloaded skill before deciding whether to use it.  
**Success:** The developer understands its declared purpose, suspicious content, test coverage, observed simulated actions, and unresolved concerns without executing its code.

### 4.3 Secondary persona: Platform or security reviewer

**Need:** Triage several findings consistently and retain a compact audit artifact.  
**Success:** The reviewer can inspect evidence, distinguish confirmed file properties from model inferences, export the report, and explain the decision.

### 4.4 Core user stories

- As a user, I can upload a skill ZIP and see which files will be inspected before analysis starts.
- As a user, I can inspect the parsed `SKILL.md` metadata and the discovered references.
- As a user, I can find suspicious instructions with a source file, line, and evidence excerpt.
- As a user, I can reveal zero-width characters, homoglyphs, HTML comments, and suspicious whitespace that are difficult to notice in a rendered view.
- As a user, I can compare rendered, raw, and escaped/annotated source views.
- As a user, I can tell whether a finding is based on a deterministic rule, a model interpretation, or simulated runtime behavior.
- As a user, I can run controlled test cases and inspect the actions the harness allowed, blocked, or flagged.
- As a user, I can review a suggested fix and rerun the exact same test cases against a revised copy.
- As a user, I can export a report that includes model provenance and test limitations.

---

## 5. Product principles

1. **Evidence over vibes:** Every nontrivial finding should cite the observed text, source location, rule or test, and reason.
2. **Observation versus inference:** A detected code point is a fact; “this is malicious” is a judgment. Label those separately.
3. **Model is an analyst, never the authority:** The model may interpret content and suggest tests, but deterministic validation and the mock harness constrain what can happen.
4. **No real execution in the MVP:** All tool calls are simulated. Never run skill-provided scripts or generated shell commands.
5. **Human review for ambiguous cases:** Preserve unknown and needs-review states. Do not equate missing metadata with a confirmed problem.
6. **Reproducibility:** Keep fixture inputs, test IDs, model details, analyzer version, and test outputs with each report.
7. **Local-first:** Core parsing, static scanning, Unicode checks, mock tests, and routing of findings should work locally. AI inference may be local or configured externally.
8. **Safe display of hostile text:** Treat uploaded text as untrusted data; escape it in the UI and never render it as active HTML.

---

## 6. Scope and supported inputs

### 6.1 Input formats (MVP)

- Upload one ZIP containing one skill directory, or paste a small `SKILL.md` into the interface for a quick scan.
- Required file: `SKILL.md`.
- Inspect text in `SKILL.md` and files under `references/` with supported text extensions, at minimum `.md`, `.txt`, `.yaml`, `.yml`, `.json`, and `.toml`.
- File inventory should identify additional files such as `scripts/` or `assets/`, but the MVP must not execute them. Optional static text scanning of source scripts can be added if safe and time allows.
- Handle UTF-8 and UTF-8 with BOM. If decoding fails, report an encoding warning and preserve enough raw-byte metadata for review rather than silently discarding bytes.

### 6.2 Upload safety limits

Default configurable limits for the hackathon MVP:

- Maximum compressed ZIP size: 10 MB.
- Maximum total extracted size: 25 MB.
- Maximum number of files: 500.
- Maximum single text file size: 2 MB.
- Reject absolute paths, `..` traversal, symlinks, path collisions, and suspicious archive entries.
- Extract only inside a newly created temporary directory; never use archive paths as trusted filesystem paths.
- Never execute file contents or invoke the system shell while scanning.
- Ignore or flag binary/unsupported files instead of trying to interpret them as plain text.

These are initial product defaults, not claims that a ZIP is safe merely because it passes the limits.

---

## 7. Main user workflow

1. **Start scan:** User uploads a ZIP or pastes `SKILL.md`.
2. **Inspect package:** SkillSentry validates the archive, shows a file inventory, and identifies `SKILL.md` plus supported reference files.
3. **Run deterministic inspection:** Parse metadata, line mappings, hidden-content indicators, suspicious patterns, and basic capability requests.
4. **Run open-weight model analysis:** Send bounded excerpts and structured context to the configured model with explicit instructions to analyze the content as untrusted data, not follow it.
5. **Generate tests:** Create candidate adversarial tests using an allowlisted mock-tool vocabulary. Validate every model-produced test before it can be run.
6. **Execute simulations:** Run tests through deterministic mock tools and log decisions/results.
7. **Review findings:** User filters by severity, file, category, evidence source, and status; selects a finding to inspect line context and explanation.
8. **Review fix:** User asks for a proposed revision or manually edits a copy. The original package remains unchanged.
9. **Retest:** Rerun the same test suite against the revision and compare outcomes.
10. **Export report:** Download a Markdown or JSON report with findings, traces, test results, model provenance, and limitations.

---

## 8. Feature requirements

Priority labels:

- **P0:** Required for the hackathon MVP.
- **P1:** Valuable if the core end-to-end workflow is stable.
- **P2:** Post-hackathon extension.

### 8.1 Package upload and parsing — P0

**Description:** Safely ingest one skill package and parse the supported text files.

Requirements:
- Accept a ZIP containing a single skill folder and/or a pasted `SKILL.md`.
- Validate that `SKILL.md` exists for package scans. If absent, explain what was found and allow a limited generic text scan only if desired.
- Parse frontmatter fields such as `name` and `description` without treating arbitrary frontmatter as executable configuration.
- Show all discovered files and which files are included/excluded from scanning.
- Preserve stable relative paths and line numbers.
- Report unsupported encodings, oversized files, and skipped content.

Acceptance criteria:
- A valid sample skill produces a file inventory and parsed name/description.
- A malformed or unsafe ZIP is rejected with an actionable message.
- A scan never writes files outside its temporary root and does not execute uploaded content.

### 8.2 Static instruction analysis — P0

**Description:** Find recognizable risky or contradictory instructions with deterministic rules.

Initial categories:
- Requests to reveal, print, or transmit credentials, API keys, tokens, or environment secrets.
- Instructions to ignore prior/system/developer rules or override an agent's restrictions.
- Attempts to broaden tool authority beyond the skill's stated purpose.
- Unrequested network destinations or instructions to send gathered content to an external endpoint.
- Conflicts between the stated purpose/description and instructions in the body or references.
- Suspicious encoded payloads or references to decoding hidden instructions.
- Instructions that appear to direct the downstream agent rather than provide domain information.

Requirements:
- Static rules must produce stable IDs and explainable reasons.
- Rule matches should include source file, line, column where available, and a short escaped evidence excerpt.
- Rules are triage signals, not definitive proof of maliciousness.
- Avoid broad phrase matching that labels every legitimate mention of “secret”, “ignore”, “token”, or “system” as high severity. Use context and exact evidence.

Acceptance criteria:
- At least five deterministic rules operate on fixture files.
- A benign control fixture does not trigger every high-severity rule.
- Each rule finding has a title, category, severity, evidence, location, rationale, and remediation hint.

### 8.3 Invisible Content & Unicode Deception Scanner — P0, signature feature

**User value:** Reveal content that may be present in the source but difficult to notice in a normal reading or rendered Markdown view.

**Files in scope:** `SKILL.md` and supported text files under `references/`. The same scanner may be reused for other supported text files if included in the package scan.

#### 8.3.1 Zero-width and default-ignorable characters

Requirements:
- Scan for Unicode format/control characters and selected default-ignorable characters that can affect text visibility or interpretation.
- Explicitly identify common examples, including:
  - `U+200B` ZERO WIDTH SPACE
  - `U+200C` ZERO WIDTH NON-JOINER
  - `U+200D` ZERO WIDTH JOINER
  - `U+2060` WORD JOINER
  - `U+FEFF` ZERO WIDTH NO-BREAK SPACE / BOM usage
  - `U+00AD` SOFT HYPHEN
  - Bidirectional controls, including `U+202A–U+202E` and `U+2066–U+2069`
- Use Unicode character properties/data rather than relying only on a tiny hard-coded list. Pin and document the Unicode data/version used by the implementation.
- Provide an escaped view showing code point, Unicode name where available, line, column, count, and a short surrounding excerpt.
- Distinguish common/possibly legitimate cases from high-risk patterns. For example, ZWJ/ZWNJ can be meaningful in emoji and some writing systems; do not label every occurrence malicious by default.
- Flag bidi controls more strongly when they change the apparent ordering of instructions or occur near sensitive-looking tokens.

Acceptance criteria:
- The scanner detects configured invisible/control-character fixtures and identifies exact code points and locations.
- The UI can display the source without silently dropping the characters.
- An output warning explains that unusual characters may be legitimate and should be reviewed in context.

#### 8.3.2 Homoglyph and confusable-character detection

Requirements:
- Use a versioned Unicode confusables data source or a well-maintained implementation aligned with Unicode Technical Standard #39 (UTS #39) for relevant detection.
- Detect suspicious mixed-script tokens and confusable forms near security-sensitive words, identifiers, tool names, and domains. Example: a Latin-looking word that includes Cyrillic letters resembling Latin characters.
- Show the original token and a safe, explicitly labeled normalized/confusable comparison for review.
- Do not modify the original uploaded content. Any normalized “skeleton” is for comparison only, not display as authoritative text and not used as the stored original.
- Avoid flagging all multilingual content; prioritize context-sensitive tokens and mixed-script cases that resemble security-sensitive terms.
- Include the detection method/data version in the report.

Acceptance criteria:
- A fixture containing a mixed-script confusable in a sensitive token is detected and the substituted code point is identified.
- Legitimate non-Latin text is not automatically classified as malicious solely because it uses another script.
- Reports describe these as possible confusables/spoofing indicators rather than proven maliciousness.

#### 8.3.3 Markdown comments and hidden HTML text

Requirements:
- Detect non-empty HTML comments using `<!-- ... -->` in `SKILL.md` and reference files, including multiline comments.
- Flag the fact that comment text is not normally visible in rendered Markdown, then assess the comment contents with deterministic rules and optional model assistance.
- Increase severity when a comment contains instruction-like content such as requests to ignore safeguards, reveal data, change model behavior, or contact an unapproved destination.
- Detect common hidden HTML styling patterns in raw Markdown/HTML, such as `display:none`, `visibility:hidden`, `opacity:0`, `font-size:0`, and likely same-color foreground/background declarations when present in inline styles.
- The MVP may use conservative pattern matching rather than a full HTML/CSS rendering engine. Clearly describe this limitation in results.
- Show hidden content only as escaped text in a forensic panel; do not render it as active HTML.
- If a file has HTML comments with ordinary editorial notes, classify as informational/low severity unless context indicates elevated risk.

Acceptance criteria:
- A fixture with a suspicious instruction inside an HTML comment is flagged with source location and visible-for-review content.
- An innocuous comment is displayed as hidden content without automatically being branded malicious.
- The scanner safely handles multiline and unterminated comments and reports the latter as a parse/format issue.

#### 8.3.4 Suspicious whitespace and whitespace-encoded content

Requirements:
- Identify unusual trailing whitespace patterns, long runs of spaces/tabs, alternating trailing spaces and tabs across consecutive lines, repeated whitespace-only patterns, and unusual Unicode whitespace characters.
- Detect common non-ASCII whitespace characters such as non-breaking space and Unicode space separators; show their exact code points in the forensic view.
- Provide a heuristic for possible space/tab bit encoding. If a supported simple pattern is detected, optionally decode it in a separate, clearly labeled field; never overwrite or normalize the source.
- Only claim that a payload was decoded when a documented deterministic decoder actually produced it. Otherwise report “suspicious whitespace pattern; payload not decoded.”
- Account for legitimate Markdown use of trailing spaces (for example, hard line breaks) to reduce false positives.
- Keep detection thresholds configurable and include the reason a pattern met the threshold.

Initial heuristic proposal:
- Report a low-priority whitespace anomaly when unusual trailing-space/tab runs appear repeatedly across multiple adjacent lines.
- Raise priority when the pattern shows a consistent binary-like space/tab sequence and the supported decoder yields a plausible printable payload.
- Do not treat long indentation or a single trailing space as a high-severity issue.

Acceptance criteria:
- Test fixtures for trailing whitespace, alternating space/tab patterns, Unicode spaces, and a documented simple encoded sample are covered.
- The finding describes exactly which lines and whitespace pattern triggered it.
- The tool does not claim to detect every possible whitespace steganography technique.

#### 8.3.5 Forensic content viewer

Requirements:
- Provide three views for supported files:
  1. **Readable/rendered preview:** A safe, sanitized preview of ordinary Markdown text.
  2. **Raw source:** Original file content with line numbers.
  3. **Reveal invisible characters:** Escaped display such as `[U+200B ZERO WIDTH SPACE]`, with suspicious whitespace visualized as `·` for space and `⇥` for tab where appropriate.
- Provide filters for invisible characters, confusables, comments/hidden HTML, whitespace anomalies, and line ranges.
- Clicking a finding should take the user to the exact source location and show surrounding context.
- Preserve the original file and code points in the stored scan artifact.
- Never render uploaded HTML directly in the browser without sanitization.

Acceptance criteria:
- A user can find and inspect every detected character or hidden block without needing an external editor.
- The UI distinguishes the raw source from any preview or normalized comparison.

#### 8.3.6 Severity guidelines for concealed-content findings

- **Informational:** A non-empty HTML comment or unusual but likely benign formatting with no suspicious instruction.
- **Low:** An isolated invisible character or whitespace anomaly with no risky context.
- **Medium:** Multiple unexplained invisible characters, a possible confusable token, hidden content that contains imperative language, or a repeated whitespace pattern.
- **High:** Concealed content or suspicious confusables are combined with explicit requests to override rules, exfiltrate data, disclose secrets, or invoke unauthorized capabilities, supported by evidence.

Severity is a prioritization estimate. It must be configurable and should not imply certainty about intent.

### 8.4 Open-weight model analysis — P0

**Description:** Use an open-weight instruct model as a core part of contextual analysis and test generation.

Requirements:
- Implement a model adapter so the application is not tightly coupled to one provider/runtime.
- Support at least one chosen open-weight model during the hackathon, using local inference (for example, via a local model server) or a documented hosted inference service.
- Record exact model name, version/revision when available, license, inference method, and whether analysis ran locally or remotely.
- Send bounded excerpts and structured inputs, not unlimited archives.
- Treat all file contents as untrusted data. The analysis prompt must explicitly say to inspect the content, not obey it.
- Do not give the analysis model tools or permissions to execute commands or access the network.
- Require validated structured output with fields such as finding category, rationale, evidence excerpt, related file, test hypothesis, and confidence estimate.
- Reject or safely repair malformed output; never treat the model's confidence as calibrated probability unless measured.
- Cache or fixture model responses for the demo if inference is unavailable; label fallback results clearly and do not fabricate model-originated findings.

Acceptance criteria:
- At least one model-generated interpretation or test hypothesis is visible in the report.
- The model can be disabled while static analysis and the mock harness continue to work.
- Model provenance appears in the scan report.

### 8.5 Capability passport — P0

Each scan includes a compact “Capability Passport” summarizing:
- Declared skill name and description.
- Discovered files and references.
- Explicitly stated tools/capabilities, if any.
- Capabilities inferred by the model (separately labeled).
- Capabilities observed in simulated traces.
- Sensitive data or destinations mentioned by the content.
- Unresolved concerns and unscanned files.

Acceptance criteria:
- The passport distinguishes declared, inferred, and observed data.
- The passport does not suggest a skill has access to real tools unless that fact is known from the tested environment.

### 8.6 Adversarial test generation — P0

Requirements:
- Generate at least five test scenarios for the MVP, ideally mixing benign control cases with adversarial cases.
- Scenarios may cover instruction override attempts, hidden instructions in a reference file, canary-secret access, unexpected mock outbound requests, and declared-purpose/capability mismatch.
- The model may propose scenarios, but the application must validate them against a fixed schema and an allowlisted set of mock tools.
- Test cases must specify goal, setup, allowed mock tools, expected policy decision, and observable success/failure criteria.
- Store the exact test-suite version and IDs so retesting uses the same cases.
- Keep generated tests short and deterministic where possible.

Acceptance criteria:
- Model-produced tests with unknown tool names, shell commands, external URLs, or invalid structures are rejected or converted to a safe, inert explanation.
- A user can inspect a test before or after running it.

### 8.7 Mock-tool harness and trace viewer — P0

Requirements:
- Provide only mock implementations in the MVP, such as `read_public_file`, `read_canary_file`, `write_mock_file`, and `send_mock_request`.
- Each tool returns a deterministic, fake result and records the request.
- Apply a deterministic policy gate that returns `ALLOW`, `BLOCK`, or `FLAG` with a reason.
- Never call real shell binaries, access the host environment, read real files outside fixture content, or make outbound network requests.
- Trace each simulated event with scenario ID, tool name, sanitized argument summary, policy decision, mock result summary, and timestamp.
- Explain that an attempted action in the mock harness is a simulation, not evidence that a real agent would definitely perform it.

Acceptance criteria:
- A canary-file access scenario creates a BLOCK trace and does not expose real system secrets.
- A mock outbound request is recorded but never sent.
- A reviewer can view the trace from the report UI.

### 8.8 Findings and report UI — P0

A finding should show:
- Title and category.
- Severity and status.
- Source file, line and column where available.
- Original evidence excerpt, safely escaped.
- What the deterministic detector observed.
- What the model inferred, if any, with a distinct label.
- Why it matters and what is uncertain.
- Suggested next action or mitigation.
- Related test cases and trace events.

The report summary should show:
- Number of files scanned and skipped.
- Count of findings by severity and category.
- Number of tests generated, run, passed, failed, or skipped.
- Hidden-content detector counts by type.
- Model details and whether inference was available.
- Analyzer version and test-suite version.
- Explicit limitations and unknowns.

Do not display a simple green “safe” badge based only on a low finding count. Prefer statuses such as “No high-priority findings detected in this scan” alongside test coverage and limitations.

### 8.9 Fix suggestion and regression comparison — P0

Requirements:
- Generate a proposed edit as a diff or replacement snippet, not as an automatic overwrite.
- Show the reason for the proposed fix and which finding/test it targets.
- Keep the original upload immutable; apply changes only to a copy or revised upload.
- Rerun the exact same test IDs against the revised version.
- Compare findings and test outcomes, preserving failures and regressions.
- Never claim a fix is verified if a test was skipped, failed to execute, or ran against a different scenario without disclosure.

Acceptance criteria:
- A user can compare before/after findings and test statuses.
- An improvement is only claimed where the recorded outputs support it.

### 8.10 Export — P1 if time is short

- Export a Markdown report and/or JSON bundle.
- Include file inventory, findings, evidence, Unicode code points, test suite, trace summaries, model provenance, analyzer version, and limitations.
- Ensure exports escape HTML and preserve code points in a reviewable form.
- Do not include secrets or unnecessary private file content in an export by default.

### 8.11 Optional future features — P2

- Git repository import and commit/PR checks.
- Batch scans across multiple skills.
- Configurable organizational policies and allow/deny lists.
- CI action and command-line interface.
- Signature or checksum of scanned skill archive.
- Rule pack versioning and user-defined rules.
- More advanced whitespace steganography detection.
- More complete HTML/CSS rendering analysis.
- Additional language/runtime integrations for optional sandboxed execution.
- Scan history, multiple users, and team review workflow.

---

## 9. Functional requirements summary

| ID | Requirement | Priority | Main owner |
|---|---|---:|---|
| FR-01 | Upload ZIP or paste `SKILL.md`; safely parse files | P0 | Dev + Systems |
| FR-02 | Validate paths, sizes, encodings, and file inventory | P0 | Systems |
| FR-03 | Run deterministic instruction/security rules | P0 | Algo |
| FR-04 | Detect zero-width/default-ignorable and bidi controls | P0 | Algo |
| FR-05 | Detect suspicious Unicode homoglyph/confusable patterns | P0 | Algo |
| FR-06 | Detect HTML comments and common hidden HTML styling | P0 | Algo |
| FR-07 | Detect anomalous whitespace and supported simple whitespace encoding patterns | P0 | Algo |
| FR-08 | Show raw/rendered/reveal-invisibles forensic views | P0 | Dev |
| FR-09 | Run contextual analysis with an open-weight model | P0 | ML |
| FR-10 | Generate schema-validated adversarial test scenarios | P0 | ML + Algo |
| FR-11 | Execute scenarios only through mock tools | P0 | Systems |
| FR-12 | Record source-linked findings and simulated traces | P0 | Systems + Dev |
| FR-13 | Produce capability passport and report summary | P0 | Dev + ML |
| FR-14 | Suggest fix and retest the same scenario suite | P0 | ML + Dev + Algo |
| FR-15 | Export report | P1 | Dev |
| FR-16 | GitHub/CI/batch scan integration | P2 | Future |

---

## 10. UX requirements and information architecture

### 10.1 Main screens

1. **Home / New Scan**
   - Upload ZIP or paste `SKILL.md`.
   - Explain what files will be inspected and the safety boundaries.
   - Show local/remote model status before scan when feasible.

2. **Scan Progress**
   - Steps: validate files → parse → static checks → hidden-content scan → model analysis → generate tests → simulate tests → create report.
   - Display progress and graceful errors for unavailable model inference.

3. **Overview / Capability Passport**
   - Skill metadata, file inventory, finding counts, test outcomes, model status, and important limitations.

4. **Findings Explorer**
   - Filter by severity, category, path, detector type, and status.
   - Select a finding to see evidence and remediation.

5. **Forensic Source Viewer**
   - Raw source, safe rendered preview, and reveal-invisibles view.
   - Line numbers, exact Unicode code points, hidden comment blocks, whitespace marks, confusable comparisons.

6. **Attack Lab**
   - Test name, purpose, setup, expected policy result, actual result, trace, and pass/fail/needs-review status.

7. **Fix & Compare**
   - Original and suggested revision side-by-side.
   - Same-suite rerun, outcome comparison, unresolved findings, and export.

### 10.2 Accessibility and content safety

- Do not rely on color alone to indicate severity or status.
- Label raw user-controlled content clearly and escape it before rendering.
- Make the forensic view keyboard navigable and provide textual labels for invisible characters.
- Keep source and any normalized representation visually distinct.
- Avoid alarming UI language when evidence is only heuristic.

---

## 11. Architecture proposal

### 11.1 Components

- **Frontend:** React + Vite; optional Tailwind CSS.
- **API:** Python + FastAPI.
- **Parser and static analyzer:** Python modules with stable file/line offsets.
- **Unicode scanner:** Unicode property checks, pinned confusables data, HTML-comment/hidden-style pattern detection, and whitespace heuristics.
- **Model adapter:** provider-neutral interface for a documented open-weight model using local inference or a configured inference endpoint.
- **Mock-tool harness:** deterministic allowlisted tools, policy gate, test runner, and event trace collector.
- **Persistence:** Start with JSON/in-memory scan objects if fastest; use SQLite if history is needed and time permits.
- **Export:** JSON first; Markdown export can be layered on top.

### 11.2 Suggested repository structure

```text
skillsentry/
├── frontend/
├── backend/
│   └── app/
│       ├── api/
│       ├── ingest/
│       ├── parser/
│       ├── analyzers/
│       │   ├── static_rules.py
│       │   ├── unicode_hidden_content.py
│       │   ├── confusables.py
│       │   └── whitespace.py
│       ├── model_adapter/
│       ├── test_generation/
│       ├── harness/
│       ├── reports/
│       └── schemas.py
├── tests/
│   ├── fixtures/
│   │   ├── benign/
│   │   └── adversarial/
│   ├── test_unicode_hidden_content.py
│   ├── test_archive_security.py
│   ├── test_static_rules.py
│   └── test_mock_harness.py
├── examples/
├── docs/
├── README.md
├── LICENSE
├── .env.example
└── docker-compose.yml  # optional
```

### 11.3 Recommended API surface

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/health` | API and model-adapter status |
| `POST` | `/api/scans` | Upload a package or submit pasted skill text; return scan ID |
| `GET` | `/api/scans/{scan_id}` | Scan status and progress |
| `GET` | `/api/scans/{scan_id}/report` | Findings, tests, traces, and limitations |
| `GET` | `/api/scans/{scan_id}/files` | File inventory and scan coverage |
| `GET` | `/api/scans/{scan_id}/files/{file_id}/view` | Source view and detected annotations |
| `POST` | `/api/scans/{scan_id}/tests/{test_id}/run` | Run one allowlisted mock scenario |
| `POST` | `/api/scans/{scan_id}/rerun` | Rerun a suite against a revised copy/upload |
| `GET` | `/api/scans/{scan_id}/export?format=json` | Download report bundle |

The MVP can simplify endpoints, but the frontend and backend must share one schema and error format.

---

## 12. Data model

### 12.1 Scan

```json
{
  "scan_id": "scan_demo_001",
  "created_at": "ISO-8601 timestamp",
  "skill_name": "research-helper",
  "input_kind": "zip",
  "status": "completed",
  "files_scanned": 3,
  "files_skipped": 0,
  "analyzer_version": "0.1.0",
  "model": {
    "name": "configured-open-weight-model",
    "revision": "record-if-available",
    "license": "record-exact-license",
    "inference_mode": "local-or-remote"
  },
  "limitations": ["Simulated tools only", "No arbitrary code execution"]
}
```

### 12.2 Finding

```json
{
  "finding_id": "F-UNICODE-001",
  "category": "invisible_unicode",
  "severity": "medium",
  "title": "Zero-width character in instruction text",
  "source_file": "references/guide.md",
  "line_start": 42,
  "column_start": 18,
  "line_end": 42,
  "evidence": "escaped source excerpt",
  "observed_fact": "U+200B ZERO WIDTH SPACE occurs between these characters",
  "interpretation": "May be intended to obscure or separate text; review context",
  "detector": "deterministic_unicode_scanner",
  "confidence": null,
  "status": "needs_review",
  "related_test_ids": []
}
```

For deterministic findings, do not manufacture a statistical confidence score; use a definite observation and a separate heuristic priority if needed.

### 12.3 TestCase

Fields: `test_id`, `name`, `purpose`, `source_finding_ids`, `setup_fixture`, `tool_sequence`, `expected_policy_decisions`, `expected_outcome`, `schema_version`.

### 12.4 TraceEvent

Fields: `event_id`, `test_id`, `tool_name`, `sanitized_arguments`, `policy_decision`, `decision_reason`, `mock_result_summary`, `timestamp`.

### 12.5 FileAnnotation

Fields: `file_id`, `relative_path`, `line`, `column`, `start_offset`, `end_offset`, `annotation_type`, `code_point`, `unicode_name`, `escaped_excerpt`, `detector_id`, `severity`, `notes`.

---

## 13. Non-functional requirements

### Security

- Treat all uploaded files and model outputs as untrusted.
- Reject archive traversal, absolute paths, symlinks, file collisions, and resource-exhaustion payloads.
- No execution of uploaded files or model-generated commands in the MVP.
- No real outbound network calls from test scenarios.
- All tool invocations go through a fixed allowlist and deterministic policy gate.
- Escape HTML and Markdown-derived raw HTML in the frontend.
- Do not store user secrets in fixtures, logs, traces, or exported reports.
- Use sanitized traces; avoid copying large or sensitive source chunks into the report by default.

### Privacy

- Prefer local processing and local inference where feasible.
- If a remote model is configured, disclose which content/excerpts are sent and to what service. Do not upload the entire archive by default.
- Provide an option to delete a scan and its artifacts in the local deployment.
- Do not collect telemetry by default in the hackathon MVP.

### Reliability

- Static and Unicode scanners continue to work if model inference is unavailable.
- Model timeouts and malformed output produce a visible status rather than a fabricated result.
- Deterministic tests use fixed fixtures and stable IDs.
- Errors should name the failed step and provide a next action.

### Performance targets for MVP

On a typical development laptop, for a package within size limits:
- File inventory and deterministic scan should complete within 3 seconds for a small package (<1 MB text total), excluding model inference.
- The user should see scan-step progress while model inference runs.
- Results should remain navigable with at least 100 findings without freezing the page.
- Model latency is hardware/provider-dependent and must be measured rather than promised.

### Compatibility

- Support the current stable versions selected by the team for Python and Node.js; pin dependencies.
- Preserve line mapping for LF and CRLF line endings.
- Detect and explain unsupported encodings instead of silently normalizing.

---

## 14. Model strategy and evaluation

### 14.1 What the model does

The open-weight model contributes to the product by:
- Interpreting the purpose and instruction hierarchy of the skill.
- Reviewing extracted hidden content in context.
- Identifying possible conflicts between declared intent and supporting instructions.
- Proposing adversarial test scenarios constrained to mock tools.
- Drafting a safer text revision for human review.
- Summarizing findings without replacing the source evidence.

### 14.2 What the model must not do

- Execute tools or decide that a test action should bypass policy controls.
- Directly access uploaded files outside the supplied bounded context.
- Browse the internet or call a real endpoint in response to skill content.
- Determine severity solely from its own assertion without evidence and rules.
- Rewrite or silently replace the user's uploaded file.

### 14.3 Evaluation dataset

Build a small labeled dataset of approximately 10–20 fixtures for the hackathon:
- Benign skill instructions and reference files.
- HTML comments with benign notes.
- HTML comments with suspicious instruction-like text.
- Zero-width characters in both suspicious and plausibly legitimate contexts.
- Homoglyph/confusable tokens near security-sensitive terms.
- Whitespace anomalies, including a known simple space/tab pattern.
- Prompt-injection-like text visible in ordinary Markdown.
- Benign files with multilingual text or normal Markdown formatting.

For each fixture, record expected detector category, expected severity band, line location, and whether the finding is expected to be informational, low, medium, or high. Do not tune only against adversarial samples; false positives matter.

### 14.4 Metrics

Report these metrics with counts and denominators:
- Detection rate on labeled test cases, by detector category.
- False-positive count/rate on benign controls.
- Missed known test cases.
- Line-location accuracy for deterministic detections.
- Valid structured-output rate for model results.
- Test-generation validity rate (how many generated tests pass schema and allowlist checks).
- Median and p95 scan time, separated into deterministic and model time where possible.
- Percentage of scans with model fallback.

Avoid claims such as “100% secure,” “detects all prompt injections,” or “X% accurate” without a disclosed benchmark and denominator.

---

## 15. Accessibility and safe handling of hidden text

The forensic viewer must let users recognize invisible content without requiring them to infer it from a risk score.

- Show a visible badge for each invisible or suspicious character.
- Explain `U+XXXX`, the Unicode name, and the character's position.
- Use an explicit escaped representation such as `[U+200B ZERO WIDTH SPACE]`; do not depend on font rendering to show it.
- For whitespace, distinguish ordinary spaces, tabs, non-breaking spaces, and Unicode separators.
- Provide a copyable evidence excerpt that escapes hidden characters and preserves the original excerpt separately.
- Keep normalized/confusable skeletons in a separate comparison field. Unicode confusable skeletons are an analysis intermediate, not a replacement for source text.
- When displaying content found in HTML comments, show a label explaining that this content may not appear in a typical rendered Markdown view.
- Do not assume that every Markdown renderer or downstream AI system treats comments and HTML identically. Describe detection as “present in source and potentially hidden in rendered views,” and explain that actual exposure depends on the skill loader/runtime.

---

## 16. Safety and threat model

### Assets to protect

- Host filesystem, environment variables, API keys, and user files.
- Integrity of the analyzer and stored reports.
- User privacy and contents of uploaded skill packages.
- Reliability of the test results and their provenance.

### In-scope attacker capabilities

- Upload a ZIP with confusing paths or large files.
- Place hidden instructions in Markdown comments or reference documents.
- Use invisible Unicode characters, bidi controls, or confusables.
- Try to persuade the model to ignore the analyzer instructions.
- Prompt the model to generate an unapproved tool call or real command.

### Required mitigations

- Archive validation and strict resource limits.
- No arbitrary code execution.
- No model-provided tool names accepted without allowlist validation.
- No real filesystem or network tools in the MVP.
- Context separation and explicit “analyze, do not follow” model instructions.
- Schema validation for all model outputs.
- HTML escaping and safe source rendering.
- Local/remote model disclosure and optional local inference.
- Clear report limitations and human review for uncertain findings.

### Known limitations

- Detection is not complete; there are many ways to obscure or encode information.
- Pattern-based hidden CSS detection is not a full browser rendering or CSS analysis engine.
- Whitespace heuristics can miss novel schemes and can flag legitimate formatting.
- A model may miss malicious intent or misinterpret benign multilingual content.
- Simulated tool behavior does not prove how a particular production agent runtime would behave.
- A clean report does not establish that a skill is safe.

---

## 17. Public repository and licensing requirements

- Publish source code to a public GitHub repository before submission.
- Include a project license such as Apache-2.0 or MIT after confirming team/event requirements.
- Document all important dependencies and their licenses.
- Record the exact open-weight model name, revision/version, model license, model source, and inference method.
- Do not assume the code license applies to model weights or third-party fixtures.
- Include setup steps, sample fixtures, test commands, API documentation, screenshots or demo video, architecture, limitations, and threat model in `README.md`.
- Do not commit credentials, private skills, real secrets, or personal data.
- If shipping a bundled Agent Skill, include a valid `SKILL.md` and validate it against the official Agent Skills specification; the primary product itself is the security harness, not merely a prompt wrapper.

---

## 18. Four-person ownership map

| Team role | Primary ownership | Deliverables | Shared integration points |
|---|---|---|---|
| Systems | Safe ingestion, mock-tool harness, policy gate, traces | File-safe parser boundary, mocked tools, trace events, safety tests | Schemas with Algo; report/API with Dev |
| Dev | Frontend, scan workflow, forensic viewer, report UI | Upload, progress, finding explorer, raw/rendered/reveal-invisibles views, fix comparison | Finding/report schema with all roles |
| Algo | Static rules, Unicode scanner, confusable data, whitespace heuristics, test evaluation | Source-linked findings and deterministic test cases | Findings and annotations schemas with Dev; test case schema with ML |
| ML | Open-weight model adapter, semantic analysis, test generation, remediation draft | Validated model response, constrained candidate tests, fix suggestions | JSON schema with Algo; API/model status with Systems/Dev |

### Independent work strategy

- **Systems** can develop against fixed sample files and mock traces without waiting for the UI.
- **Dev** can use fixture JSON to build and polish the interface before any model is connected.
- **Algo** can implement and unit-test detectors on plain text fixtures without the model.
- **ML** can build a standalone model adapter that accepts text and returns schema-valid JSON; use cached fixtures if model setup takes too long.

Each role should publish a working stub by hour 1 and a testable independent component by hour 3.

---

## 19. Ten-hour delivery roadmap and checkpoints

| Time | Checkpoint | Deliverable and exit criteria |
|---|---|---|
| 0:00–0:30 | Kickoff | Confirm MVP scope, sample attack story, safety boundaries, model choice, and repository structure. |
| 0:30–1:00 | **CP1 — Contracts locked** | Shared `Finding`, `FileAnnotation`, `TestCase`, `TraceEvent`, and `ScanReport` schemas committed; every role has a runnable skeleton or fixture. |
| 1:00–3:00 | Parallel implementation | Systems: mock tools and traces. Dev: UI against fixtures. Algo: static + hidden-content detectors. ML: model adapter and schema validation. |
| 3:00–3:15 | **CP2 — Independent demo** | Each person demonstrates one passing example. Fix schema mismatches immediately. |
| 3:15–5:00 | Vertical-slice integration | Upload/parse → deterministic scan → model analysis → safe test generation → mock execution → report. |
| 5:00–5:15 | **CP3 — End-to-end path works** | One-click scan finishes and shows a source-linked finding plus a simulated trace. If not, cut optional features. |
| 5:15–6:30 | Retest flow | Add proposed edit, same-suite rerun, before/after result comparison, and graceful model fallback. |
| 6:30–7:00 | **CP4 — Signature demo passes** | Hidden Unicode/comment example is detected, evidence view shows exact characters, mock action is blocked, and retest result is visible. |
| 7:00–8:15 | Quality and evaluation | Run benign/adversarial fixtures, measure false positives, validate ZIP safety and model output schema, write README. |
| 8:15–9:00 | Release candidate | Clean-start test, local deployment or chosen hosting, model provenance and license documented. |
| 9:00–9:30 | **CP5 — Feature freeze** | No new features; fix demo-blocking defects only. |
| 9:30–10:00 | Rehearsal and submission | Run the full three-minute demo, verify public repository/license, and ensure fallback works offline or with model unavailable. |

### Checkpoint rule

Every checkpoint must end with a visible artifact or repeatable test result. If the project slips, cut GitHub import, advanced visualization, auto-patching, and custom execution features first. Do not cut the source-evidence viewer, mock-tool boundary, or end-to-end demo.

---

## 20. Demo scenario

### Setup

Create a clearly fictional skill called `research-assistant` with ordinary research instructions and a `references/guide.md` file. Add a suspicious instruction hidden inside an HTML comment and include a zero-width character or mixed-script confusable in a separate test fixture. Do not use real credentials or real network addresses.

### Three-minute walk-through

1. **Upload (0:00–0:20):** Show file inventory and capability passport.
2. **Reveal (0:20–0:55):** Open `references/guide.md`; show the normal preview and reveal-invisibles view. Point to the exact comment/Unicode code point and source location.
3. **Analyze (0:55–1:20):** Show deterministic scanner evidence and the open-weight model's contextual interpretation as separate types of evidence.
4. **Test (1:20–1:50):** Run the relevant generated scenario. Display a simulated canary-file request being blocked and/or mock outbound request being denied.
5. **Fix (1:50–2:20):** Preview a safer edit and apply it to a copy of the sample.
6. **Retest (2:20–2:45):** Rerun exactly the same test IDs and compare outcomes without hiding remaining failures.
7. **Close (2:45–3:00):** Emphasize open-weight AI, original harness, Unicode hidden-content feature, reproducible fixtures, open license, and clear limitations.

---

## 21. Acceptance criteria for hackathon completion

The MVP is considered complete when all of the following are true:

- [ ] Public GitHub repository exists and includes an open-source license.
- [ ] A user can upload a sample skill ZIP or paste `SKILL.md`.
- [ ] The package parser validates paths and size limits; uploaded scripts are never executed.
- [ ] `SKILL.md` and supported reference files are scanned for static findings.
- [ ] Zero-width/default-ignorable characters are detected and shown by code point and location.
- [ ] Suspicious homoglyph/confusable cases are detected using versioned data/methodology.
- [ ] Non-empty HTML comments and common hidden HTML styles are surfaced safely.
- [ ] Suspicious whitespace patterns are detected with evidence and documented limitations.
- [ ] The user can inspect raw source, safe preview, and reveal-invisibles annotations.
- [ ] An open-weight model contributes at least one contextual analysis or test hypothesis, with model provenance documented.
- [ ] At least five test scenarios can run using allowlisted mock tools.
- [ ] Simulated tool calls are blocked/allowed/flagged by deterministic policy and recorded in traces.
- [ ] A fix can be previewed and the same test suite rerun against a revised copy.
- [ ] The report distinguishes observed facts, model inferences, simulated results, and unknowns.
- [ ] A benign control fixture is included and false positives are acknowledged.
- [ ] A clean-start setup and live demo have been rehearsed.

---

## 22. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Model setup or inference takes too long | Core AI feature unavailable | Choose model early; run one smoke test in hour 1; build adapter with cached fixture fallback. |
| Unicode heuristics create too many false positives | User distrusts findings | Context-sensitive severity, explicit code point evidence, benign multilingual fixtures, and “needs review” status. |
| Team spends too long on detection breadth | No integrated product | Aim for end-to-end flow by hour 5; start with limited, testable detectors. |
| Hidden content is rendered unsafely | Cross-site scripting / UI issues | Never insert uploaded HTML as live DOM; escape all content and show raw text in safe viewer. |
| ZIP path traversal or resource exhaustion | Host files or server may be at risk | Strict archive validation, size/count limits, temporary roots, no symlink extraction. |
| Model output proposes real tool actions | Unsafe test execution | Strict schema and allowlist validation; never execute arbitrary output. |
| Team claims security guarantees | Misleading result | Report exact coverage, test outcomes, and limitations; avoid universal safe/unsafe claims. |
| Unicode standard/data updates | Detection drift | Pin and document Unicode/UTS #39 data version; add tests before updating. |
| Reference file is parsed differently by different agent runtimes | Hidden-content conclusion overgeneralized | State that runtime exposure depends on the downstream loader; report source presence, not guaranteed model exposure. |

---

## 23. Suggested backlog after the hackathon

1. Add CI integration for scanning skill changes in pull requests.
2. Add command-line batch scanning and SARIF-like output for developer workflows.
3. Improve CSS/rendered-view analysis by comparing raw Markdown and a sanitized renderer.
4. Expand Unicode confusable and whitespace-steganography tests using versioned corpora.
5. Add user-configurable policies and organization-specific allowlists.
6. Explore language-specific static analysis of scripts without executing them.
7. Add reproducible scan bundles and signatures for verifying exactly what was reviewed.
8. Add an optional isolated runtime for carefully selected skill integration tests, with much stronger sandboxing and security review than the hackathon mock harness.
9. Add model comparison and evaluation dashboards.
10. Create a bundled SkillSentry Agent Skill for developers who want to invoke the scanner from an agent; validate that skill against the official Agent Skills format.

---

## 24. Definitions

- **Agent Skill:** A directory-based package centered on `SKILL.md`, optionally containing scripts, references, assets, and related files.
- **Zero-width/default-ignorable character:** A Unicode character that may have no visible glyph or may affect text behavior/formatting. Some are legitimate in certain scripts and emoji sequences.
- **Bidi control:** A character that influences bidirectional text ordering and can make source order differ from displayed order.
- **Homoglyph/confusable:** A character or sequence that can resemble another character or sequence visually.
- **HTML comment:** Text between `<!--` and `-->`, typically not shown in a rendered HTML/Markdown view.
- **Whitespace anomaly:** Unusual space/tab/non-breaking-space patterns that may be accidental formatting or may be used to conceal data.
- **Mock tool:** A deterministic simulation of a tool. It does not access the host system or perform a real external action.
- **Observed fact:** A deterministic property of the source or a recorded simulated action.
- **Model inference:** A contextual interpretation or hypothesis generated by the open-weight model; it may be wrong.
- **Regression test:** A previously run scenario repeated against a revised version to see whether the outcome changed.

---

## 25. Reference standards and resources

These links should be checked again at implementation time in case specifications or data revisions have changed.

1. **Agent Skills specification:** https://github.com/agentskills/agentskills/blob/main/docs/specification.mdx  
   Describes the skill directory structure, required `SKILL.md` metadata, optional `references/`, `scripts/`, and `assets/` directories, and validation guidance.
2. **Agent Skills project:** https://github.com/agentskills/agentskills  
   Canonical project and open development repository.
3. **Unicode Technical Standard #39 — Unicode Security Mechanisms:** https://unicode.org/reports/tr39/  
   Defines mechanisms for confusable detection and mixed-script analysis. Pin the data version used and do not use a confusable skeleton as replacement source text.
4. **Unicode Technical Report #36 — Unicode Security Considerations:** https://www.unicode.org/reports/tr36/  
   Background on security issues related to Unicode text handling.
5. **OWASP Top 10 for LLM Applications:** https://owasp.org/www-project-top-10-for-large-language-model-applications/  
   General security context for prompt injection and LLM application risks.

---

## Final product definition

SkillSentry is a reproducible, open-source security testing harness for Agent Skills. It combines source-level analysis—including a forensic scanner for invisible Unicode, confusables, HTML comments, and suspicious whitespace—with an open-weight model that interprets content and proposes tests, and a deterministic mock-tool harness that records simulated behavior. Users receive evidence-linked findings, review proposed remediations, and rerun the same tests to compare outcomes.

The hackathon success criterion is a working end-to-end demonstration, honest evaluation, safe handling of untrusted files, and a public, licensed repository—not a claim that the product can prove every skill safe.
