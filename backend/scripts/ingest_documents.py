#!/usr/bin/env python3
"""
Document ingestion script for the RAG pipeline.
Processes PDF files, chunks text, generates embeddings, and stores in database.
"""

import sys
import os
from pathlib import Path
import logging
from typing import List
import argparse

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
from app.models.database import Document, Chunk
from app.models.db_connection import SessionLocal, init_db
from app.services.document_processor import DocumentProcessor
from app.services.embedding_service import get_embedding_service
from app.utils.chunking import TextChunker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def ingest_document(
    file_path: str,
    doc_processor: DocumentProcessor,
    chunker: TextChunker,
    embedding_service,
    db_session
) -> bool:
    """
    Ingest a single document into the database.
    
    Args:
        file_path: Path to the PDF file
        doc_processor: Document processor instance
        chunker: Text chunker instance
        embedding_service: Embedding service instance
        db_session: Database session
        
    Returns:
        True if successful, False otherwise
    """
    try:
        filename = Path(file_path).name
        logger.info(f"Processing document: {filename}")
        
        # Check if document already exists
        existing_doc = db_session.query(Document).filter(
            Document.filename == filename
        ).first()
        
        if existing_doc:
            logger.warning(f"Document {filename} already exists. Skipping.")
            return False
        
        # Load and process PDF
        logger.info("Extracting text from PDF...")
        pdf_data = doc_processor.load_pdf(file_path)
        
        # Combine all pages
        full_text = "\n\n".join([page['content'] for page in pdf_data['pages']])
        
        # Extract topics
        logger.info("Extracting topics...")
        topics = doc_processor.extract_topics(full_text)
        main_topic = topics[0] if topics else 'general'
        
        # Create document record
        doc = Document(
            filename=filename,
            title=pdf_data['metadata']['title'],
            source_type='redbook',
            total_pages=pdf_data['metadata']['total_pages'],
            doc_metadata={
                'author': pdf_data['metadata'].get('author', ''),
                'subject': pdf_data['metadata'].get('subject', ''),
                'topics': topics
            }
        )
        db_session.add(doc)
        db_session.flush()  # Get document ID
        
        logger.info(f"Created document record with ID: {doc.id}")
        
        # Process each page
        all_chunks = []
        for page in pdf_data['pages']:
            page_num = page['page_number']
            page_text = doc_processor.clean_text(page['content'])
            
            if not page_text.strip():
                continue
            
            # Extract sections from page
            sections = doc_processor.extract_sections(page_text)
            
            for section in sections:
                section_title = section['title']
                section_content = section['content']
                
                if not section_content.strip():
                    continue
                
                # Chunk the section content
                chunks = chunker.chunk_text(
                    section_content,
                    metadata={
                        'page_number': page_num,
                        'section': section_title,
                        'topic': main_topic
                    }
                )
                
                all_chunks.extend(chunks)
        
        logger.info(f"Created {len(all_chunks)} chunks")
        
        # Generate embeddings in batches
        logger.info("Generating embeddings...")
        chunk_texts = [chunk['content'] for chunk in all_chunks]
        embeddings = embedding_service.embed_batch(chunk_texts, batch_size=32)
        
        # Create chunk records
        logger.info("Storing chunks in database...")
        for i, (chunk_data, embedding) in enumerate(zip(all_chunks, embeddings)):
            chunk = Chunk(
                document_id=doc.id,
                chunk_index=i,
                content=chunk_data['content'],
                embedding=embedding,
                token_count=chunk_data.get('token_count', 0),
                page_number=chunk_data.get('page_number'),
                section=chunk_data.get('section'),
                topic=chunk_data.get('topic'),
                chunk_metadata={}
            )
            db_session.add(chunk)
        
        # Update document with total chunks
        doc.total_chunks = len(all_chunks)
        
        # Commit transaction
        db_session.commit()
        
        logger.info(f"Successfully ingested {filename}")
        logger.info(f"  - Pages: {doc.total_pages}")
        logger.info(f"  - Chunks: {doc.total_chunks}")
        logger.info(f"  - Topics: {', '.join(topics)}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error ingesting document {file_path}: {e}")
        db_session.rollback()
        return False


def ingest_directory(directory: str, pattern: str = "*.pdf"):
    """
    Ingest all PDF files from a directory.
    
    Args:
        directory: Path to directory containing PDFs
        pattern: File pattern to match (default: *.pdf)
    """
    settings = get_settings()
    
    # Initialize database
    logger.info("Initializing database...")
    init_db()
    
    # Initialize services
    logger.info("Loading embedding model...")
    embedding_service = get_embedding_service(settings.embedding_model)
    
    doc_processor = DocumentProcessor()
    chunker = TextChunker(
        chunk_size=settings.chunk_size,
        overlap=settings.chunk_overlap
    )
    
    # Find PDF files
    pdf_dir = Path(directory)
    pdf_files = list(pdf_dir.glob(pattern))
    
    if not pdf_files:
        logger.warning(f"No PDF files found in {directory}")
        return
    
    logger.info(f"Found {len(pdf_files)} PDF files to process")
    
    # Process each file
    success_count = 0
    db_session = SessionLocal()
    
    try:
        for pdf_file in pdf_files:
            if ingest_document(
                str(pdf_file),
                doc_processor,
                chunker,
                embedding_service,
                db_session
            ):
                success_count += 1
    finally:
        db_session.close()
    
    logger.info(f"\nIngestion complete!")
    logger.info(f"Successfully processed: {success_count}/{len(pdf_files)} documents")


def main():
    """Main entry point for the ingestion script."""
    parser = argparse.ArgumentParser(
        description="Ingest PDF documents into the RAG knowledge base"
    )
    parser.add_argument(
        '--input',
        type=str,
        default='data/redbooks',
        help='Input directory or file path (default: data/redbooks)'
    )
    parser.add_argument(
        '--pattern',
        type=str,
        default='*.pdf',
        help='File pattern to match (default: *.pdf)'
    )
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    
    if input_path.is_file():
        # Single file
        logger.info(f"Processing single file: {input_path}")
        settings = get_settings()
        init_db()
        
        embedding_service = get_embedding_service(settings.embedding_model)
        doc_processor = DocumentProcessor()
        chunker = TextChunker(
            chunk_size=settings.chunk_size,
            overlap=settings.chunk_overlap
        )
        
        db_session = SessionLocal()
        try:
            ingest_document(
                str(input_path),
                doc_processor,
                chunker,
                embedding_service,
                db_session
            )
        finally:
            db_session.close()
    
    elif input_path.is_dir():
        # Directory
        ingest_directory(str(input_path), args.pattern)
    
    else:
        logger.error(f"Invalid input path: {input_path}")
        sys.exit(1)


if __name__ == "__main__":
    main()

# Made with Bob
