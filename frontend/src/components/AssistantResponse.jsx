import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Tabs,
  Tab,
  Chip,
  IconButton,
  Tooltip,
  Button
} from '@mui/material';
import { CpuChipIcon } from '@heroicons/react/24/solid';
import { 
  ClipboardDocumentIcon,
  CheckIcon,
  ClockIcon,
  InformationCircleIcon,
  ArrowPathIcon
} from '@heroicons/react/24/outline';
import AnswerPanel from './AnswerPanel';
import SourcesPanel from './SourcesPanel';

const AssistantResponse = ({ response, onRegenerate }) => {
  const [activeTab, setActiveTab] = useState(0);
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

  const getConfidenceColor = (confidence) => {
    switch (confidence) {
      case 'high': return '#10B981';
      case 'medium': return '#E07A2A';
      case 'low': return '#F59E0B';
      default: return '#6B7280';
    }
  };

  const getConfidenceLabel = (confidence) => {
    switch (confidence) {
      case 'high': return 'High Confidence';
      case 'medium': return 'Medium Confidence';
      case 'low': return 'Low Confidence';
      default: return 'Unknown';
    }
  };

  return (
    <Paper
      elevation={1}
      sx={{
        backgroundColor: 'background.paper',
        borderRadius: '14px',
        border: '1px solid',
        borderColor: 'divider',
        overflow: 'hidden',
      }}
    >
      {/* Header with Assistant Icon */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          px: 3,
          py: 2,
          borderBottom: '1px solid',
          borderColor: 'divider',
          backgroundColor: '#FAFAFA',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Box
            sx={{
              width: 32,
              height: 32,
              borderRadius: '8px',
              backgroundColor: 'primary.main',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <CpuChipIcon style={{ width: 18, height: 18, color: 'white' }} />
          </Box>
          <Typography variant="h6" sx={{ fontWeight: 600, fontSize: '1rem' }}>
            LinuxONE Assistant
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'center' }}>
          {onRegenerate && (
            <>
              <Typography
                variant="body2"
                sx={{
                  color: 'text.secondary',
                  fontSize: '0.8125rem',
                  fontWeight: 500,
                }}
              >
                Not satisfied? Try regenerating!
              </Typography>
              <Tooltip title="Regenerate response" arrow>
                <IconButton
                  onClick={onRegenerate}
                  size="small"
                  sx={{
                    color: 'text.secondary',
                    '&:hover': {
                      backgroundColor: 'rgba(224, 122, 42, 0.08)',
                      color: 'primary.main',
                    },
                  }}
                >
                  <ArrowPathIcon style={{ width: 18, height: 18 }} />
                </IconButton>
              </Tooltip>
            </>
          )}
          <Tooltip title={copied ? "Copied!" : "Copy answer"} arrow>
            <IconButton
              onClick={handleCopy}
              size="small"
              sx={{
                color: copied ? '#10B981' : 'text.secondary',
                '&:hover': {
                  backgroundColor: 'rgba(224, 122, 42, 0.08)',
                  color: 'primary.main',
                },
              }}
            >
              {copied ? (
                <CheckIcon style={{ width: 18, height: 18 }} />
              ) : (
                <ClipboardDocumentIcon style={{ width: 18, height: 18 }} />
              )}
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* Tabs Navigation */}
      <Box sx={{ borderBottom: '1px solid', borderColor: 'divider' }}>
        <Tabs
          value={activeTab}
          onChange={(e, newValue) => setActiveTab(newValue)}
          sx={{
            minHeight: '48px',
            px: 2,
            '& .MuiTab-root': {
              minHeight: '48px',
              textTransform: 'none',
              fontWeight: 500,
              fontSize: '0.875rem',
              color: 'text.secondary',
              '&.Mui-selected': {
                color: 'primary.main',
                fontWeight: 600,
              },
            },
            '& .MuiTabs-indicator': {
              backgroundColor: 'primary.main',
              height: '3px',
            },
          }}
        >
          <Tab label="Answer" />
          <Tab 
            label={
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                Sources
                <Chip
                  label={response.sources?.length || 0}
                  size="small"
                  sx={{
                    height: '20px',
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    backgroundColor: activeTab === 1 ? 'primary.main' : '#E5E7EB',
                    color: activeTab === 1 ? 'white' : 'text.secondary',
                  }}
                />
              </Box>
            }
          />
        </Tabs>
      </Box>

      {/* Tab Content */}
      <Box sx={{ p: 3 }}>
        {activeTab === 0 ? (
          <>
            <AnswerPanel answer={response.answer} />
            
            {/* Metadata Row */}
            <Box
              sx={{
                mt: 3,
                pt: 3,
                borderTop: '1px solid',
                borderColor: 'divider',
                display: 'flex',
                gap: 1.5,
                flexWrap: 'wrap',
                alignItems: 'center',
              }}
            >
              {response.confidence && (
                <Chip
                  icon={<InformationCircleIcon style={{ width: 14, height: 14 }} />}
                  label={getConfidenceLabel(response.confidence)}
                  size="small"
                  sx={{
                    backgroundColor: getConfidenceColor(response.confidence),
                    color: 'white',
                    fontWeight: 600,
                    height: '26px',
                    fontSize: '0.75rem',
                    '& .MuiChip-icon': {
                      color: 'white',
                      marginLeft: '6px',
                    },
                  }}
                />
              )}
              <Chip
                icon={<ClockIcon style={{ width: 14, height: 14 }} />}
                label={`${response.response_time_ms}ms`}
                size="small"
                variant="outlined"
                sx={{
                  borderColor: 'divider',
                  color: 'text.secondary',
                  height: '26px',
                  fontSize: '0.75rem',
                }}
              />
              <Chip
                label={response.model}
                size="small"
                sx={{
                  backgroundColor: '#FAFAFA',
                  color: 'text.secondary',
                  height: '26px',
                  fontSize: '0.75rem',
                  fontWeight: 500,
                }}
              />
            </Box>
          </>
        ) : (
          <SourcesPanel sources={response.sources || []} />
        )}
      </Box>
    </Paper>
  );
};

export default AssistantResponse;

// Made with Bob