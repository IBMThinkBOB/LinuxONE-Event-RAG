# LinuxONE Real Hosted System — Required Code Changes

## Purpose
This document lists the **code changes and repo/config changes** needed to turn the current LinuxONE prototype into a **real hosted system** rather than a temporary demo. It is based on the current repo state and the runtime behavior already observed on LinuxONE:

- The **frontend can run** on LinuxONE and is reachable through the SSH tunnel.
- The **current backend cannot boot as-is** because it imports `app.models.*`, but the `backend/app/models/` package does not exist in the deployed commit.
- The current backend dependency set mixes **runtime packages** with **AI/PDF/tokenizer packages**, which is blocking deployment on LinuxONE/s390x.

This plan is organized into:
1. **Must-do code changes**
2. **Strongly recommended production changes**
3. **Conditional changes** depending on architecture decisions
4. **Open questions that must be answered before finalizing the build/deploy path**

---

# 1) Must-Do Code Changes

These changes are required if the current project is going to become the real hosted LinuxONE runtime.

---

## 1.1 Restore or rebuild the missing backend package structure

### Current issue
The current backend imports these modules:

- `app.models.db_connection`
- `app.models.database`
- `app.models.schemas`

But the current repo structure does **not** contain:

```text
backend/app/models/
```

This means the current backend is structurally incomplete and cannot run as written.

### Required change
One of the following must happen:

#### Option A — Restore the missing package from another branch / backup
Recreate these files if they already exist somewhere else:

```text
backend/app/models/__init__.py
backend/app/models/db_connection.py
backend/app/models/database.py
backend/app/models/schemas.py
```

#### Option B — Refactor imports if those modules were moved elsewhere
Update imports in:

```text
backend/app/main.py
backend/app/api/routes.py
```

to point to the new actual location of:
- DB session creation
- SQLAlchemy models
- Pydantic schemas

#### Option C — Rebuild the models package cleanly
If the files are permanently gone, recreate a minimal but correct backend package layout.

### Expected resulting layout
At minimum, the backend should have:

```text
backend/app/
├── api/
│   └── routes.py
├── models/
│   ├── __init__.py
│   ├── db_connection.py
│   ├── database.py
│   └── schemas.py
├── services/
├── utils/
├── config.py
└── main.py
```

---

## 1.2 Split Python dependencies into runtime vs. AI pipeline

### Current issue
The current `backend/requirements.txt` mixes:

- web runtime packages
- DB packages
- utility packages
- PDF-processing packages
- tokenizer packages
- AI/embedding packages

This causes LinuxONE deployment to fail on packages that are **not needed to boot the hosted runtime**.

### Required change
Split the backend dependencies into separate files.

#### Create `backend/requirements-base.txt`
This file should include only the packages required to run the hosted backend runtime:

Suggested categories:
- FastAPI / Uvicorn / multipart
- database / SQLAlchemy / pgvector
- dotenv / pydantic / settings
- requests
- numpy (only if runtime truly needs it)

#### Create `backend/requirements-ai.txt`
This file should include the optional LinuxONE-native AI path:

Suggested categories:
- `sentence-transformers`
- `torch`
- `transformers`
- `scikit-learn`
- `tiktoken`
- `PyMuPDF`

#### Keep `backend/requirements-dev.txt` optional
If you want clean separation, move:
- pytest
- pytest-asyncio
- black

into a dedicated dev-only file.

### Why this matters
This allows the **real hosted system** to deploy now using the base runtime, while keeping the AI path as a second-stage enablement.

---

## 1.3 Make AI/PDF/tokenizer imports optional or lazy

### Current issue
The current codebase imports LinuxONE-problematic packages directly inside service modules:

- `document_processor.py` imports `fitz`
- `embedding_service.py` imports `SentenceTransformer`
- `reranking_service.py` imports `CrossEncoder`
- `chunking.py` imports `tiktoken`

If any of these modules are imported during app startup, the backend can fail even if those features are not being used for the hosted runtime.

### Required change
Refactor all non-essential AI/PDF/tokenizer imports into **lazy imports** or feature-gated imports.

