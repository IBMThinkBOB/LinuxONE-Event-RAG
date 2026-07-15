# IBM MQ Knowledge Ingestion — Plan

## Top-Level Overview

The system currently ingests IBM Redbook PDFs as its sole source type.  
This plan extends it to ingest IBM MQ documentation from **HTML pages** (IBM Docs, tutorials,
download pages) fetched by URL, plus optional local `.html` files, producing semantically-structured
chunks stored under `source_type = "ibm_mq"`.

**Confirmed decisions:**
- Primary ingestion mode: URL list (fetch live pages); local `.html` files are a secondary fallback
- Chunking strategy: **heading-based semantic chunking** (split on `<h1>`–`<h4>` / markdown `#`–`####` boundaries extracted by trafilatura), not fixed-token or sentence-only
- Sub-Tasks 5 & 6 (query classification + keyword vocab) are in scope

**No IBM MQ source files exist in the repo today** — only 5 Redbook PDFs under `data/redbooks/`.  
A URL seed list file is therefore part of this plan (Sub-Task 0).

All new code follows established pipeline conventions:
- Loaders → `backend/app/services/`
- Utilities → `backend/app/utils/`
- Ingestion scripts → `backend/scripts/`
- Same `Document` + `Chunk` ORM schema (no DB migrations needed)
- Same 384-dim `all-MiniLM-L6-v2` embeddings throughout
- Retrieval, reranking, and LLM paths require **zero changes**

---

## Sub-Tasks

---

### Sub-Task 0 — IBM MQ URL Seed List, Data Directory & New Redbooks

**Intent**
Commit the 9 confirmed IBM MQ documentation URLs into a structured seed file, create the
`data/mq_docs/` drop directory, and note the 4 newly added MQ Redbooks so the existing PDF
ingestion script covers them too. The seed file drives the primary ingestion mode.

**URL analysis (IBM Docs URL convention):**

| # | URL | Version | Slug decoded | Expected type | GUI? |
|---|-----|---------|-------------|---------------|------|
| 1 | `...10.0.x?topic=migrating-installing-uninstalling` | 10.0 | Install/uninstall workflow | procedure | No |
| 2 | `...10.0.x?topic=information-mq-downloads` | 10.0 | Download page | procedure | No |
| 3 | `...9.3.x?topic=explorer-mq-tutorials` | 9.3 | MQ Explorer tutorials | procedure | **Yes** |
| 4 | `developer.ibm.com/components/ibm-mq/tutorials/` | N/A | IBM Developer tutorial hub | concept | No |
| 5 | `...10.0.x?topic=scenarios-getting-started-mq` | 10.0 | Getting started scenarios | procedure | No |
| 6 | `...9.4.x?topic=mq-explorer` | 9.4 | MQ Explorer overview | concept | **Yes** |
| 7 | `...9.3.x?topic=explorer-configuring-mq` | 9.3 | Configuring MQ via Explorer | procedure | **Yes** |
| 8 | `...9.4.x?topic=mq-94-quick-start-guide` | 9.4 | 9.4 Quick Start guide | procedure | No |
| 9 | `ibm.com/docs/en/ibm-mq` | N/A | Product docs landing page | concept | No |

URLs 3, 6, 7 are MQ Explorer (GUI) pages — `GUINormalizer` will detect and normalise these sections.
URLs 1, 2, 5, 7, 8 are install/configure/quickstart — `"procedure"` type.
URLs 4, 9 are index/hub pages — `"concept"` type, fewer chunks expected.

**New Redbooks (already in `data/redbooks/`):**
- `IntroToMQRedbook.pdf`
- `IntegratingMQRedbook.pdf`
- `MQApplianceSolutionRedbook.pdf`
- `MQAsAServiceRedbook.pdf`

These are ingested by the **existing** `ingest_documents.py` script unchanged. Sub-Task 6 (MQ keywords) ensures they get correctly tagged topics when run.

**Expected Outcomes**
- `data/mq_docs/` directory exists with a `.gitkeep`
- `data/mq_docs/sources.txt` exists with all 9 URLs, grouped by category with `#` comment headers and per-URL version annotations

