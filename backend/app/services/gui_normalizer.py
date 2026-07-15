"""
GUI text normalizer for IBM MQ documentation.
Detects sections described in GUI navigation prose (MQ Explorer click-through
instructions) and converts them to numbered plain-text steps so they embed
and retrieve cleanly.
"""

import re
import logging
from typing import Dict

logger = logging.getLogger(__name__)

# Signals that indicate GUI navigation prose — at least 2 must appear for
# is_gui_text() to return True.
_GUI_SIGNALS = (
    '→', '>', 'click', 'open', 'select', 'right-click', 'checkbox',
    'dropdown', 'button', 'menu', 'mq explorer', 'toolbar', 'panel',
    'dialog', 'wizard', 'tab',
)

# Delimiters used to split a GUI navigation sequence into individual steps
_DELIMITER_RE = re.compile(r'\s*(?:→|>)\s*')

# Matches lines that already start with a number + dot/paren, e.g. "1. Click..."
_NUMBERED_LINE_RE = re.compile(r'^\s*\d+[.)]\s+')


class GUINormalizer:
    """Detect and normalise GUI-described IBM MQ workflow text."""

    def is_gui_text(self, text: str) -> bool:
        """
        Return True when the text looks like GUI navigation prose.
        Requires at least 2 distinct GUI signals to avoid false positives.

        Args:
            text: Section content string.

        Returns:
            True if the text appears to be GUI-navigation prose.
        """
        text_lower = text.lower()
        hits = sum(1 for signal in _GUI_SIGNALS if signal in text_lower)
        return hits >= 2

    def normalize(self, text: str) -> str:
        """
        Convert GUI navigation prose into a numbered plain-text step list.

        Strategy:
        1. Split on arrow/chevron delimiters within each line.
        2. Respect lines that are already numbered.
        3. Prefix each item with "Step N:" and join with newlines.

        Args:
            text: Raw GUI-navigation text.

        Returns:
            Normalised step-list string.
        """
        raw_steps = []

        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue

            if _NUMBERED_LINE_RE.match(line):
                # Already numbered — strip the existing number prefix and keep as one step
                step_text = _NUMBERED_LINE_RE.sub('', line).strip()
                if step_text:
                    raw_steps.append(step_text)
            elif _DELIMITER_RE.search(line):
                # Split arrow/chevron-separated navigation path into individual steps
                parts = [p.strip() for p in _DELIMITER_RE.split(line) if p.strip()]
                raw_steps.extend(parts)
            else:
                # Plain sentence — keep as a single step
                raw_steps.append(line)

        if not raw_steps:
            return text  # Nothing to normalise — return original

        numbered = [f"Step {i + 1}: {step}" for i, step in enumerate(raw_steps)]
        return '\n'.join(numbered)

    def normalize_section(self, section: Dict) -> Dict:
        """
        Normalise the content of a section dict if it contains GUI prose.
        Returns the section unchanged if it does not look like GUI text.

        Args:
            section: Dict with at least a 'content' key (and optionally
                     'section_title', 'page_number', etc.).

        Returns:
            The same dict with 'content' replaced by the normalised step list
            when GUI text is detected; the original dict otherwise.
        """
        content = section.get('content', '')
        if not content or not self.is_gui_text(content):
            return section

        logger.debug(
            f"GUI text detected in section "
            f"'{section.get('section_title', '?')}' — normalising."
        )
        return {**section, 'content': self.normalize(content)}

# Made with Bob
