import React from 'react';
import { Tag } from '@carbon/react';
import { Idea } from '@carbon/icons-react';

const FollowUpSuggestions = ({ suggestions, onSuggestionClick }) => {
  if (!suggestions || suggestions.length === 0) return null;

  return (
    <div style={{
      marginTop: '1rem',
      padding: '0.875rem 1rem',
      background: 'var(--cds-layer-02, #e0e0e0)',
      borderLeft: '3px solid var(--cds-border-interactive, #0f62fe)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.625rem' }}>
        <Idea size={16} />
        <span className="cds--type-helper-text-01" style={{ fontWeight: 600, color: 'var(--cds-text-secondary)' }}>
          Continue exploring
        </span>
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
        {suggestions.map((suggestion, i) => (
          <Tag
            key={i}
            type="blue"
            onClick={() => onSuggestionClick && onSuggestionClick(suggestion)}
            style={{ cursor: 'pointer' }}
          >
            {suggestion}
          </Tag>
        ))}
      </div>
    </div>
  );
};

export default FollowUpSuggestions;

// Made with Bob