#### Files to modify
```text
backend/app/services/document_processor.py
backend/app/services/embedding_service.py
backend/app/services/reranking_service.py
backend/app/utils/chunking.py
```

### Required behavior
- Import heavy/optional packages **inside methods**, not at module import time.
- Raise clear runtime errors only when the feature is actually used.
- Never fail backend startup because `tiktoken`, `fitz`, `torch`, `SentenceTransformer`, or `CrossEncoder` is unavailable.

### Example design pattern
Instead of:

```python
from sentence_transformers import SentenceTransformer
```

at the top of the module, defer it until the service is initialized or called.

Similarly, `tiktoken` should be optional in `chunking.py`, with a fallback tokenizer behavior.

---

## 1.4 Convert the hosted runtime to use an external LLM path by default

### Current issue
The current runtime is still oriented around local embedding / local model assumptions in parts of the architecture.

For the real hosted LinuxONE system **right now**, the most practical production path is:

- LinuxONE hosts the app runtime
- LinuxONE performs orchestration / retrieval / formatting
- Generation is handled via **external LLM API**

### Required change
Create a real provider abstraction in the backend.

#### Files likely to modify
```text
backend/app/config.py
backend/app/services/llm_service.py
backend/app/api/routes.py
```

### Add configuration for provider selection
Introduce runtime config such as:

```text
LLM_PROVIDER=external
OPENAI_API_KEY=...
OPENAI_MODEL=...
ANTHROPIC_API_KEY=...
ANTHROPIC_MODEL=...
OLLAMA_BASE_URL=...
OLLAMA_MODEL=...
```

### Required backend behavior
- If `LLM_PROVIDER=external`, use external hosted API path.
- If `LLM_PROVIDER=ollama`, use local provider path later.
- The backend should not assume Ollama or local Qwen is present unless explicitly configured.

### Refactor recommendation
`llm_service.py` should expose one unified method such as:

```python
generate_response(query, context_chunks, answer_mode, ...)
```

but internally route to the selected provider.

---

## 1.5 Rebuild the real `/api/query` path so it can run without the AI-local path

### Current issue
The current `/api/query` route appears to assume:
- local embedding service
- local retrieval pipeline
- local DB/session models
- local LLM service wiring

That is fine long-term, but for the first **real hosted runtime**, you need the route to be able to operate in a reduced hosted mode if the local LinuxONE AI path is not fully ported yet.

### Required change
Refactor `/api/query` so it supports one of these real runtime modes:

#### Mode A — Hosted runtime + external generation + real retrieval
The preferred near-term production path.

#### Mode B — Hosted runtime + external generation + precomputed corpus import
If local embedding generation is not yet on LinuxONE.

#### Mode C — Hosted runtime + external generation + graceful degraded path
If retrieval layer is not yet ready.

### Files likely to modify
```text
backend/app/api/routes.py
backend/app/services/retrieval_service.py
backend/app/services/llm_service.py
backend/app/config.py
```

### Required behavior
- `/api/query` must remain stable as the canonical route.
- The route should not hard-fail just because offline/AI-heavy paths are unavailable.
- The route should build prompt context from LinuxONE-hosted data if available.
- The route should send the final generation request through the selected LLM provider.

---

# 2) Strongly Recommended Production Code/Config Changes

These changes are not optional if the target is a **real hosted system**, even if they are not the first blocker.

---

## 2.1 Make frontend API URL environment-driven

### Current issue
The frontend currently hardcodes:

```javascript
const API_BASE_URL = 'http://localhost:8000/api';
```

That works only through the SSH tunnel and is not appropriate for real hosted deployment.

### Required change
Refactor the frontend API client to use a Vite environment variable.

#### File to modify
```text
frontend/src/services/api.js
```

### Replace the hardcoded API base URL with something like:
- default to `/api` for reverse-proxy environments
- allow override with `VITE_API_BASE_URL`

### Required outcome
The frontend should work in all three cases:
1. local tunnel
2. same-host reverse proxy in production
3. explicit remote API URL if needed

---

## 2.2 Build the frontend for production instead of using Vite dev server

### Current issue
The frontend is currently being run via:

