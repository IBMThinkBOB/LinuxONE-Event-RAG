import React, { useState } from 'react';
import {
  Box,
  TextField,
  Button,
  Paper,
  CircularProgress,
  FormControl,
  Select,
  MenuItem,
  Chip,
  Typography
} from '@mui/material';
import { PaperAirplaneIcon, SparklesIcon } from '@heroicons/react/24/outline';

const Composer = ({ onSubmit, loading }) => {
  const [query, setQuery] = useState('');
  const [selectedTopic, setSelectedTopic] = useState('All Topics');

  const topics = [
    'All Topics',
    'ai',
    'security',
    'performance',
    'resilience',
    'linuxone'
  ];

  const exampleQueries = [
    "How do I optimize AI workloads on LinuxONE?",
    "What are the security features of LinuxONE?",
    "How does LinuxONE ensure high availability?",
    "What AI frameworks are supported on LinuxONE?"
  ];

  const handleSubmit = (e) => {
    if (e) e.preventDefault();
    if (query.trim() && !loading) {
      const filters = selectedTopic !== 'All Topics' ? { topic: selectedTopic } : null;
      onSubmit(query, filters);
      setQuery('');
    }
  };

  const handleKeyDown = (e) => {
    // Submit on Enter (without Shift for new line)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleExampleClick = (example) => {
    setQuery(example);
  };

  const isQueryValid = query.trim().length > 0;

  return (
    <Paper
      elevation={1}
      sx={{
        p: 2.5,
        backgroundColor: 'background.paper',
        border: '1px solid',
        borderColor: 'divider',
        borderRadius: '14px',
        transition: 'all 0.2s ease-in-out',
        '&:focus-within': {
          borderColor: 'primary.main',
          boxShadow: '0 0 0 3px rgba(224, 122, 42, 0.1)',
        },
      }}
    >
      <form onSubmit={handleSubmit}>
        {/* Prompt Input */}
        <TextField
          fullWidth
          multiline
          rows={2}
          variant="outlined"
          placeholder="Ask anything about LinuxONE..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
          sx={{
            mb: 1.5,
            '& .MuiOutlinedInput-root': {
              fontSize: '1rem',
              lineHeight: 1.5,
              padding: 0,
              '& fieldset': {
                border: 'none',
              },
              '&:hover fieldset': {
                border: 'none',
              },
              '&.Mui-focused fieldset': {
                border: 'none',
              },
            },
            '& .MuiOutlinedInput-input': {
              padding: '8px 0',
              '&::placeholder': {
                color: '#9CA3AF',
                opacity: 1,
              },
            },
          }}
        />

        {/* Footer Row: Topic + Send */}
        <Box sx={{ 
          display: 'flex', 
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: 2,
        }}>
          {/* Topic Selector - Left aligned */}
          <FormControl 
            size="small"
            sx={{ 
              minWidth: 140,
            }}
          >
            <Select
              value={selectedTopic}
              onChange={(e) => setSelectedTopic(e.target.value)}
              disabled={loading}
              sx={{
                fontSize: '0.875rem',
                borderRadius: '10px',
                height: '36px',
                '& .MuiOutlinedInput-notchedOutline': {
                  borderColor: 'divider',
                },
                '&:hover .MuiOutlinedInput-notchedOutline': {
                  borderColor: 'primary.light',
                },
                '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
                  borderColor: 'primary.main',
                },
              }}
            >
              {topics.map((topic) => (
                <MenuItem key={topic} value={topic} sx={{ fontSize: '0.875rem' }}>
                  {topic}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          {/* Send Button - Right aligned */}
          <Button
            type="submit"
            variant="contained"
            disabled={loading || !isQueryValid}
            sx={{
              minWidth: '100px',
              height: '36px',
              borderRadius: '10px',
              fontSize: '0.875rem',
              fontWeight: 600,
              textTransform: 'none',
              backgroundColor: isQueryValid ? 'primary.main' : '#E5E7EB',
              color: isQueryValid ? 'white' : '#9CA3AF',
              boxShadow: 'none',
              px: 2.5,
              '&:hover': {
                backgroundColor: isQueryValid ? 'primary.dark' : '#E5E7EB',
                boxShadow: isQueryValid ? '0 2px 8px rgba(224, 122, 42, 0.3)' : 'none',
              },
              '&.Mui-disabled': {
                backgroundColor: '#E5E7EB',
                color: '#9CA3AF',
              },
              transition: 'all 0.2s ease-in-out',
            }}
          >
            {loading ? (
              <>
                <CircularProgress size={16} sx={{ mr: 1, color: 'inherit' }} />
                Sending
              </>
            ) : (
              <>
                <PaperAirplaneIcon style={{ width: 16, height: 16, marginRight: 6 }} />
                Send
              </>
            )}
          </Button>
        </Box>
      </form>

      {/* Suggested Prompts - Always show */}
      <Box sx={{ mt: 2, pt: 2, borderTop: '1px solid', borderColor: 'divider' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
          <SparklesIcon style={{ width: 14, height: 14, color: '#E07A2A' }} />
          <Typography 
            variant="caption" 
            sx={{ 
              color: 'text.secondary',
              fontWeight: 500,
              fontSize: '0.75rem',
            }}
          >
            Suggested prompts
          </Typography>
        </Box>
        <Box 
          sx={{ 
            display: 'flex', 
            gap: 1, 
            flexWrap: 'wrap',
            overflowX: 'auto',
            pb: 0.5,
            '&::-webkit-scrollbar': {
              height: '4px',
            },
            '&::-webkit-scrollbar-thumb': {
              backgroundColor: '#E5E7EB',
              borderRadius: '4px',
            },
          }}
        >
          {exampleQueries.map((example, index) => (
            <Chip
              key={index}
              label={example}
              onClick={() => handleExampleClick(example)}
              disabled={loading}
              size="small"
              sx={{
                cursor: 'pointer',
                backgroundColor: '#FAFAFA',
                border: '1px solid #E5E7EB',
                borderRadius: '999px',
                color: 'text.secondary',
                fontSize: '0.75rem',
                fontWeight: 400,
                height: '26px',
                transition: 'all 0.2s ease-in-out',
                '&:hover': {
                  backgroundColor: '#FEF3E7',
                  borderColor: '#F2A863',
                  color: '#B85F1F',
                },
                '&.Mui-disabled': {
                  opacity: 0.5,
                },
              }}
            />
          ))}
        </Box>
      </Box>
    </Paper>
  );
};

export default Composer;

// Made with Bob