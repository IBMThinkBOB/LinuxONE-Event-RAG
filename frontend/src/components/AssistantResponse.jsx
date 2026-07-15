import React, { useState, useMemo } from 'react';
import {
  Tabs,
  TabList,
  Tab,
  TabPanels,
  TabPanel,
  Tag,
  IconButton,
  Tooltip,
} from '@carbon/react';
import { Renew, Checkmark, Time, IbmWatsonAssistant, CopyFile } from '@carbon/icons-react';
import AnswerPanel from './AnswerPanel';
import SourcesPanel from './SourcesPanel';
import FollowUpSuggestions from './FollowUpSuggestions';
import AnswerContext from './AnswerContext';

const AssistantResponse = ({ response, onRegenerate, onFollowUpClick }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(response.answer);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const followUpSuggestions = useMemo(() => {
    if (!response.sources || response.sources.length === 0) return [];
    const suggestions = [];
    const ans = response.answer.toLowerCase();
    if (ans.includes('security') || ans.includes('encryption')) {
      suggestions.push('How does LinuxONE ensure data security?');
      suggestions.push('What encryption features does LinuxONE provide?');
    }
    if (ans.includes('performance') || ans.includes('workload')) {
      suggestions.push('How does LinuxONE optimize workload performance?');
    }
    if (ans.includes('ai') || ans.includes('artificial intelligence')) {
      suggestions.push('What AI frameworks are supported on LinuxONE?');
      suggestions.push('How do I deploy AI models on LinuxONE?');
    }
    if (ans.includes('container') || ans.includes('kubernetes')) {
      suggestions.push('How does LinuxONE support containerization?');
    }
    if (suggestions.length === 0) {
      suggestions.push('What are the key features of LinuxONE?');
      suggestions.push('What workloads are best suited for LinuxONE?');
    }
    return [...new Set(suggestions)].slice(0, 3);
  }, [response]);

  const confidenceTagType = {
    high: 'green',
    medium: 'teal',
    low: 'warm-gray',
  }[response.retrieval_metrics?.confidence_level] || 'gray';

  return (
    <div style={{
      background: 'var(--cds-layer-01, #f4f4f4)',
      border: '1px solid var(--cds-border-subtle-01, #e0e0e0)',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0.75rem 1rem',
        borderBottom: '1px solid var(--cds-border-subtle-01, #e0e0e0)',
        background: 'var(--cds-layer-02, #e0e0e0)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <IbmWatsonAssistant size={20} />
          <span className="cds--type-body-short-02" style={{ fontWeight: 600 }}>
            LinuxONE Assistant
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
          {onRegenerate && (
            <>
              <span className="cds--type-helper-text-01" style={{ color: 'var(--cds-text-secondary)', marginRight: '0.25rem' }}>
                Not satisfied?
              </span>
              <Tooltip align="bottom" label="Regenerate response">
                <IconButton
                  label="Regenerate"
                  kind="ghost"
                  size="sm"
                  onClick={onRegenerate}
                  renderIcon={Renew}
                />
              </Tooltip>
            </>
          )}
          <Tooltip align="bottom" label={copied ? 'Copied!' : 'Copy answer'}>
            <IconButton
              label="Copy"
              kind="ghost"
              size="sm"
              onClick={handleCopy}
              renderIcon={copied ? Checkmark : CopyFile}
            />
          </Tooltip>
        </div>
      </div>

      {/* Tabs */}
      <Tabs>
        <TabList aria-label="Response sections" contained>
          <Tab>Answer</Tab>
          <Tab>Sources ({response.sources?.length || 0})</Tab>
        </TabList>

        <TabPanels>
          {/* Answer tab */}
          <TabPanel style={{ padding: '1.25rem 1rem' }}>
            <AnswerPanel answer={response.answer} />

            {/* Metadata */}
            <div style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--cds-border-subtle-01)', display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
              {response.retrieval_metrics?.confidence_level && (
                <Tag type={confidenceTagType} size="sm">
                  {response.retrieval_metrics.confidence_level.charAt(0).toUpperCase() +
                    response.retrieval_metrics.confidence_level.slice(1)} Confidence
                </Tag>
              )}
              {response.response_time_ms && (
                <Tag type="outline" size="sm">
                  <Time size={12} style={{ marginRight: 4 }} />
                  {response.response_time_ms}ms
                </Tag>
              )}
              {response.model && (
                <Tag type="outline" size="sm">{response.model}</Tag>
              )}
            </div>

            <AnswerContext sources={response.sources || []} confidence={response.retrieval_metrics?.confidence_level} />
            <FollowUpSuggestions suggestions={followUpSuggestions} onSuggestionClick={onFollowUpClick} />
          </TabPanel>

          {/* Sources tab */}
          <TabPanel style={{ padding: '1.25rem 1rem' }}>
            <SourcesPanel sources={response.sources || []} />
          </TabPanel>
        </TabPanels>
      </Tabs>
    </div>
  );
};

export default AssistantResponse;

// Made with Bob
