import React from 'react';
import { Box } from '@mui/material';
import ReactMarkdown from 'react-markdown';

const AnswerPanel = ({ answer }) => {
  return (
    <Box
      sx={{
        '& p': {
          mb: 2,
          lineHeight: 1.7,
          color: 'text.primary',
          fontSize: '0.9375rem',
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
            fontSize: '0.9375rem',
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
        '& pre': {
          backgroundColor: '#F8F9FA',
          border: '1px solid',
          borderColor: 'divider',
          borderRadius: '10px',
          p: 2,
          overflow: 'auto',
          '& code': {
            backgroundColor: 'transparent',
            padding: 0,
            color: 'text.primary',
          },
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
          '&:first-of-type': {
            mt: 0,
          },
        },
        '& h1': { fontSize: '1.5rem' },
        '& h2': { fontSize: '1.25rem' },
        '& h3': { fontSize: '1.125rem' },
        '& h4': { fontSize: '1rem' },
        '& a': {
          color: 'primary.main',
          textDecoration: 'none',
          '&:hover': {
            textDecoration: 'underline',
          },
        },
        '& blockquote': {
          borderLeft: '3px solid',
          borderColor: 'primary.light',
          pl: 2,
          ml: 0,
          color: 'text.secondary',
          fontStyle: 'italic',
        },
        '& hr': {
          border: 'none',
          borderTop: '1px solid',
          borderColor: 'divider',
          my: 3,
        },
      }}
    >
      <ReactMarkdown>{answer}</ReactMarkdown>
    </Box>
  );
};

export default AnswerPanel;

// Made with Bob