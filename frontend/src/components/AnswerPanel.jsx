import React from 'react';
import ReactMarkdown from 'react-markdown';

const AnswerPanel = ({ answer }) => (
  <div className="answer-markdown cds--type-body-long-01">
    <ReactMarkdown>{answer}</ReactMarkdown>
  </div>
);

export default AnswerPanel;

// Made with Bob
