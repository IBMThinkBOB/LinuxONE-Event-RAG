import React, { useState } from 'react';
import {
  Accordion,
  AccordionItem,
  Tag,
} from '@carbon/react';
import { Document } from '@carbon/icons-react';

const SourcesPanel = ({ sources }) => {
  if (!sources || sources.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '2rem 0' }}>
        <Document size={48} style={{ color: 'var(--cds-icon-disabled)', marginBottom: '0.75rem' }} />
        <p className="cds--type-body-short-01" style={{ color: 'var(--cds-text-secondary)' }}>
          No sources available
        </p>
      </div>
    );
  }

  const getMatchTag = (sim) => {
    if (sim > 0.8) return 'green';
    if (sim > 0.6) return 'teal';
    return 'warm-gray';
  };

  return (
    <Accordion>
      {sources.map((source, index) => (
        <AccordionItem
          key={index}
          title={
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flex: 1 }}>
              <span className="cds--type-body-short-02" style={{ fontWeight: 600 }}>
                {index + 1}. {source.title}
              </span>
              <Tag type={getMatchTag(source.similarity)} size="sm">
                {(source.similarity * 100).toFixed(1)}% match
              </Tag>
            </div>
          }
        >
          <div style={{ paddingBottom: '0.75rem' }}>
            <p className="cds--type-helper-text-01" style={{ color: 'var(--cds-text-secondary)', marginBottom: '0.375rem' }}>
              {source.filename}
            </p>
            <div style={{ display: 'flex', gap: '1rem' }}>
              {source.page_number && (
                <span className="cds--type-helper-text-01" style={{ color: 'var(--cds-text-secondary)' }}>
                  Page {source.page_number}
                </span>
              )}
              {source.section && (
                <span className="cds--type-helper-text-01" style={{ color: 'var(--cds-text-secondary)' }}>
                  {source.section}
                </span>
              )}
            </div>
            {source.content && (
              <div style={{
                marginTop: '0.75rem',
                padding: '0.75rem',
                background: 'var(--cds-layer-02, #e0e0e0)',
                borderLeft: '3px solid var(--cds-border-interactive, #0f62fe)',
              }}>
                <p className="cds--type-body-short-01" style={{ fontStyle: 'italic', color: 'var(--cds-text-secondary)', margin: 0 }}>
                  {source.content}
                </p>
              </div>
            )}
          </div>
        </AccordionItem>
      ))}
    </Accordion>
  );
};

export default SourcesPanel;

// Made with Bob
