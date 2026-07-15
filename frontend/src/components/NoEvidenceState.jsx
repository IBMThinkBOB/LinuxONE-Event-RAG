import React from 'react';
import { InlineNotification, Tag, Button } from '@carbon/react';

const NoEvidenceState = ({ onSuggestionClick }) => {
  const suggestions = [
    'LinuxONE architecture',
    'LinuxONE security',
    'LinuxONE AI workloads',
    'LinuxONE resiliency',
  ];

  return (
    <div>
      <InlineNotification
        kind="warning"
        title="No source-backed answer found"
        subtitle="I couldn't find relevant information in the indexed LinuxONE documentation for that question."
        hideCloseButton
        lowContrast
      />
      <div style={{ marginTop: '1rem', padding: '1rem', background: 'var(--cds-layer-01, #f4f4f4)', border: '1px solid var(--cds-border-subtle-01, #e0e0e0)' }}>
        <p className="cds--type-body-short-02" style={{ fontWeight: 600, marginBottom: '0.5rem' }}>
          Try these tips:
        </p>
        <ul className="cds--type-body-short-01" style={{ paddingLeft: '1.25rem', color: 'var(--cds-text-secondary)', marginBottom: '1rem' }}>
          <li>Rephrase your question with different keywords</li>
          <li>Be more specific about what you're looking for</li>
          <li>Use technical terms from LinuxONE documentation</li>
        </ul>

        <p className="cds--type-body-short-02" style={{ fontWeight: 600, marginBottom: '0.5rem' }}>
          Or explore these topics:
        </p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
          {suggestions.map((s, i) => (
            <Tag
              key={i}
              type="blue"
              onClick={() => onSuggestionClick && onSuggestionClick(s)}
              style={{ cursor: 'pointer' }}
            >
              {s}
            </Tag>
          ))}
        </div>
      </div>
    </div>
  );
};

export default NoEvidenceState;

// Made with Bob
