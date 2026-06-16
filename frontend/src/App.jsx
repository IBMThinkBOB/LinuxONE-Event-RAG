import React, { useState, useEffect } from 'react';
import {
  Container,
  Box,
  Typography,
  AppBar,
  Toolbar,
  CssBaseline,
  ThemeProvider,
  createTheme,
  CircularProgress,
  Tabs,
  Tab
} from '@mui/material';
import { CpuChipIcon } from '@heroicons/react/24/solid';
import Composer from './components/Composer';
import UserMessage from './components/UserMessage';
import AssistantResponse from './components/AssistantResponse';
import NoEvidenceState from './components/NoEvidenceState';
import SystemErrorState from './components/SystemErrorState';
import ExplorePage from './components/ExplorePage';
import { queryKnowledgeBase } from './services/api';

// Professional Design System
const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#E07A2A',
      dark: '#B85F1F',
      light: '#F2A863',
    },
    secondary: {
      main: '#24a148',
    },
    background: {
      default: '#F8F9FA',
      paper: '#FFFFFF',
    },
    text: {
      primary: '#1A1A1A',
      secondary: '#6B7280',
    },
    divider: '#E5E7EB',
  },
  typography: {
    fontFamily: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    h3: {
      fontSize: '2.25rem',
      fontWeight: 600,
      lineHeight: 1.2,
      letterSpacing: '-0.02em',
    },
    h5: {
      fontSize: '1.5rem',
      fontWeight: 600,
      lineHeight: 1.3,
    },
    h6: {
      fontSize: '1.125rem',
      fontWeight: 600,
      lineHeight: 1.4,
    },
    body1: {
      fontSize: '1rem',
      lineHeight: 1.6,
    },
    body2: {
      fontSize: '0.875rem',
      lineHeight: 1.5,
    },
    caption: {
      fontSize: '0.8125rem',
      lineHeight: 1.4,
    },
  },
  shape: {
    borderRadius: 14,
  },
  spacing: 8,
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 600,
          borderRadius: '10px',
          height: '44px',
          padding: '0 18px',
          fontSize: '0.9375rem',
          transition: 'all 0.2s ease-in-out',
          boxShadow: 'none',
          '&:hover': {
            boxShadow: 'none',
          },
        },
        contained: {
          '&:disabled': {
            backgroundColor: '#E5E7EB',
            color: '#9CA3AF',
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          fontWeight: 500,
          fontSize: '0.8125rem',
          height: '28px',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
        },
        elevation1: {
          boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
        },
        elevation2: {
          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: '12px',
          },
        },
      },
    },
  },
});

