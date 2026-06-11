import React from 'react';
import { Box, Typography, Paper } from '@mui/material';
import { UserIcon } from '@heroicons/react/24/solid';

const UserMessage = ({ message }) => {
  return (
    <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 2 }}>
      <Paper
        elevation={0}
        sx={{
          maxWidth: '85%',
          p: 2,
          backgroundColor: '#F8F9FA',
          borderRadius: '14px',
          border: '1px solid',
          borderColor: 'divider',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1.5 }}>
          <Box
            sx={{
              width: 28,
              height: 28,
              borderRadius: '8px',
              backgroundColor: '#E5E7EB',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}
          >
            <UserIcon style={{ width: 16, height: 16, color: '#6B7280' }} />
          </Box>
          <Box sx={{ flex: 1, pt: 0.5 }}>
            <Typography
              variant="body1"
              sx={{
                color: 'text.primary',
                lineHeight: 1.6,
                fontSize: '0.9375rem',
              }}
            >
              {message}
            </Typography>
          </Box>
        </Box>
      </Paper>
    </Box>
  );
};

export default UserMessage;

// Made with Bob