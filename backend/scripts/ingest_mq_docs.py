#!/usr/bin/env python3
"""
IBM MQ documentation ingestion script.
Ingests IBM MQ HTML pages (by URL list or local files) into the RAG knowledge base.

Primary mode   — URL list file:
    python backend/scripts/ingest_mq_docs.py --sources data/mq_docs/sources.txt

Secondary mode — local HTML directory:
    python backend/scripts/ingest_mq_docs.py --input data/mq_docs --pattern "*.html"

Single file:
    python backend/scripts/ingest_mq_docs.py --input data/mq_docs/install.html
"""

import sys
import logging
import argparse
from pathlib import Path
from typing import Optional

# Ensure the backend package is importable when run as a script
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
from app.models.database import Document, Chunk
from app.models.db_connection import SessionLocal, init_db
from app.services.html_loader import HTMLLoader
from app.services.gui_normalizer import GUINormalizer
from app.services.metadata_enricher import MetadataEnricher
from app.services.embedding_service import get_embedding_service
from app.utils.chunking import TextChunker

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


def ingest_mq_document(
    source: str,
    loader: HTMLLoader,
    normalizer: GUINormalizer,
    enricher: MetadataEnricher,
    chunker: TextChunker,
    embedding_service,
    db_session,
) -> bool:
    """
    Ingest a single IBM MQ documentation source (URL or local file path).

    Flow:
        load → per-section GUI normalisation → chunk → embed
        → enrich metadata → store Document + Chunks

    Args:
        source:            URL string or absolute/relative local file path.
        loader:            HTMLLoader instance.
        normalizer:        GUINormalizer instance.
        enricher:          MetadataEnricher instance.
        chunker:           TextChunker instance.
        embedding_service: EmbeddingService instance.
        db_session:        Active SQLAlchemy session.

    Returns:
        True on success, False on failure.
    """
    try:
        is_url = source.startswith('http://') or source.startswith('https://')
        identifier = source  # used for duplicate-check and logging

        logger.info(f"Processing: {identifier}")

        # ── Duplicate check ───────────────────────────────────────────────────
        existing = db_session.query(Document).filter(
            Document.filename == identifier
        ).first()
        if existing:
            logger.warning(f"Already ingested: {identifier} — skipping.")
            return False

        # ── Load & extract ────────────────────────────────────────────────────
        if is_url:
            doc_data = loader.load_url(source)
        else:
            doc_data = loader.load_file(source)

        pages = doc_data['pages']
        meta = doc_data['metadata']

        if not pages:
            logger.warning(f"No content extracted from: {identifier}")
            return False

        topics = meta.get('topics', [])
        main_topic = topics[0] if topics else 'ibm mq'

        # ── Create Document record ────────────────────────────────────────────
        doc = Document(
            filename=identifier,
            title=meta.get('title', identifier),
            source_type='ibm_mq',
            total_pages=meta.get('total_pages', len(pages)),
            doc_metadata={
                'topics': topics,
                'source_url': source if is_url else None,
            },
        )
        db_session.add(doc)
        db_session.flush()  # obtain doc.id before inserting chunks

        logger.info(f"Created document record id={doc.id}: {doc.title}")

        # ── Per-section: normalise → chunk → accumulate ───────────────────────
        all_chunks = []

        for page in pages:
            section_title = page.get('section_title', 'Main Content')
            page_num = page.get('page_number', 0)

            # GUI normalisation — replaces content in-place when detected
            normalised_page = normalizer.normalize_section(page)
            content = normalised_page.get('content', '').strip()

            if not content:
                continue

            chunks = chunker.chunk_text(
                content,
                metadata={
                    'page_number': page_num,
                    'section': section_title,
                    'topic': main_topic,
                },
            )
            all_chunks.extend(chunks)

        logger.info(f"Created {len(all_chunks)} chunks from {len(pages)} sections")

        if not all_chunks:
            logger.warning(f"No chunks produced for: {identifier}")
            db_session.rollback()
            return False

        # ── Embed all chunks in one batch ─────────────────────────────────────
        logger.info("Generating embeddings...")
        chunk_texts = [c['content'] for c in all_chunks]
        embeddings = embedding_service.embed_batch(chunk_texts, batch_size=32)

        # ── Store Chunk records ───────────────────────────────────────────────
        logger.info("Storing chunks in database...")
        for i, (chunk_data, embedding) in enumerate(zip(all_chunks, embeddings)):
            enriched_meta = enricher.enrich_chunk(chunk_data['content'], meta)

            chunk = Chunk(
                document_id=doc.id,
                chunk_index=i,
                content=chunk_data['content'],
                embedding=embedding,
                token_count=chunk_data.get('token_count', 0),
                page_number=chunk_data.get('page_number'),
                section=chunk_data.get('section'),
                topic=chunk_data.get('topic'),
                chunk_metadata=enriched_meta,
            )
            db_session.add(chunk)

        doc.total_chunks = len(all_chunks)
        db_session.commit()

        logger.info(f"Successfully ingested: {identifier}")
        logger.info(f"  - Sections : {len(pages)}")
        logger.info(f"  - Chunks   : {doc.total_chunks}")
        logger.info(f"  - Topics   : {', '.join(topics)}")

        return True

    except Exception as e:
        logger.error(f"Error ingesting {source}: {e}")
        db_session.rollback()
        return False


