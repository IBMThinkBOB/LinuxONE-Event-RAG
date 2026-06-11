import React from 'react';
import { Box, Typography, Chip, Paper } from '@mui/material';
import { MagnifyingGlassIcon } from '@heroicons/react/24/outline';

const NoEvidenceState = ({ onSuggestionClick }) => {
  const suggestions = [
    "LinuxONE architecture",
    "LinuxONE security",
    "LinuxONE AI workloads",
    "LinuxONE resiliency"
  ];

  return (
    <Paper
      elevation={1}
      sx={{
        backgroundColor: 'background.paper',
        borderRadius: '14px',
        border: '1px solid',
        borderColor: 'divider',
        p: 4,
        textAlign: 'center',
      }}
    >
      <Box
        sx={{
          width: 64,
          height: 64,
          borderRadius: '50%',
          backgroundColor: '#FEF3E7',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 24px',
        }}
      >
        <MagnifyingGlassIcon style={{ width: 32, height: 32, color: '#E07A2A' }} />
      </Box>

      <Typography
        variant="h6"
        sx={{
          fontWeight: 600,
          color: 'text.primary',
          mb: 1.5,
          fontSize: '1.125rem',
        }}
      >
        No source-backed answer found
      </Typography>

      <Typography
        variant="body2"
        sx={{
          color: 'text.secondary',
          mb: 3,
          maxWidth: '480px',
          margin: '0 auto 24px',
          lineHeight: 1.6,
        }}
      >
        I couldn't find relevant information in the indexed LinuxONE documentation for that question.
      </Typography>

      <Box>
        <Typography
          variant="body2"
          sx={{
            fontWeight: 600,
            color: 'text.primary',
            mb: 1.5,
            fontSize: '0.875rem',
          }}
        >
          Try one of these instead:
        </Typography>
        <Box
          sx={{
            display: 'flex',
            gap: 1,
            flexWrap: 'wrap',
            justifyContent: 'center',
          }}
        >
          {suggestions.map((suggestion, index) => (
            <Chip
              key={index}
              label={suggestion}
              onClick={() => onSuggestionClick && onSuggestionClick(suggestion)}
              sx={{
                cursor: 'pointer',
                backgroundColor: '#FEF3E7',
                border: '1px solid #F2A863',
                borderRadius: '999px',
                color: '#B85F1F',
                fontSize: '0.8125rem',
                fontWeight: 500,
                height: '32px',
                transition: 'all 0.2s ease-in-out',
                '&:hover': {
                  backgroundColor: '#F2A863',
                  color: 'white',
                  borderColor: '#E07A2A',
                  transform: 'translateY(-1px)',
                },
              }}
            />
          ))}
        </Box>
      </Box>
    </Paper>
  );
};

export default NoEvidenceState;

// Made with Bob