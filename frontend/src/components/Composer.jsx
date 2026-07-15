import React, { useState } from 'react';
import {
  TextArea,
  Button,
  Select,
  SelectItem,
  Tag,
} from '@carbon/react';
import { SendAlt, Idea } from '@carbon/icons-react';

const Composer = ({ onSubmit, loading, compact = false }) => {
  const [query, setQuery] = useState('');
  const [selectedTopic, setSelectedTopic] = useState('all');

  const topics = [
    { value: 'all', label: 'All Topics' },
    { value: 'ai', label: 'AI' },
    { value: 'security', label: 'Security' },
    { value: 'performance', label: 'Performance' },
    { value: 'resilience', label: 'Resilience' },
    { value: 'linuxone', label: 'LinuxONE' },
  ];

  const exampleQueries = [
    'How do I optimize AI workloads on LinuxONE?',
    'What are the security features of LinuxONE?',
    'How does LinuxONE ensure high availability?',
    'What AI frameworks are supported on LinuxONE?',
  ];

  const handleSubmit = (e) => {
    if (e) e.preventDefault();
    if (query.trim() && !loading) {
      const filters = selectedTopic !== 'all' ? { topic: selectedTopic } : null;
      onSubmit(query, filters);
      setQuery('');
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="composer">
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        <TextArea
          id="query-input"
          labelText=""
          placeholder="Ask anything about LinuxONE…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
          rows={2}
          style={{ resize: 'none' }}
        />

        <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: '1rem' }}>
          <Select
            id="topic-select"
            labelText=""
            value={selectedTopic}
            onChange={(e) => setSelectedTopic(e.target.value)}
            disabled={loading}
            style={{ maxWidth: '180px' }}
          >
            {topics.map((t) => (
              <SelectItem key={t.value} value={t.value} text={t.label} />
            ))}
          </Select>

          <Button
            type="submit"
            renderIcon={SendAlt}
            disabled={loading || !query.trim()}
            size="md"
          >
            {loading ? 'Sending…' : 'Send'}
          </Button>
        </div>
      </form>

      {/* Suggested prompts — only in idle state */}
      {!compact && (
        <div style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--cds-border-subtle-01, #e0e0e0)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.625rem' }}>
            <Idea size={16} />
            <span className="cds--type-helper-text-01" style={{ color: 'var(--cds-text-secondary)' }}>
              Suggested prompts
            </span>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
            {exampleQueries.map((example, i) => (
              <Tag
                key={i}
                type="outline"
                onClick={() => !loading && setQuery(example)}
                style={{ cursor: loading ? 'default' : 'pointer' }}
              >
                {example}
              </Tag>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default Composer;

// Made with Bob