def ingest_from_sources_file(sources_file: str) -> None:
    """
    Primary ingestion mode: read a URL list file and ingest each URL.
    Lines starting with '#' and blank lines are skipped.

    Args:
        sources_file: Path to sources.txt (one URL per non-comment line).
    """
    sources_path = Path(sources_file)
    if not sources_path.is_file():
        logger.error(f"Sources file not found: {sources_file}")
        return

    urls = [
        line.strip()
        for line in sources_path.read_text(encoding='utf-8').splitlines()
        if line.strip() and not line.strip().startswith('#')
    ]

    if not urls:
        logger.warning(f"No URLs found in: {sources_file}")
        return

    logger.info(f"Found {len(urls)} URLs to ingest from {sources_file}")
    _run_ingestion(urls)


def ingest_directory(directory: str, pattern: str = '*.html') -> None:
    """
    Secondary ingestion mode: ingest all matching HTML files in a directory.

    Args:
        directory: Path to the directory containing HTML files.
        pattern:   Glob pattern (default '*.html').
    """
    html_dir = Path(directory)
    files = list(html_dir.glob(pattern))

    if not files:
        logger.warning(f"No files matching '{pattern}' found in {directory}")
        return

    logger.info(f"Found {len(files)} files to process in {directory}")
    _run_ingestion([str(f) for f in files])


def _run_ingestion(sources: list) -> None:
    """Shared ingestion loop used by both ingestion modes."""
    settings = get_settings()

    logger.info("Initialising database...")
    init_db()

    logger.info("Loading embedding model...")
    embedding_service = get_embedding_service(settings.embedding_model)

    loader = HTMLLoader()
    normalizer = GUINormalizer()
    enricher = MetadataEnricher()
    chunker = TextChunker(
        chunk_size=settings.chunk_size,
        overlap=settings.chunk_overlap,
    )

    success_count = 0
    db_session = SessionLocal()

    try:
        for source in sources:
            if ingest_mq_document(
                source, loader, normalizer, enricher,
                chunker, embedding_service, db_session,
            ):
                success_count += 1
    finally:
        db_session.close()

    logger.info(f"\nIngestion complete!")
    logger.info(f"Successfully processed: {success_count}/{len(sources)} sources")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Ingest IBM MQ documentation into the RAG knowledge base'
    )

    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        '--sources',
        type=str,
        help='Path to a URL list file (one URL per line, # for comments). '
             'Example: data/mq_docs/sources.txt',
    )
    source_group.add_argument(
        '--input',
        type=str,
        help='Path to a local HTML file or directory of HTML files.',
    )

    parser.add_argument(
        '--pattern',
        type=str,
        default='*.html',
        help='File glob pattern when --input is a directory (default: *.html)',
    )

    args = parser.parse_args()

    if args.sources:
        ingest_from_sources_file(args.sources)

    elif args.input:
        input_path = Path(args.input)
        if input_path.is_file():
            logger.info(f"Processing single file: {input_path}")
            settings = get_settings()
            init_db()
            embedding_service = get_embedding_service(settings.embedding_model)
            db_session = SessionLocal()
            try:
                ingest_mq_document(
                    str(input_path),
                    HTMLLoader(),
                    GUINormalizer(),
                    MetadataEnricher(),
                    TextChunker(
                        chunk_size=settings.chunk_size,
                        overlap=settings.chunk_overlap,
                    ),
                    embedding_service,
                    db_session,
                )
            finally:
                db_session.close()

        elif input_path.is_dir():
            ingest_directory(str(input_path), args.pattern)

        else:
            logger.error(f"Invalid --input path: {input_path}")
            sys.exit(1)


if __name__ == '__main__':
    main()

# Made with Bob
