import React from 'react';
import { InlineNotification, Button } from '@carbon/react';

const SystemErrorState = ({ error, onRetry }) => (
  <div>
    <InlineNotification
      kind="error"
      title="Something went wrong"
      subtitle={error || 'An unexpected error occurred while processing your request.'}
      hideCloseButton
      lowContrast
      actions={
        onRetry
          ? <Button kind="ghost" size="sm" onClick={onRetry}>Try again</Button>
          : undefined
      }
    />
    <div style={{ marginTop: '0.75rem', padding: '1rem', background: 'var(--cds-layer-01, #f4f4f4)', border: '1px solid var(--cds-border-subtle-01, #e0e0e0)' }}>
      <p className="cds--type-body-short-02" style={{ fontWeight: 600, marginBottom: '0.5rem' }}>
        What you can do:
      </p>
      <ul className="cds--type-body-short-01" style={{ paddingLeft: '1.25rem', color: 'var(--cds-text-secondary)', margin: 0 }}>
        <li>Try again in a moment</li>
        <li>Simplify your question</li>
        <li>Check your connection</li>
      </ul>
    </div>
  </div>
);

export default SystemErrorState;

// Made with Bob
