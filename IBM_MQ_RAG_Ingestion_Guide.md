# IBM MQ RAG Pipeline – Ingestion & Knowledge Structuring Guide

## 🎯 Objective

Extend the existing RAG pipeline (currently ingesting IBM Redbooks PDFs) into a multi-source, structured IBM MQ knowledge system.

---

## 🧩 1. Source Types & Required Processing Techniques

| Source Type | Ingestion Technique | Notes |
|-------------|--------------------|------|
| Redbooks PDF | pymupdf/pdfplumber | Chunk by section |
| IBM Docs HTML | trafilatura | Remove nav + keep headings |
| Tutorials HTML | trafilatura | Preserve step order |
| GUI docs | normalize to steps | Convert to structured procedure |
| Download pages | HTML parsing | Extract actionable steps |

---

## 🏗️ 2. Repository Changes

Add:

- ingestion/html_loader.py
- ingestion/gui_normalizer.py
- ingestion/metadata_enricher.py

---

## 🔄 3. Ingestion Pipeline

### HTML Loader

Use:

```python
import trafilatura

def extract_main_text(url):
    downloaded = trafilatura.fetch_url(url)
    return trafilatura.extract(downloaded)
```

---

### Chunking Strategy

❌ Avoid fixed chunks

✅ Use semantic chunks:

- Procedure = full task
- Concept = full explanation
- Troubleshooting = one issue

---

### Example Chunk

```json
{
  "title": "Install IBM MQ on Linux",
  "type": "procedure",
  "steps": ["download", "install", "verify"]
}
```

---

## 🧠 4. GUI Normalization

Convert GUI text into steps.

```python
def normalize_gui():
    return {
        "type": "procedure",
        "interface": "GUI",
        "steps": [
            "Open MQ Explorer",
            "Create Queue Manager"
        ]
    }
```

---

## 🧾 5. Metadata Schema

```json
{
  "title": "",
  "type": "procedure",
  "platform": ["Linux"],
  "interface": ["CLI"],
  "source": "IBM Docs",
  "keywords": [],
  "content": "",
  "embedding": []
}
```

---

## 🔍 6. Query Classification

```python
def classify_query(q):
    if "install" in q:
        return "procedure"
    if "error" in q:
        return "troubleshooting"
    return "concept"
```

---

## 🧪 7. Hybrid Retrieval

Combine:

- Embeddings (semantic)
- Keyword search (BM25)

---

## ✅ 8. Outcome

System supports:

- Installation guides
- GUI workflows
- CLI usage
- Troubleshooting
- Architecture

---

## 🚀 End State

Production-grade IBM MQ RAG system.
