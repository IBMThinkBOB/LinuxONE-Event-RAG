import React, { useState } from 'react';
import {
  Box,
  TextField,
  Button,
  Paper,
  CircularProgress,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip
} from '@mui/material';
import { MagnifyingGlassIcon, SparklesIcon } from '@heroicons/react/24/outline';

const QueryInput = ({ onSubmit, loading }) => {
  const [query, setQuery] = useState('');
  const [selectedTopic, setSelectedTopic] = useState('');

  const topics = [
    'All Topics',
    'ai',
    'security',
    'performance',
    'resilience',
    'linuxone'
  ];

  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim()) {
      const filters = selectedTopic && selectedTopic !== 'All Topics'
        ? { topic: selectedTopic }
        : null;
      onSubmit(query, null, filters);
    }
  };

  const exampleQueries = [
    "How do I optimize AI workloads on LinuxONE?",
    "What are the security features of LinuxONE?",
    "How does LinuxONE ensure high availability?",
    "What AI frameworks are supported on LinuxONE?"
  ];

  const handleExampleClick = (example) => {
    setQuery(example);
  };

  const isQueryValid = query.trim().length > 0;

  return (
    <Paper
      elevation={2}
      sx={{
        p: 3.5,  // 28px internal padding
        backgroundColor: 'background.paper',
        border: '1px solid',
        borderColor: 'divider',
        borderRadius: '14px',
        transition: 'all 0.2s ease-in-out',
        '&:hover': {
          borderColor: 'primary.light',
          boxShadow: '0 4px 12px rgba(224, 122, 42, 0.08)',
        },
      }}
    >
      <form onSubmit={handleSubmit}>
        {/* Main Textarea */}
        <TextField
          fullWidth
          multiline
          rows={4}
          variant="outlined"
          placeholder="Ask anything about LinuxONE... e.g., How do I deploy AI models on LinuxONE?"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          disabled={loading}
          sx={{
            mb: 2,  // 16px spacing
            '& .MuiOutlinedInput-root': {
              fontSize: '1rem',
              lineHeight: 1.6,
              backgroundColor: '#FAFAFA',
              '& fieldset': {
                borderColor: 'divider',
              },
              '&:hover fieldset': {
                borderColor: 'primary.main',
              },
              '&.Mui-focused fieldset': {
                borderColor: 'primary.main',
                borderWidth: '2px',
              },
              '&.Mui-disabled': {
                backgroundColor: '#F5F5F5',
              },
            },
            '& .MuiOutlinedInput-input': {
              '&::placeholder': {
                color: '#9CA3AF',
                opacity: 1,
              },
            },
          }}
        />

        {/* Utility Row: Filter + Search Button */}
        <Box sx={{ 
          display: 'flex', 
          gap: 2,  // 16px gap
          alignItems: 'stretch',
          mb: 3,   // 24px spacing before chips
        }}>
          {/* Topic Filter - Secondary emphasis */}
          <FormControl 
            sx={{ 
              flex: '0 0 200px',
              minWidth: 200,
            }}
            size="small"
          >
            <InputLabel sx={{ fontSize: '0.875rem' }}>Filter by Topic</InputLabel>
            <Select
              value={selectedTopic}
              label="Filter by Topic"
              onChange={(e) => setSelectedTopic(e.target.value)}
              disabled={loading}
              sx={{
                borderRadius: '10px',
                backgroundColor: '#FAFAFA',
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
                <MenuItem key={topic} value={topic}>
                  {topic}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          {/* Primary Search Button */}
          <Button
            type="submit"
            variant="contained"
            size="large"
            fullWidth
            disabled={loading || !isQueryValid}
            sx={{
              flex: 1,
              height: '44px',
              borderRadius: '10px',
              fontSize: '0.9375rem',
              fontWeight: 600,
              textTransform: 'none',
              backgroundColor: isQueryValid ? 'primary.main' : '#E5E7EB',
              color: isQueryValid ? 'white' : '#9CA3AF',
              boxShadow: 'none',
              '&:hover': {
                backgroundColor: isQueryValid ? 'primary.dark' : '#E5E7EB',
                boxShadow: isQueryValid ? '0 4px 12px rgba(224, 122, 42, 0.3)' : 'none',
              },
              '&:active': {
                transform: 'scale(0.98)',
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
                <CircularProgress size={20} sx={{ mr: 1.5, color: 'inherit' }} />
                Searching...
              </>
            ) : (
              <>
                <MagnifyingGlassIcon style={{ width: 20, height: 20, marginRight: 8 }} />
                Search Knowledge Base
              </>
            )}
          </Button>
        </Box>

        {/* Suggested Prompts - Reduced visual aggressiveness */}
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
            <SparklesIcon style={{ width: 16, height: 16, color: '#E07A2A' }} />
            <Typography 
              variant="caption" 
              sx={{ 
                color: 'text.secondary',
                fontWeight: 500,
                fontSize: '0.8125rem',
              }}
            >
              Try these examples:
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            {exampleQueries.map((example, index) => (
              <Chip
                key={index}
                label={example}
                onClick={() => handleExampleClick(example)}
                disabled={loading}
                size="small"
                sx={{
                  cursor: 'pointer',
                  backgroundColor: '#FEF3E7',
                  border: '1px solid #F2A863',
                  borderRadius: '999px',  // Full pill radius
                  color: '#B85F1F',
                  fontSize: '0.8125rem',
                  fontWeight: 500,
                  height: '28px',
                  transition: 'all 0.2s ease-in-out',
                  '&:hover': {
                    backgroundColor: '#F2A863',
                    color: 'white',
                    borderColor: '#E07A2A',
                    transform: 'translateY(-1px)',
                  },
                  '&:active': {
                    transform: 'translateY(0)',
                  },
                  '&.Mui-disabled': {
                    opacity: 0.5,
                  },
                }}
              />
            ))}
          </Box>
        </Box>
      </form>
    </Paper>
  );
};

export default QueryInput;

// Made with Bob