```bash
npm run dev
```

This is fine for debugging but not for a real hosted system.

### Required change
Use the Vite production build path.

#### Required workflow
```bash
npm install
npm run build
```

#### Output expected
A build directory such as:

```text
frontend/dist/
```

### Required deployment behavior
This built frontend should be served by **Nginx** (or another static server), not by the Vite dev server.

---

## 2.3 Add reverse-proxy support with Nginx

### Why this is needed
A real hosted LinuxONE system should expose a single browser-facing endpoint and route:
- `/` → frontend
- `/api/*` → backend

### Required repo/config additions
Add deployment config files such as:

```text
deploy/nginx/linuxone-rag.conf
deploy/systemd/linuxone-rag-backend.service
```

### Nginx behavior should include
- serve `frontend/dist`
- proxy `/api` to backend on `127.0.0.1:8000`
- optionally support WebSocket/proxy settings if needed later

### Why this matters
This removes the need for:
- hardcoded backend URLs
- Vite dev server in production
- multiple public ports

---

## 2.4 Add backend production entrypoint / service support

### Current issue
The backend is currently being started manually via `uvicorn`.

### Required change
Create a stable production backend entry path.

### Recommended options
- `gunicorn` + `uvicorn.workers.UvicornWorker`
- or managed `uvicorn` under `systemd`

### Suggested additions
```text
deploy/systemd/linuxone-rag-backend.service
scripts/start_backend.sh
```

### Required service behavior
- start on boot
- restart on failure
- run with the correct working directory and virtual environment
- write logs to journal/app logs

---

## 2.5 Introduce environment-specific settings files

### Current issue
The config currently appears to assume one blended environment.

### Required change
Create environment-specific configuration guidance and defaults.

#### Recommended files
```text
.env.example
.env.production.example
.env.linuxone.example
```

### Settings to include
- DB connection string / credentials
- LLM provider and API credentials
- CORS settings
- backend host/port
- frontend base URL
- embedding mode (local / external / precomputed)
- feature flags for optional AI pipeline

---

## 2.6 Add feature flags for hosted runtime modes

### Why this matters
The real hosted runtime should not require all optional features to be enabled at once.

### Required change
Add flags such as:

```text
ENABLE_LOCAL_EMBEDDINGS=false
ENABLE_LOCAL_RERANKING=false
ENABLE_LOCAL_PDF_PROCESSING=false
ENABLE_EXTERNAL_LLM=true
ENABLE_PRECOMPUTED_CORPUS=true
```

### Files likely to modify
```text
backend/app/config.py
backend/app/api/routes.py
backend/app/services/*.py
```

### Required behavior
The backend should boot and operate correctly depending on enabled/disabled feature sets.

---

# 3) Retrieval / Data Layer Changes for the Real Hosted System

These are the code changes needed if the hosted LinuxONE system is meant to support the actual RAG runtime.

---

## 3.1 Introduce a precomputed corpus import path

### Why this matters
Your architecture decision says that:
- PDF extraction
- chunking
- metadata tagging
- and possibly corpus embedding generation

can remain offline / off LinuxONE for now.

That means the hosted LinuxONE system needs an import path for:
- chunks
- metadata
- precomputed embeddings

### Required change
Add an import script or ingestion job, for example:

```text
backend/scripts/import_precomputed_corpus.py
```

### Responsibilities of this script
- load precomputed JSON/CSV/Parquet corpus
- store chunk rows in PostgreSQL
- store embeddings in pgvector
- preserve metadata such as:
  - title
  - filename
  - page number
  - section
  - topic tags
  - content

### Why this is important
It allows LinuxONE to host the **real retrieval runtime** without requiring LinuxONE-native corpus embedding generation on day one.

---

## 3.2 Rebuild or validate DB schema definitions

### Current issue
The backend references:
- `Document`
- `QueryLog`
- probably chunk/vector-related models

but those model definitions are currently missing from the deployed code structure.

### Required change
Define or restore the SQLAlchemy schema for:

Suggested minimum tables:
- `documents`
- `chunks`
- `query_logs`
- optional `topics` / `chunk_tags`

