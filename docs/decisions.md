# Resolved open decisions (architecture §16)

| # | Decision | Resolution |
|---|---|---|
| 1 | Open-weight model and inference | Default `qwen2.5:7b-instruct` (Qwen2.5 7B Instruct, Apache-2.0) via local Ollama. Any OpenAI-compatible server hosting open weights works via `SKILLSENTRY_MODEL_PROVIDER=openai_compatible`. Model, revision, license and inference mode are recorded in every report. |
| 2 | Artifact storage | JSON files per scan under `data/scans/<scan_id>/` (`report.json`, `files.json`). Deletable via `DELETE /api/scans/{id}`. |
| 3 | Supported `references/` extensions | `.md .txt .yaml .yml .json .toml` |
| 4 | Confusables data | Pinned subset of Unicode `confusables.txt` 15.1.0 (Cyrillic/Greek/Armenian/Latin look-alikes) + NFKC. Unicode properties from Python `unicodedata` (version reported). |
| 5 | Limits | 10 MB compressed, 25 MB extracted, 500 files, 2 MB per text file (all configurable). |
| 6 | Fixed suite | `suite-v1`: TC-001 benign control, TC-002 canary secret, TC-003 outbound transfer, TC-004 override/role hijack, TC-005 concealed instruction, TC-006 capability expansion, TC-007 concealment from user, TC-008 purpose mismatch. Up to 4 validated model-proposed tests (TM-xxx) are appended. |
| 7 | Schema owner | `backend/app/schemas.py` is the single source; `frontend/src/types/index.ts` mirrors it. |
| 8 | Markdown export | Implemented (`?format=markdown`), alongside JSON. |

## Test semantics

The harness never runs skill code. A deterministic "simulated agent" performs a test's mock tool
sequence only when the trigger is present in the skill version under test (a matching rule finding,
or an exact quoted excerpt for model-proposed tests). Outcomes:

- **pass** – not triggered, or every simulated action was ALLOWed (benign control).
- **fail** – the skill text induces an action the policy gate BLOCKs.
- **needs_review** – only FLAGged actions, or a benign control unexpectedly blocked.

Because tool arguments are frozen when the suite is generated, a rerun against a revised copy uses
identical test IDs and arguments, so before/after comparisons are like-for-like.

## Documented decoders

- Base64 (RFC 4648) → UTF-8, accepted when ≥95% printable (`SS-ENC-001`).
- Unicode tag characters → ASCII (code point − 0xE0000) (`SS-UNI-003`).
- Zero-width bits: U+200B=0, U+200C=1, 8-bit ASCII MSB-first (`SS-UNI-004`).
- Trailing whitespace bits: SPACE=0, TAB=1, 8-bit ASCII MSB-first, ≥2 printable bytes (`SS-WS-001`).

A payload is reported as decoded only when one of these produced it; otherwise findings say
"payload not decoded".
