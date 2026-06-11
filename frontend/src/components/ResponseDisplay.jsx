import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Chip,
  Card,
  CardContent,
  Alert,
  IconButton,
  Tooltip,
  Collapse
} from '@mui/material';
import ReactMarkdown from 'react-markdown';
import { 
  DocumentTextIcon, 
  ClockIcon, 
  CpuChipIcon,
  ClipboardDocumentIcon,
  CheckIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  InformationCircleIcon,
  DocumentIcon
} from '@heroicons/react/24/outline';

const ResponseDisplay = ({ response, error }) => {
  const [copied, setCopied] = useState(false);
  const [expandedSources, setExpandedSources] = useState({});

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(response.answer);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const toggleSource = (index) => {
    setExpandedSources(prev => ({
      ...prev,
      [index]: !prev[index]
    }));
  };

  const getConfidenceColor = (confidence) => {
    switch (confidence) {
      case 'high': return '#10B981'; // green
      case 'medium': return '#E07A2A'; // LinuxONE orange
      case 'low': return '#F59E0B'; // amber
      default: return '#6B7280'; // gray
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

  if (error) {
    return (
      <Alert 
        severity="error" 
        sx={{ 
          mb: 4,
          borderRadius: '14px',
          borderLeft: '4px solid #EF4444',
          backgroundColor: '#FEF2F2',
          '& .MuiAlert-icon': {
            color: '#EF4444',
          },
        }}
      >
        <Typography variant="h6" gutterBottom sx={{ fontWeight: 600, color: '#991B1B' }}>
          Unable to find relevant information
        </Typography>
        <Typography variant="body2" sx={{ color: '#7F1D1D', mb: 2 }}>
          {error}
        </Typography>
        <Box sx={{ mt: 2 }}>
          <Typography variant="body2" sx={{ fontWeight: 600, color: '#991B1B', mb: 1 }}>
            💡 Suggestions:
          </Typography>
          <Box component="ul" sx={{ m: 0, pl: 2.5, color: '#7F1D1D' }}>
            <Typography component="li" variant="body2" sx={{ mb: 0.5 }}>
              Rephrase your question with different keywords
            </Typography>
            <Typography component="li" variant="body2" sx={{ mb: 0.5 }}>
              Be more specific about what you're looking for
            </Typography>
            <Typography component="li" variant="body2">
              Try using technical terms from LinuxONE documentation
            </Typography>
          </Box>
        </Box>
      </Alert>
    );
  }

  if (!response) {
    return null;
  }

  return (
    <Box>
      {/* Answer Section */}
      <Paper 
        elevation={2} 
        sx={{ 
          p: 3.5,  // 28px internal padding
          mb: 4,   // 32px spacing between sections
          backgroundColor: 'background.paper',
          borderRadius: '14px',
          borderLeft: '4px solid',
          borderLeftColor: 'primary.main',
          transition: 'all 0.2s ease-in-out',
          '&:hover': {
            boxShadow: '0 10px 20px rgba(224, 122, 42, 0.1)',
          }
        }}
      >
        {/* Answer Header */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <DocumentTextIcon style={{ width: 24, height: 24, color: '#E07A2A' }} />
            <Typography variant="h5" sx={{ fontWeight: 600, color: 'text.primary' }}>
              Answer
            </Typography>
          </Box>
          <Tooltip title={copied ? "Copied!" : "Copy answer"} arrow>
            <IconButton 
              onClick={handleCopy}
              size="small"
              sx={{ 
                color: copied ? '#10B981' : 'primary.main',
                '&:hover': { 
                  backgroundColor: 'rgba(224, 122, 42, 0.08)',
                },
              }}
            >
              {copied ? (
                <CheckIcon style={{ width: 20, height: 20 }} />
              ) : (
                <ClipboardDocumentIcon style={{ width: 20, height: 20 }} />
              )}
            </IconButton>
          </Tooltip>
        </Box>
        
        {/* Answer Content - Improved typography */}
        <Box sx={{ 
          '& p': { 
            mb: 2, 
            lineHeight: 1.7,
            color: 'text.primary',
            fontSize: '1rem',
          },
          '& p:last-child': {
            mb: 0,
          },
          '& ul, & ol': { 
            pl: 3, 
            mb: 2,
            '& li': {
              mb: 1,
              lineHeight: 1.6,
              color: 'text.primary',
            },
          },
          '& code': { 
            backgroundColor: '#FEF3E7', 
            color: '#B85F1F',
            padding: '3px 6px', 
            borderRadius: '6px',
            fontFamily: '"SF Mono", "Monaco", "Inconsolata", "Fira Code", monospace',
            fontSize: '0.875em',
            fontWeight: 500,
          },
          '& strong': {
            color: 'primary.dark',
            fontWeight: 600,
          },
          '& h1, & h2, & h3, & h4, & h5, & h6': {
            color: 'text.primary',
            fontWeight: 600,
            mt: 3,
            mb: 2,
          },
        }}>
          <ReactMarkdown>{response.answer}</ReactMarkdown>
        </Box>

        {/* Metadata Row - Cleaner alignment */}
        <Box sx={{ 
          mt: 3, 
          pt: 3,
          borderTop: '1px solid',
          borderColor: 'divider',
          display: 'flex', 
          gap: 1.5, 
          flexWrap: 'wrap', 
          alignItems: 'center' 
        }}>
          {response.confidence && (
            <Chip
              icon={<InformationCircleIcon style={{ width: 16, height: 16 }} />}
              label={getConfidenceLabel(response.confidence)}
              size="small"
              sx={{
                backgroundColor: getConfidenceColor(response.confidence),
                color: 'white',
                fontWeight: 600,
                height: '28px',
                fontSize: '0.8125rem',
                '& .MuiChip-icon': { 
                  color: 'white',
                  marginLeft: '6px',
                },
              }}
            />
          )}
          <Chip
            icon={<ClockIcon style={{ width: 16, height: 16 }} />}
            label={`${response.response_time_ms}ms`}
            size="small"
            variant="outlined"
            sx={{ 
              borderColor: 'divider',
              color: 'text.secondary',
              height: '28px',
              fontSize: '0.8125rem',
            }}
          />
          <Chip
            icon={<DocumentIcon style={{ width: 16, height: 16 }} />}
            label={`${response.retrieved_chunks} sources`}
            size="small"
            variant="outlined"
            sx={{ 
              borderColor: 'divider',
              color: 'text.secondary',
              height: '28px',
              fontSize: '0.8125rem',
            }}
          />
          <Chip
            icon={<CpuChipIcon style={{ width: 16, height: 16 }} />}
            label={response.model}
            size="small"
            sx={{ 
              backgroundColor: 'primary.main',
              color: 'white',
              fontWeight: 500,
              height: '28px',
              fontSize: '0.8125rem',
              '& .MuiChip-icon': { 
                color: 'white',
                marginLeft: '6px',
              },
            }}
          />
        </Box>
      </Paper>

      {/* Sources Section - Cleaner spacing */}
      <Paper 
        elevation={2} 
        sx={{ 
          p: 3.5,
          backgroundColor: 'background.paper',
          borderRadius: '14px',
          transition: 'all 0.2s ease-in-out',
          '&:hover': {
            boxShadow: '0 10px 20px rgba(0, 0, 0, 0.08)',
          }
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 3 }}>
          <DocumentIcon style={{ width: 24, height: 24, color: '#E07A2A' }} />
          <Typography variant="h5" sx={{ fontWeight: 600, color: 'text.primary' }}>
            Sources
          </Typography>
          <Chip 
            label={response.sources.length} 
            size="small" 
            sx={{ 
              backgroundColor: '#FEF3E7',
              color: '#B85F1F',
              fontWeight: 600,
              height: '24px',
              fontSize: '0.75rem',
            }}
          />
        </Box>

        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {response.sources.map((source, index) => (
            <Card 
              key={index} 
              variant="outlined"
              sx={{
                backgroundColor: '#FAFAFA',
                borderColor: 'divider',
                borderLeft: '3px solid',
                borderLeftColor: 'primary.main',
                borderRadius: '10px',
                transition: 'all 0.2s ease-in-out',
                '&:hover': {
                  backgroundColor: '#FFFFFF',
                  boxShadow: '0 4px 12px rgba(224, 122, 42, 0.08)',
                  borderLeftWidth: '4px',
                },
              }}
            >
              <CardContent sx={{ p: 2.5, '&:last-child': { pb: 2.5 } }}>
                {/* Source Header */}
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', mb: 1.5 }}>
                  <Typography 
                    variant="subtitle1" 
                    sx={{ 
                      fontWeight: 600,
                      color: 'text.primary',
                      flex: 1,
                      pr: 2,
                    }}
                  >
                    {index + 1}. {source.title}
                  </Typography>
                  <Chip
                    label={`${(source.similarity * 100).toFixed(1)}% match`}
                    size="small"
                    sx={{
                      backgroundColor: source.similarity > 0.8 ? '#10B981' : 
                                      source.similarity > 0.6 ? '#E07A2A' : '#F59E0B',
                      color: 'white',
                      fontWeight: 600,
                      height: '24px',
                      fontSize: '0.75rem',
                    }}
                  />
                </Box>

                {/* Source Metadata */}
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1, fontSize: '0.875rem' }}>
                  📄 {source.filename}
                </Typography>
                <Box sx={{ display: 'flex', gap: 2, mb: 1.5 }}>
                  {source.page_number && (
                    <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.8125rem' }}>
                      📖 Page {source.page_number}
                    </Typography>
                  )}
                  {source.section && (
                    <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.8125rem' }}>
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
                        <ChevronUpIcon style={{ width: 20, height: 20 }} />
                      ) : (
                        <ChevronDownIcon style={{ width: 20, height: 20 }} />
                      )}
                      <Typography 
                        variant="caption" 
                        sx={{ 
                          ml: 0.5,
                          fontSize: '0.8125rem',
                          fontWeight: 500,
                        }}
                      >
                        {expandedSources[index] ? 'Hide' : 'Show'} content
                      </Typography>
                    </IconButton>
                    <Collapse in={expandedSources[index]}>
                      <Box 
                        sx={{ 
                          mt: 2, 
                          p: 2, 
                          backgroundColor: '#FFFFFF',
                          borderRadius: '10px',
                          border: '1px solid',
                          borderColor: 'divider',
                          borderLeft: '3px solid',
                          borderLeftColor: 'primary.light',
                        }}
                      >
                        <Typography 
                          variant="body2" 
                          sx={{ 
                            fontStyle: 'italic',
                            color: 'text.secondary',
                            lineHeight: 1.6,
                            fontSize: '0.875rem',
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
      </Paper>
    </Box>
  );
};

export default ResponseDisplay;

// Made with Bob
