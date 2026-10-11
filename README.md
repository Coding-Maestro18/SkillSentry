# SkillSentry

Open-source security testing workbench for **AI Agent Skills**. Upload a skill package, see what it
really contains (including invisible Unicode, homoglyphs, HTML comments, hidden HTML and
whitespace-encoded text), run adversarial scenarios against **deterministic mock tools**, review
evidence, apply a fix to a copy and rerun **the same test suite** to compare.

> SkillSentry analyzes untrusted content and simulates behaviour. It **never executes** uploaded
> code, makes no real network requests from the harness, and does not certify a skill as safe.

See [`docs/prd.md`](docs/prd.md), [`docs/architecture.md`](docs/architecture.md) and
[`docs/decisions.md`](docs/decisions.md).

## Quick start

Requirements: Python 3.11+, Node 18+ (only to build the UI). Ollama is optional.

```bash
pip install -r requirements-dev.txt
cd frontend && npm install && npm run build && cd ..
cp .env.example .env                     # optional
uvicorn app.main:app --app-dir backend --port 8000
```

Open http://localhost:8000. Upload `examples/research-assistant.zip` (or click **Load demo skill**).
API docs: http://localhost:8000/docs.

Frontend dev mode (hot reload, proxies `/api` to :8000): `cd frontend && npm run dev` → http://localhost:5173.

### Optional: open-weight model

```bash
ollama pull qwen2.5:7b-instruct          # Qwen2.5 7B Instruct, Apache-2.0
ollama serve
```

Without a reachable model, SkillSentry runs in **static-only mode**, shows
"Model unavailable — static analysis only", and never fabricates model output.
Providers: `ollama` (default), `openai_compatible` (vLLM, llama.cpp server, LM Studio, hosted
open-weight endpoints), `replay` (re-serves responses cached from earlier live runs, labelled
`cached-replay`), `disabled`.

Docker (optional): `docker compose up --build`, then `docker compose exec ollama ollama pull qwen2.5:7b-instruct`.

## Tests and evaluation

```bash
python -m pytest                          # archive safety, rules, Unicode scanner, model validation, harness, API e2e
python scripts/evaluate.py                # labelled fixtures: detections found, benign false positives, timings
python scripts/build_fixtures.py          # regenerate fixtures + example zips from documented escapes
```

Current results on the small labelled set (11 fixtures; **not** a general accuracy claim):
16/16 expected detections found, 0/3 benign fixtures with a medium/high finding, ~6 ms median
deterministic scan.

## What it detects

| Rule | Detector | What |
|---|---|---|
| SS-OVR-001 | static | Instructions to ignore/override prior/system rules |
| SS-SEC-001 | static | Reading/disclosing secrets, keys, `.env`, SSH keys (negated guidance is skipped) |
| SS-EXF-001 | static | Sending data to URLs/webhooks/external servers |
| SS-CAP-001 | static | Shell execution, `curl \| sh`, sudo, disabling safeguards |
| SS-CNC-001 | static | Hiding actions from the user |
| SS-ROLE-001 | static | Role/system-prompt hijack |
| SS-ENC-001/002 | static | Base64 payloads (decoded) and "decode the following" directives |
| SS-PUR-001 | static | Behaviour not mentioned in the declared description |
| SS-UNI-001 | unicode | Zero-width/default-ignorable characters (context-aware: emoji ZWJ, ZWNJ in Persian/Indic, BOM are informational) |
| SS-UNI-002 | unicode | Bidi controls (Trojan Source) |
| SS-UNI-003 | unicode | Unicode tag characters (ASCII smuggling), decoded |
| SS-UNI-004 | unicode | Zero-width binary encoding |
| SS-UNI-005 | unicode | Mixed-script / confusable tokens with comparison skeleton |
| SS-HID-001/003 | markdown | Non-empty and unterminated HTML comments (severity from content) |
| SS-HID-002 | markdown | `display:none`, `visibility:hidden`, `opacity:0`, `font-size:0`, same colour fg/bg, `hidden` |
| SS-WS-001/002/003 | whitespace | Space/tab trailing patterns (decoded when possible), unusual Unicode spaces, long runs |
| SS-MODEL | model | Model interpretations — quotes verified against source; capped at medium unless corroborated |

Severity is a prioritization estimate, not proof of intent.

## API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | API, detector versions and model status |
| POST | `/api/scans` | multipart `file` (ZIP) or `skill_text`; returns scan ID (202) |
| GET | `/api/scans/{id}` | Status and stage |
| GET | `/api/scans/{id}/report` | Full report |
| GET | `/api/scans/{id}/files` | Inventory and coverage |
| GET | `/api/scans/{id}/files/{file_id}/view` | Raw, reveal-invisibles segments, preview, annotations |
| POST | `/api/scans/{id}/tests/{test_id}/run` | Re-run one validated mock scenario |
| POST | `/api/scans/{id}/fix-suggestion` | Model or deterministic fix as a diff + revised copy |
| POST | `/api/scans/{id}/rerun` | Same suite against a revised copy (`{"files": {path: content}}`) |
| GET | `/api/scans/{id}/comparison` | Before/after for a revision scan |
| GET | `/api/scans/{id}/export?format=json\|markdown` | Report download |
| DELETE | `/api/scans/{id}` | Delete scan artifacts |

Errors always use `{"error": {"code", "message", "details", "request_id"}}`, with no stack traces or server paths.

## Security model

- ZIPs are read in memory: absolute paths, `..`, backslashes, symlinks, encrypted entries, case/NFC path collisions, too many files and oversize content (enforced while streaming, so lying headers don't help) are rejected.
- Uploaded text is never evaluated; frontmatter is parsed as inert data.
- The model gets bounded, escaped excerpts wrapped as untrusted data, no tools, and its output is schema-validated. Model-proposed tests must use allowlisted tools, schema-valid arguments, no shell-like values, no URLs absent from the skill, and an exact quote from the skill.
- Mock tools touch only in-memory fixtures; canary secrets are fake and never returned.
- The UI renders all content as text (no `dangerouslySetInnerHTML`); the API sets a strict CSP.
- This repository's own source contains no literal hidden characters (`scripts/escape_invisibles_in_source.py`).

## Limitations

Detection is incomplete; hidden CSS checks are regex-based (not a rendering engine); whitespace
heuristics can miss novel schemes or flag formatting; the confusables table is a pinned subset;
simulated behaviour doesn't prove how a real runtime acts; a clean report doesn't establish safety.

## Layout

```
backend/app/   ingest/ parser/ analyzers/ model_adapter/ test_generation/ harness/ reports/ persistence/ api/
frontend/src/  components/ pages/ api/ types/
tests/         pytest suites + fixtures/{benign,adversarial} + labels.json
examples/      research-assistant demo (+ .zip), benign zip, unsafe-traversal.zip
scripts/       build_fixtures.py, evaluate.py, escape_invisibles_in_source.py
```

## License

Code: MIT (see `LICENSE`). Model weights are licensed separately by their authors (Qwen2.5-7B-Instruct: Apache-2.0).