**Todo List**
1. Create `data/mq_docs/` directory with `.gitkeep`
2. Create `data/mq_docs/sources.txt` with the exact 9 URLs provided, organised under comment headers:
   - `# Installation & Downloads` → URLs 1, 2
   - `# Getting Started` → URLs 5, 8
   - `# GUI / MQ Explorer` → URLs 3, 6, 7
   - `# Tutorials` → URLs 4
   - `# Documentation Root` → URL 9

**Relevant Context**
- `IBM_MQ_RAG_Ingestion_Guide.md §8 Outcome` — topic areas the system must support
- The ingestion script (Sub-Task 4) reads this file with `--sources data/mq_docs/sources.txt`
- The 4 new Redbooks in `data/redbooks/` are handled by the existing `ingest_documents.py` — no changes needed to that script

**Status** — `[x] done`

---

### Sub-Task 1 — HTML Loader (`backend/app/services/html_loader.py`)

**Intent**  
Create a loader that fetches IBM MQ HTML pages by URL (or reads local `.html` files) and returns
the same `{pages, metadata}` dictionary shape as `DocumentProcessor.load_pdf()`, so the rest of
the pipeline is unchanged. Heading-based section splitting happens here — each `<h1>`–`<h4>` block
becomes one "page" entry, giving the semantic chunk boundaries the guide requires.

**Expected Outcomes**
- `backend/app/services/html_loader.py` exists
- `HTMLLoader.load_url(url)` fetches a page with `trafilatura.fetch_url` + `trafilatura.extract`, then splits by headings
- `HTMLLoader.load_file(file_path)` does the same from a local `.html` file
- `HTMLLoader.extract_topics(text)` returns IBM MQ-specific keywords
- Each heading-delimited block is returned as a separate entry in the `pages` list (with `page_number` = section index, `section_title` = heading text, `content` = body text)
- Return shape: `{pages: [{page_number, section_title, content}], metadata: {filename/url, title, total_pages, source_type: "ibm_mq", topics}}`
- `trafilatura` added to `backend/requirements.txt`

**Todo List**
1. Create `backend/app/services/html_loader.py`
2. Add `HTMLLoader` class
3. Implement `load_url(url)` — `trafilatura.fetch_url` → `trafilatura.extract` → `_split_by_headings()`
4. Implement `load_file(file_path)` — read file bytes → `trafilatura.extract` → `_split_by_headings()`
5. Implement `_split_by_headings(text)` — regex split on Markdown-style `# Heading` patterns that `trafilatura` outputs; each block becomes one page entry with `section_title` and `content`
6. Implement `extract_topics(text)` with IBM MQ keyword vocabulary: `mq`, `ibm mq`, `queue manager`, `channel`, `listener`, `cluster`, `message broker`, `topic`, `subscription`, `failover`, `tls`, `security`, `authentication`, `runmqsc`, `mq explorer`
7. Implement `_build_result(sections, title, source_hint)` to assemble the final dict
8. Add `trafilatura` (no pinned version) to `backend/requirements.txt`

**Relevant Context**
- Mirror return shape of: `backend/app/services/document_processor.py` `load_pdf()` (lines 13–48)
- Guide reference: `IBM_MQ_RAG_Ingestion_Guide.md §3` — trafilatura usage
- Each `pages` entry here maps to a whole semantic section, not a PDF page; `page_number` is just the section index

**Status** — `[x] done`

---

### Sub-Task 2 — GUI Normalizer (`backend/app/services/gui_normalizer.py`)

