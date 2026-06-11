import React from 'react';
import { Box, Typography, Paper, Button } from '@mui/material';
import { ExclamationTriangleIcon } from '@heroicons/react/24/outline';

const SystemErrorState = ({ error, onRetry }) => {
  return (
    <Paper
      elevation={1}
      sx={{
        backgroundColor: '#FEF2F2',
        borderRadius: '14px',
        border: '1px solid #FCA5A5',
        p: 4,
        textAlign: 'center',
      }}
    >
      <Box
        sx={{
          width: 64,
          height: 64,
          borderRadius: '50%',
          backgroundColor: '#FEE2E2',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 24px',
        }}
      >
        <ExclamationTriangleIcon style={{ width: 32, height: 32, color: '#EF4444' }} />
      </Box>

      <Typography
        variant="h6"
        sx={{
          fontWeight: 600,
          color: '#991B1B',
          mb: 1.5,
          fontSize: '1.125rem',
        }}
      >
        Something went wrong while retrieving results
      </Typography>

      <Typography
        variant="body2"
        sx={{
          color: '#7F1D1D',
          mb: 3,
          maxWidth: '480px',
          margin: '0 auto 24px',
          lineHeight: 1.6,
        }}
      >
        {error || 'Please try again in a moment.'}
      </Typography>

      {onRetry && (
        <Button
          variant="contained"
          onClick={onRetry}
          sx={{
            backgroundColor: '#EF4444',
            color: 'white',
            '&:hover': {
              backgroundColor: '#DC2626',
            },
          }}
        >
          Try Again
        </Button>
      )}
    </Paper>
  );
};

export default SystemErrorState;

// Made with Bob