function App() {
  const [activeView, setActiveView] = useState('ask'); // ask, explore, compare
  const [uiState, setUiState] = useState('idle'); // idle, searching, answered, no_sources, error
  const [currentQuery, setCurrentQuery] = useState('');
  const [response, setResponse] = useState(null);
  const [error, setError] = useState(null);

  const handleQuery = async (query, filters) => {
    setCurrentQuery(query);
    setUiState('searching');
    setError(null);
    setResponse(null);
    setActiveView('ask'); // Switch to ask view when querying

    try {
      const data = await queryKnowledgeBase(query, null, filters);
      
      // Check if we got sources
      if (!data.sources || data.sources.length === 0) {
        setUiState('no_sources');
      } else {
        setResponse(data);
        setUiState('answered');
      }
    } catch (err) {
      // Check if it's a 404 (no relevant content) vs actual error
      if (err.response?.status === 404) {
        setUiState('no_sources');
      } else {
        const errorMessage = err.response?.data?.detail || err.message || 'Failed to query knowledge base';
        setError(errorMessage);
        setUiState('error');
      }
    }
  };

  const handleRegenerate = () => {
    if (currentQuery) {
      handleQuery(currentQuery, null);
    }
  };

  const handleSuggestionClick = (suggestion) => {
    handleQuery(suggestion, null);
  };

  const handleRetry = () => {
    if (currentQuery) {
      handleQuery(currentQuery, null);
    }
  };

  // Determine if we're in conversation mode
  const isConversationMode = ['searching', 'answered', 'no_sources', 'error'].includes(uiState);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ minHeight: '100vh', backgroundColor: 'background.default' }}>
        {/* Header with Navigation */}
        <AppBar
          position="static"
          elevation={0}
          sx={{
            borderBottom: '1px solid',
            borderColor: 'divider',
          }}
        >
          <Toolbar sx={{ py: 1.5 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, flex: 1 }}>
              <Box
                sx={{
                  width: 32,
                  height: 32,
                  borderRadius: '8px',
                  backgroundColor: 'rgba(255,255,255,0.2)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <CpuChipIcon style={{ width: 20, height: 20, color: 'white' }} />
              </Box>
              <Typography variant="h6" component="div" sx={{ fontWeight: 600 }}>
                LinuxONE Knowledge Assistant
              </Typography>
            </Box>
            
            {/* Navigation Tabs */}
            <Tabs
              value={activeView}
              onChange={(e, newValue) => setActiveView(newValue)}
              sx={{
                minHeight: '48px',
                '& .MuiTab-root': {
                  minHeight: '48px',
                  textTransform: 'none',
                  fontWeight: 500,
                  fontSize: '0.9375rem',
                  color: 'rgba(255,255,255,0.7)',
                  '&.Mui-selected': {
                    color: 'white',
                    fontWeight: 600,
                  },
                },
                '& .MuiTabs-indicator': {
                  backgroundColor: 'white',
                  height: '3px',
                },
              }}
            >
              <Tab label="Ask" value="ask" />
              <Tab label="Explore" value="explore" />
            </Tabs>
          </Toolbar>
        </AppBar>

        {/* Main Content */}
        <Container
          maxWidth={false}
          sx={{
            maxWidth: activeView === 'explore' ? '1200px' : '900px',
            pt: isConversationMode ? 3 : 5,
            pb: 4,
          }}
        >
          {/* Explore View */}
          {activeView === 'explore' && (
            <ExplorePage
              onQuerySubmit={handleQuery}
            />
          )}

          {/* Ask View - Empty State - Hero */}
          {activeView === 'ask' && uiState === 'idle' && (
            <>
              <Box sx={{ mb: 4, textAlign: 'center' }}>
                <Typography
                  variant="h3"
                  gutterBottom
                  sx={{
                    color: 'text.primary',
                    mb: 2,
                  }}
                >
                  Ask Questions About LinuxONE
                </Typography>
                <Typography
                  variant="body1"
                  sx={{
                    color: 'text.secondary',
                    maxWidth: '600px',
                    margin: '0 auto',
                    lineHeight: 1.6,
                  }}
                >
                  Search indexed LinuxONE documentation and redbooks for source-backed answers.
                </Typography>
              </Box>
              <Composer onSubmit={handleQuery} loading={false} />
            </>
          )}

          {/* Ask View - Conversation Mode */}
          {activeView === 'ask' && isConversationMode && (
            <>
              {/* User Message */}
              <UserMessage message={currentQuery} />

              {/* Loading State */}
              {uiState === 'searching' && (
                <Box
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 2,
                    p: 3,
                    backgroundColor: '#FEF3E7',
                    borderRadius: '14px',
                    border: '1px solid #F2A863',
                    mb: 3,
                  }}
                >
                  <CircularProgress size={24} sx={{ color: 'primary.main' }} />
                  <Box>
                    <Typography variant="body2" fontWeight={600} color="primary.main">
                      Searching knowledge base...
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Analyzing indexed documentation
                    </Typography>
                  </Box>
                </Box>
              )}

              {/* Assistant Response */}
              {uiState === 'answered' && response && (
                <Box sx={{ mb: 3 }}>
                  <AssistantResponse
                    response={response}
                    onRegenerate={handleRegenerate}
                    onFollowUpClick={handleSuggestionClick}
                  />
                </Box>
              )}

              {/* No Evidence State */}
              {uiState === 'no_sources' && (
                <Box sx={{ mb: 3 }}>
                  <NoEvidenceState onSuggestionClick={handleSuggestionClick} />
                </Box>
              )}

              {/* System Error State */}
              {uiState === 'error' && (
                <Box sx={{ mb: 3 }}>
                  <SystemErrorState error={error} onRetry={handleRetry} />
                </Box>
              )}

              {/* Composer at bottom in conversation mode */}
              <Box sx={{ mt: 3 }}>
                <Composer
                  onSubmit={handleQuery}
                  loading={uiState === 'searching'}
                />
              </Box>
            </>
          )}
        </Container>
      </Box>
    </ThemeProvider>
  );
}

export default App;

// Made with Bob
