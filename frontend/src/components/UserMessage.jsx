import React from 'react';
import { UserAvatar } from '@carbon/icons-react';

const UserMessage = ({ message }) => (
  <div style={{
    display: 'flex',
    justifyContent: 'flex-end',
    marginBottom: '1rem',
  }}>
    <div style={{
      maxWidth: '80%',
      background: 'var(--cds-layer-01, #f4f4f4)',
      border: '1px solid var(--cds-border-subtle-01, #e0e0e0)',
      padding: '0.875rem 1rem',
      display: 'flex',
      alignItems: 'flex-start',
      gap: '0.75rem',
    }}>
      <UserAvatar size={20} style={{ flexShrink: 0, marginTop: 2, color: 'var(--cds-icon-secondary, #525252)' }} />
      <p className="cds--type-body-long-01" style={{ margin: 0, color: 'var(--cds-text-primary, #161616)' }}>
        {message}
      </p>
    </div>
  </div>
);

export default UserMessage;

// Made with Bob