If using pgvector directly, the `chunks` table should include the vector column.

### Required files
Likely inside the restored/rebuilt:

```text
backend/app/models/database.py
```

### Related connection/session logic
Should live in:

```text
backend/app/models/db_connection.py
```

---

## 3.3 Make the retrieval service work with precomputed vectors

### Current issue
The retrieval path currently appears to assume local embedding-generation services and a specific backend structure.

### Required change
Refactor retrieval so it cleanly supports:

- DB-hosted vector search with pgvector
- precomputed chunk embeddings already stored in DB
- lightweight runtime orchestration on LinuxONE

### Files likely to modify
```text
backend/app/services/retrieval_service.py
backend/app/api/routes.py
```

### Required behavior
- if query embedding path is available, use it
- otherwise support a future external/alternate embedding path
- do not tightly couple retrieval service startup to all AI dependencies at import time

---

# 4) LinuxONE Runtime Packaging / Deployment Changes

These are not all code changes, but they are part of making the project actually hostable.

---

## 4.1 Add LinuxONE-specific dependency/install documentation

### Why this matters
LinuxONE uses **s390x**, and several packages in the current requirements already failed for architecture/toolchain reasons.

### Required repo additions
Add docs such as:

```text
LINUXONE_HOSTING.md
backend/requirements-base.txt
backend/requirements-ai.txt
```

### Should document
- Ubuntu packages needed for runtime
- optional packages needed later for AI enablement
- PostgreSQL/pgvector setup on s390x
- external LLM configuration
- frontend build + Nginx setup

---

## 4.2 Add systemd service definitions

### Suggested files
```text
deploy/systemd/linuxone-rag-backend.service
deploy/systemd/linuxone-rag-worker.service   # optional later
deploy/systemd/linuxone-rag-nginx-notes.md   # optional docs
```

### Why this matters
A real hosted system should not rely on manually open terminals for:
- frontend runtime
- backend runtime
- tunnel-only access

---

## 4.3 Add Nginx deployment config to repo

### Suggested file
```text
deploy/nginx/linuxone-rag.conf
```

### This config should support
- static frontend hosting
- reverse-proxy backend `/api`
- browser refresh support for SPA routes
- future TLS support

---

# 5) Frontend/Backend Integration Changes

These changes are needed to ensure the real hosted system behaves properly.

---

## 5.1 Validate frontend response shape against the real backend

### Current issue
The frontend currently calls:
- `/query`
- `/documents`
- `/statistics`
- `/health`

through `frontend/src/services/api.js`

### Required change
The real backend must return the exact response structure the frontend expects.

If the frontend expects fields such as:
- `answer`
- `sources`
- `retrieved_chunks`
- `response_time_ms`
- `model`
- `timestamp`

then the real backend must keep this contract stable.

### Files likely to verify/modify
```text
frontend/src/services/api.js
frontend/src/App.jsx
backend/app/api/routes.py
backend/app/models/schemas.py
```

---

## 5.2 Add user-visible error handling in the frontend

### Why this matters
A real hosted system should handle:
- backend unavailable
- timeout
- malformed response
- external LLM failure
- retrieval failure

### Suggested frontend changes
Add robust handling for:
- loading state
- error state
- retry state
- “backend unavailable” messaging

### Files likely to modify
```text
frontend/src/App.jsx
frontend/src/services/api.js
```

---

# 6) Recommended LinuxONE-Friendly Dependency Strategy

This section describes the runtime plan so you don’t keep getting blocked by architecture-specific packages when only the hosted runtime is needed.

---

## 6.1 Base runtime install path (hosted system now)

The real hosted LinuxONE runtime should be able to install and run with **base runtime dependencies only**.

This means the hosted runtime should not require these packages just to boot:
- `torch`
- `sentence-transformers`
- `transformers`
- `PyMuPDF`
- `tiktoken`

Those should move behind feature flags, lazy imports, or a later install stage.

---

## 6.2 Optional AI enablement path (later)

When you revisit LinuxONE-native AI enablement, that should be treated as a separate track.