**Intent**  
Some IBM MQ documentation describes tasks using GUI navigation prose ("Open MQ Explorer →
Right-click Queue Managers → New → Queue Manager"). This normalizer detects such text and converts
it to numbered plain-text steps so it embeds cleanly and retrieves correctly for GUI-workflow queries.

**Expected Outcomes**
- `backend/app/services/gui_normalizer.py` exists
- `GUINormalizer.is_gui_text(text)` returns `True` when the text contains GUI signals
- `GUINormalizer.normalize(text)` returns a numbered plain-text step string
- `GUINormalizer.normalize_section(section_dict)` operates on a `{section_title, content}` dict and returns the same shape with content replaced if GUI detected

**Todo List**
1. Create `backend/app/services/gui_normalizer.py`
2. Add `GUINormalizer` class
3. Implement `is_gui_text(text)` — return `True` if 2+ of these signals appear: `→`, `>`, `Click`, `Open`, `Select`, `Right-click`, `checkbox`, `dropdown`, `button`, `menu`, `MQ Explorer`
4. Implement `normalize(text)` — split on `→` and `>` delimiters and numbered patterns; strip whitespace; prefix each item with `Step N:` ; join with newlines
5. Implement `normalize_section(section_dict)` — call `is_gui_text(content)`, if true replace content with `normalize(content)`, return updated dict unchanged otherwise

**Relevant Context**
- Guide reference: `IBM_MQ_RAG_Ingestion_Guide.md §4 GUI Normalization`
- Output feeds directly into `TextChunker.chunk_text()` in the ingestion script (Sub-Task 4)

**Status** — `[x] done`

---

### Sub-Task 3 — Metadata Enricher (`backend/app/services/metadata_enricher.py`)

**Intent**  
Produce IBM MQ-specific chunk metadata (content type, platform, interface, keywords) to populate
`Chunk.chunk_metadata`. This enables future filtered retrieval by type, platform, or interface
without any changes to the retrieval service.

**Expected Outcomes**
- `backend/app/services/metadata_enricher.py` exists
- `MetadataEnricher.enrich_chunk(content, doc_meta)` returns a dict matching the guide's schema:
  `{title, type, platform, interface, source, keywords, content, embedding: []}`
- `MetadataEnricher.classify_content_type(text)` returns `"procedure"`, `"troubleshooting"`, or `"concept"`
- `MetadataEnricher.extract_platform(text)` returns a list from `["Linux", "Windows", "z/OS", "AIX"]`
- `MetadataEnricher.extract_interface(text)` returns a list from `["CLI", "GUI", "API"]`

**Todo List**
1. Create `backend/app/services/metadata_enricher.py`
2. Add `MetadataEnricher` class
3. Implement `classify_content_type(text)` — keyword match: (`install`, `configure`, `step`, `create`, `enable`, `run`) → `"procedure"`; (`error`, `fail`, `troubleshoot`, `cannot`, `reason`, `resolve`) → `"troubleshooting"`; else → `"concept"`
4. Implement `extract_platform(text)` — case-insensitive scan for `linux`, `windows`, `z/os`, `aix`
5. Implement `extract_interface(text)` — scan for (`cli`, `command line`, `terminal`, `runmqsc`) → CLI; (`gui`, `explorer`, `click`, `mq explorer`) → GUI; (`api`, `rest`, `http`, `amqp`) → API
6. Implement `enrich_chunk(content, doc_meta)` combining the above plus pulling `title` and `source` from `doc_meta`

**Relevant Context**
- Guide reference: `IBM_MQ_RAG_Ingestion_Guide.md §5 Metadata Schema` — exact JSON shape
- Guide reference: `IBM_MQ_RAG_Ingestion_Guide.md §6 Query Classification` — basis for `classify_content_type`
- `Chunk.chunk_metadata` is already a JSON column in `backend/app/models/database.py`

**Status** — `[x] done`

---

### Sub-Task 4 — IBM MQ Ingestion Script (`backend/scripts/ingest_mq_docs.py`)

**Intent**  
Wire together HTMLLoader + GUINormalizer + MetadataEnricher with the existing TextChunker and
EmbeddingService into a single runnable ingestion script. Primary mode reads URLs from a sources
file; secondary mode ingests a local `.html` file or directory.

**Expected Outcomes**
- `backend/scripts/ingest_mq_docs.py` is runnable:
  ```
  # Fetch and ingest from URL list (primary mode)
  python backend/scripts/ingest_mq_docs.py --sources data/mq_docs/sources.txt

  # Ingest local HTML files (secondary mode)
  python backend/scripts/ingest_mq_docs.py --input data/mq_docs --pattern "*.html"

  # Single local file
  python backend/scripts/ingest_mq_docs.py --input data/mq_docs/install.html
  ```
- Documents stored with `source_type = "ibm_mq"`
- Chunks stored with `chunk_metadata` populated by `MetadataEnricher`
- GUI sections normalised before chunking
- Duplicate URLs/filenames skipped (same guard as `ingest_documents.py`)
- Logging matches existing format

**Todo List**
1. Create `backend/scripts/ingest_mq_docs.py`
2. Add `ingest_mq_document(source, loader, normalizer, enricher, chunker, embedding_service, db_session)` function — `source` is either a URL string or a local file path; route to `loader.load_url()` or `loader.load_file()` accordingly
3. Follow the exact try/rollback pattern from `ingest_documents.py` `ingest_document()` (lines 32–164)
4. Per section: call `normalizer.normalize_section()`, then `chunker.chunk_text()`, then `enricher.enrich_chunk()` per chunk
5. Store enriched dict in `Chunk.chunk_metadata`
6. Add `ingest_from_sources_file(sources_file)` — read `sources.txt`, skip comment lines (`#`), iterate URLs
7. Add `ingest_directory(directory, pattern)` — mirror existing `ingest_directory()` for local HTML files
8. Add `main()` with argparse: `--sources` (URL list file) and `--input` / `--pattern` (local files); require at least one

**Relevant Context**
- Mirror exactly: `backend/scripts/ingest_documents.py` (full file, lines 1–282)
- `TextChunker` and `EmbeddingService` imported and used identically
- `Document` / `Chunk` from `backend/app/models/database.py` — same ORM, set `source_type = "ibm_mq"`

**Status** — `[x] done`

---

### Sub-Task 5 — IBM MQ Query Classification in `query_utils.py`

**Intent**  
Extend the existing query utilities so that IBM MQ-specific queries get better retrieval through
MQ-aware query expansion, and so the query type (procedure/troubleshooting/concept) is available
for future use.

**Expected Outcomes**
- `classify_mq_query(query)` added to `backend/app/utils/query_utils.py` — returns `"procedure"`, `"troubleshooting"`, or `"concept"`
- `expand_query()` extended: when the query contains MQ signals (`mq`, `queue`, `channel`, `broker`, `message`), append `"ibm mq queue manager channel configuration messaging"` to the expansion

**Todo List**
1. Add `classify_mq_query(query)` to `backend/app/utils/query_utils.py` after the existing functions — keyword heuristics matching guide §6
2. Extend the existing `expand_query()` to check for MQ-related terms and append MQ expansion if detected (in addition to the existing vagueness expansion)

**Relevant Context**
- File to edit: `backend/app/utils/query_utils.py` (all 4 functions, lines 1–70)
- Guide reference: `IBM_MQ_RAG_Ingestion_Guide.md §6 Query Classification`
- No API route changes needed — `routes.py` line 50 already calls `expand_query()`

**Status** — `[x] done`

---

### Sub-Task 6 — Add IBM MQ Keywords to `DocumentProcessor.extract_topics()`

**Intent**  
Minimal backward-compatible extension so that if an IBM MQ Redbook PDF is ingested via the
existing PDF pipeline, MQ-relevant topics are correctly surfaced.

**Expected Outcomes**
- `technical_keywords` set in `DocumentProcessor.extract_topics()` includes:
  `'mq'`, `'ibm mq'`, `'queue manager'`, `'channel'`, `'message broker'`, `'topic'`, `'subscription'`, `'clustering'`, `'high availability'`, `'tls'`

**Todo List**
1. Edit `backend/app/services/document_processor.py` lines 150–158 — add MQ keywords to `technical_keywords` set

**Relevant Context**
- File to edit: `backend/app/services/document_processor.py`, `extract_topics()` method (lines 138–174)
- One-line-per-keyword addition; no logic changes

**Status** — `[x] done`

---

## Implementation Order

```
Sub-Task 0  (URL seed list + data/mq_docs/ dir)
    ↓
Sub-Task 1  (HTMLLoader — fetches + heading-splits pages)
    ↓
Sub-Task 2  (GUINormalizer — normalises GUI sections)
    ↓
Sub-Task 3  (MetadataEnricher — enriches chunk metadata)
    ↓
Sub-Task 4  (Ingestion script — wires 0+1+2+3 together)
    ↓
Sub-Task 5  (Query utils extension)       ← independent
Sub-Task 6  (DocumentProcessor keywords)  ← independent, smallest
```
