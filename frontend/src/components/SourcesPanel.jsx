import React, { useState } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Chip,
  IconButton,
  Collapse
} from '@mui/material';
import {
  ChevronDownIcon,
  ChevronUpIcon,
  DocumentTextIcon
} from '@heroicons/react/24/outline';

const SourcesPanel = ({ sources }) => {
  const [expandedSources, setExpandedSources] = useState({});

  const toggleSource = (index) => {
    setExpandedSources(prev => ({
      ...prev,
      [index]: !prev[index]
    }));
  };

  if (!sources || sources.length === 0) {
    return (
      <Box sx={{ textAlign: 'center', py: 4 }}>
        <DocumentTextIcon
          style={{
            width: 48,
            height: 48,
            color: '#E5E7EB',
            marginBottom: 16,
          }}
        />
        <Typography variant="body2" color="text.secondary">
          No sources available
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      {sources.map((source, index) => (
        <Card
          key={index}
          variant="outlined"
          sx={{
            backgroundColor: '#FAFAFA',
            borderColor: 'divider',
            borderRadius: '10px',
            transition: 'all 0.2s ease-in-out',
            '&:hover': {
              backgroundColor: '#FFFFFF',
              boxShadow: '0 2px 8px rgba(0, 0, 0, 0.06)',
            },
          }}
        >
          <CardContent sx={{ p: 2.5, '&:last-child': { pb: 2.5 } }}>
            {/* Source Header */}
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', mb: 1.5 }}>
              <Typography
                variant="subtitle2"
                sx={{
                  fontWeight: 600,
                  color: 'text.primary',
                  flex: 1,
                  pr: 2,
                  fontSize: '0.875rem',
                }}
              >
                {index + 1}. {source.title}
              </Typography>
              <Chip
                label={`${(source.similarity * 100).toFixed(1)}%`}
                size="small"
                sx={{
                  backgroundColor: source.similarity > 0.8 ? '#10B981' :
                                  source.similarity > 0.6 ? '#E07A2A' : '#F59E0B',
                  color: 'white',
                  fontWeight: 600,
                  height: '22px',
                  fontSize: '0.7rem',
                }}
              />
            </Box>

            {/* Source Metadata */}
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1, fontSize: '0.8125rem' }}>
              📄 {source.filename}
            </Typography>
            <Box sx={{ display: 'flex', gap: 2, mb: 1 }}>
              {source.page_number && (
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.75rem' }}>
                  📖 Page {source.page_number}
                </Typography>
              )}
              {source.section && (
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.75rem' }}>
                  📑 {source.section}
                </Typography>
              )}
            </Box>

            {/* Expandable Content Preview */}
            {source.content && (
              <>
                <IconButton
                  size="small"
                  onClick={() => toggleSource(index)}
                  sx={{
                    mt: 0.5,
                    color: 'primary.main',
                    padding: '4px',
                    '&:hover': {
                      backgroundColor: 'rgba(224, 122, 42, 0.08)',
                    },
                  }}
                >
                  {expandedSources[index] ? (
                    <ChevronUpIcon style={{ width: 18, height: 18 }} />
                  ) : (
                    <ChevronDownIcon style={{ width: 18, height: 18 }} />
                  )}
                  <Typography
                    variant="caption"
                    sx={{
                      ml: 0.5,
                      fontSize: '0.75rem',
                      fontWeight: 500,
                    }}
                  >
                    {expandedSources[index] ? 'Hide' : 'Show'} excerpt
                  </Typography>
                </IconButton>
                <Collapse in={expandedSources[index]}>
                  <Box
                    sx={{
                      mt: 1.5,
                      p: 2,
                      backgroundColor: '#FFFFFF',
                      borderRadius: '8px',
                      border: '1px solid',
                      borderColor: 'divider',
                    }}
                  >
                    <Typography
                      variant="body2"
                      sx={{
                        fontStyle: 'italic',
                        color: 'text.secondary',
                        lineHeight: 1.6,
                        fontSize: '0.8125rem',
                      }}
                    >
                      {source.content}
                    </Typography>
                  </Box>
                </Collapse>
              </>
            )}
          </CardContent>
        </Card>
      ))}
    </Box>
  );
};

export default SourcesPanel;

// Made with Bob