This likely includes optional environment/toolchain packages such as:
- Rust / Cargo for `tiktoken`
- Clang / `libclang` for `PyMuPDF`
- LinuxONE-compatible package or source-build strategy for PyTorch/transformer dependencies

This should not block the hosted runtime milestone.

---

# 7) Implementation Sequence (Code-Focused)

Use this order to avoid rework.

---

## Phase 1 — Fix the codebase so the real backend can boot
1. Restore/rebuild `backend/app/models/`
2. Make imports valid again
3. Split requirements
4. Move optional AI/PDF/tokenizer imports behind lazy loading
5. Ensure backend health endpoint and root endpoint work

---

## Phase 2 — Stabilize the real hosted runtime
1. Switch frontend API base URL to env-driven
2. Build frontend for production
3. Add Nginx config
4. Add backend service definition
5. Add `.env.production` guidance

---

## Phase 3 — Reintroduce the real query pipeline on LinuxONE runtime
1. Restore DB layer and schemas
2. Restore/query retrieval flow
3. Integrate external LLM provider path
4. Validate `/api/query` end-to-end with real frontend

---

## Phase 4 — LinuxONE-native AI expansion later
1. Re-enable local query embeddings if desired
2. Re-enable corpus embedding generation if desired
3. Re-enable tokenizer/PDF paths if desired
4. Explore local model hosting path later

---

# 8) Summary of Concrete File-Level Changes

Below is the most actionable file list.

---

## Must add or restore
```text
backend/app/models/__init__.py
backend/app/models/db_connection.py
backend/app/models/database.py
backend/app/models/schemas.py
backend/requirements-base.txt
backend/requirements-ai.txt
backend/requirements-dev.txt             # optional but recommended
deploy/nginx/linuxone-rag.conf
deploy/systemd/linuxone-rag-backend.service
.env.production.example
LINUXONE_HOSTING.md
backend/scripts/import_precomputed_corpus.py   # if using precomputed corpus import
```

---

## Must modify
```text
backend/app/main.py
backend/app/api/routes.py
backend/app/config.py
backend/app/services/llm_service.py
backend/app/services/retrieval_service.py
backend/app/services/document_processor.py
backend/app/services/embedding_service.py
backend/app/services/reranking_service.py
backend/app/utils/chunking.py
frontend/src/services/api.js
frontend/src/App.jsx                      # likely for error/loading handling
README.md                                # deployment instructions should be updated
```

---

## Likely remove or stop relying on for hosted runtime startup
```text
single monolithic backend/requirements.txt as the only deployment dependency file
hardcoded localhost API base URL in frontend
unconditional imports of torch/fitz/tiktoken/sentence-transformers at module import time
manual Vite dev server as the production hosting strategy
manual uvicorn terminal session as the production backend hosting strategy
```

---

# 9) Final Recommendation

The correct path is **not** to keep the current temporary demo backend forever, but also **not** to force every AI dependency onto LinuxONE immediately.

The right path is:
- repair the actual backend code structure first
- turn the frontend + backend + reverse proxy into a real hosted runtime on LinuxONE
- keep external generation for now
- split off harder LinuxONE-native AI dependencies into a second-stage enablement track

That way, every step you take now still belongs to the final architecture.

---

# Questions That Need Answers Before Finalizing the Hosted Build Path

Please answer these before we lock the implementation plan:

1. **Do you want PostgreSQL + pgvector on this same LinuxONE VM, on a separate DB host, or not in the first hosted version?**
   - same VM
   - separate DB
   - not in first hosted version

2. **Is using an external LLM API acceptable for the real hosted system right now?**
   - yes, external API is fine
   - no, generation must be local

3. **Do you have the missing backend files anywhere?** Specifically:
   - `backend/app/models/db_connection.py`
   - `backend/app/models/database.py`
   - `backend/app/models/schemas.py`

   Answer:
   - yes, I have them
   - no, I do not
   - not sure

4. **Is the repository public or private?**
   This changes the recommended deployment/update workflow.

5. **Do you want the app exposed publicly by URL now, or is private/tunneled access acceptable for the first real hosted pass?**
   - public URL
   - private/tunnel first
