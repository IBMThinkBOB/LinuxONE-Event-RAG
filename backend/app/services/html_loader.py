"""
HTML document loader for IBM MQ documentation.
Fetches pages by URL or reads local HTML files, extracts clean prose via
trafilatura, and splits content on heading boundaries to produce semantic
sections — one section per page entry, matching DocumentProcessor.load_pdf()'s
return shape.
"""

import re
import logging
from pathlib import Path
from typing import Dict, List, Optional

import trafilatura

logger = logging.getLogger(__name__)

# IBM MQ-specific keyword vocabulary for topic extraction
_MQ_KEYWORDS = {
    'mq', 'ibm mq', 'queue manager', 'channel', 'listener',
    'cluster', 'message broker', 'topic', 'subscription',
    'failover', 'tls', 'security', 'authentication',
    'runmqsc', 'mq explorer', 'messaging', 'queue',
    'broker', 'dead letter', 'transmission queue', 'amqp',
    'mqsc', 'strmqm', 'endmqm', 'crtmqm',
}

# Regex that matches Markdown-style headings produced by trafilatura
# Matches lines like:  # Heading   ## Heading   ### Heading   #### Heading
_HEADING_RE = re.compile(r'^(#{1,4})\s+(.+)$', re.MULTILINE)


class HTMLLoader:
    """Load IBM MQ HTML documentation and split by headings into semantic sections."""

    def load_url(self, url: str) -> Dict:
        """
        Fetch a URL and return its content split into heading-based sections.

        Args:
            url: Fully-qualified HTTP/HTTPS URL to fetch.

        Returns:
            Dict with keys 'pages' and 'metadata', matching DocumentProcessor.load_pdf().
        """
        logger.info(f"Fetching URL: {url}")
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            logger.warning(f"trafilatura could not fetch: {url}")
            return self._build_result([], url, url)

        text = trafilatura.extract(downloaded, include_formatting=True)
        if not text:
            logger.warning(f"trafilatura extracted no text from: {url}")
            return self._build_result([], url, url)

        title = self._extract_title(text) or url
        sections = self._split_by_headings(text)
        return self._build_result(sections, title, url)

    def load_file(self, file_path: str) -> Dict:
        """
        Load a local HTML file and return its content split into heading-based sections.

        Args:
            file_path: Path to the local .html file.

        Returns:
            Dict with keys 'pages' and 'metadata', matching DocumentProcessor.load_pdf().
        """
        logger.info(f"Loading local file: {file_path}")
        raw_bytes = Path(file_path).read_bytes()
        text = trafilatura.extract(raw_bytes.decode('utf-8', errors='replace'),
                                   include_formatting=True)
        if not text:
            logger.warning(f"trafilatura extracted no text from: {file_path}")
            return self._build_result([], Path(file_path).name, file_path)

        title = self._extract_title(text) or Path(file_path).stem
        sections = self._split_by_headings(text)
        return self._build_result(sections, title, file_path)

    # ── Private helpers ──────────────────────────────────────────────────────

    def _split_by_headings(self, text: str) -> List[Dict]:
        """
        Split trafilatura-extracted text on Markdown-style heading lines.
        Each heading + its following body text becomes one section entry.

        Returns:
            List of dicts: {section_index, section_title, content}
        """
        # Find all heading positions
        matches = list(_HEADING_RE.finditer(text))

        if not matches:
            # No headings — return entire text as a single section
            body = text.strip()
            if body:
                return [{'section_index': 0, 'section_title': 'Main Content', 'content': body}]
            return []

        sections = []
        for i, match in enumerate(matches):
            heading_text = match.group(2).strip()
            body_start = match.end()
            body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            body = text[body_start:body_end].strip()

            # Skip heading-only entries with no body
            if not body:
                continue

            sections.append({
                'section_index': len(sections),
                'section_title': heading_text,
                'content': body,
            })

        # Capture any text that appears before the first heading
        preamble = text[:matches[0].start()].strip()
        if preamble:
            sections.insert(0, {
                'section_index': 0,
                'section_title': 'Introduction',
                'content': preamble,
            })
            # Re-index
            for idx, s in enumerate(sections):
                s['section_index'] = idx

        return sections

    def _extract_title(self, text: str) -> Optional[str]:
        """Return the text of the first h1 heading, or None."""
        m = re.search(r'^#\s+(.+)$', text, re.MULTILINE)
        return m.group(1).strip() if m else None

    def _build_result(self, sections: List[Dict], title: str, source_hint: str) -> Dict:
        """Assemble the standard return dict consumed by the ingestion script."""
        full_text = ' '.join(s['content'] for s in sections)
        topics = self.extract_topics(full_text)

        # Map sections → pages list, using section_index as page_number
        pages = [
            {
                'page_number': s['section_index'],
                'section_title': s['section_title'],
                'content': s['content'],
            }
            for s in sections
        ]

        return {
            'pages': pages,
            'metadata': {
                'filename': source_hint,
                'title': title,
                'total_pages': len(pages),
                'source_type': 'ibm_mq',
                'topics': topics,
            },
        }

    def extract_topics(self, text: str, max_topics: int = 5) -> List[str]:
        """
        Extract IBM MQ-specific topic keywords by frequency.

        Args:
            text: Full document text.
            max_topics: Maximum number of topics to return.

        Returns:
            List of keyword strings, highest frequency first.
        """
        text_lower = text.lower()
        counts = {kw: text_lower.count(kw) for kw in _MQ_KEYWORDS if text_lower.count(kw) > 0}
        sorted_kws = sorted(counts, key=counts.get, reverse=True)
        return sorted_kws[:max_topics] if sorted_kws else ['ibm mq']

# Made with Bob
