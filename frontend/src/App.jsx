import React, { useState, useEffect, useRef } from 'react';
import {
  Header,
  HeaderName,
  HeaderNavigation,
  HeaderMenuItem,
  Content,
  Theme,
} from '@carbon/react';
import Composer from './components/Composer';
import UserMessage from './components/UserMessage';
import AssistantResponse from './components/AssistantResponse';
import NoEvidenceState from './components/NoEvidenceState';
import SystemErrorState from './components/SystemErrorState';
import ExplorePage from './components/ExplorePage';
import { queryKnowledgeBase } from './services/api';
import '@carbon/styles/css/styles.css';
import './app.css';

function App() {
  const [activeView, setActiveView] = useState('ask');
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleQuery = async (query, filters) => {
    if (isLoading) return;
    setActiveView('ask');
    setIsLoading(true);

    const placeholderId = Date.now() + Math.random();
    setMessages((prev) => [
      ...prev,
      { id: Date.now() + Math.random() + 1, type: 'user', query },
      { id: placeholderId, type: 'assistant', loading: true },
    ]);

    try {
      const data = await queryKnowledgeBase(query, null, filters);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === placeholderId
            ? !data.sources || data.sources.length === 0
              ? { ...m, type: 'no_sources', loading: false }
              : { ...m, type: 'assistant', loading: false, response: data }
            : m
        )
      );
    } catch (err) {
      const is404 = err.response?.status === 404;
      const errorMessage =
        err.response?.data?.detail || err.message || 'Failed to query knowledge base';
      setMessages((prev) =>
        prev.map((m) =>
          m.id === placeholderId
            ? is404
              ? { ...m, type: 'no_sources', loading: false }
              : { ...m, type: 'error', loading: false, error: errorMessage }
            : m
        )
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegenerate = (query) => {
    setMessages((prev) => {
      const next = [...prev];
      for (let i = next.length - 1; i >= 0; i--) {
        if (next[i].type !== 'user') { next.splice(i, 1); break; }
      }
      return next;
    });
    handleQuery(query, null);
  };

  const handleSuggestionClick = (suggestion) => handleQuery(suggestion, null);

  const hasMessages = messages.length > 0;

  return (
    <Theme theme="white">
      <div className="app-shell">
        {/* IBM Carbon Header */}
        <Header aria-label="LinuxONE Knowledge Assistant">
          <HeaderName prefix="IBM">LinuxONE Knowledge Assistant</HeaderName>
          <HeaderNavigation aria-label="Main navigation">
            <HeaderMenuItem
              isCurrentPage={activeView === 'ask'}
              onClick={() => setActiveView('ask')}
            >
              Ask
            </HeaderMenuItem>
            <HeaderMenuItem
              isCurrentPage={activeView === 'explore'}
              onClick={() => setActiveView('explore')}
            >
              Explore
            </HeaderMenuItem>
          </HeaderNavigation>
        </Header>

        <Content className="app-content">
          {/* Explore View */}
          {activeView === 'explore' && (
            <div className="explore-wrapper">
              <ExplorePage onQuerySubmit={handleQuery} />
            </div>
          )}

          {/* Ask View */}
          {activeView === 'ask' && (
            <div className="ask-layout">
              {/* Scrollable message area */}
              <div className="message-area">
                <div className="message-inner">
                  {/* Hero — shown before first message */}
                  {!hasMessages && (
                    <div className="hero">
                      <h1 className="cds--type-productive-heading-05">
                        Ask Questions About LinuxONE
                      </h1>
                      <p className="cds--type-body-long-01 hero-sub">
                        Search indexed LinuxONE documentation and redbooks for source-backed answers.
                      </p>
                    </div>
                  )}

                  {/* Message thread */}
                  {messages.map((msg) => (
                    <div key={msg.id}>
                      {msg.type === 'user' && <UserMessage message={msg.query} />}

                      {msg.type === 'assistant' && msg.loading && (
                        <div className="loading-bubble">
                          <div className="cds--loading cds--loading--small">
                            <svg className="cds--loading__svg" viewBox="0 0 100 100">
                              <circle className="cds--loading__background" cx="50" cy="50" r="44" />
                              <circle className="cds--loading__stroke" cx="50" cy="50" r="44" />
                            </svg>
                          </div>
                          <div>
                            <p className="cds--type-body-short-02 loading-title">Searching knowledge base…</p>
                            <p className="cds--type-helper-text-01">Analyzing indexed documentation</p>
                          </div>
                        </div>
                      )}

                      {msg.type === 'assistant' && !msg.loading && msg.response && (
                        <div className="msg-row">
                          <AssistantResponse
                            response={msg.response}
                            onRegenerate={() => {
                              const idx = messages.findIndex((m) => m.id === msg.id);
                              const userMsg = messages.slice(0, idx).reverse().find((m) => m.type === 'user');
                              handleRegenerate(userMsg?.query);
                            }}
                            onFollowUpClick={handleSuggestionClick}
                          />
                        </div>
                      )}

                      {msg.type === 'no_sources' && (
                        <div className="msg-row">
                          <NoEvidenceState onSuggestionClick={handleSuggestionClick} />
                        </div>
                      )}

                      {msg.type === 'error' && (
                        <div className="msg-row">
                          <SystemErrorState
                            error={msg.error}
                            onRetry={() => {
                              const idx = messages.findIndex((m) => m.id === msg.id);
                              const userMsg = messages.slice(0, idx).reverse().find((m) => m.type === 'user');
                              if (userMsg) handleRegenerate(userMsg.query);
                            }}
                          />
                        </div>
                      )}
                    </div>
                  ))}
                  <div ref={bottomRef} />
                </div>
              </div>

              {/* Pinned composer */}
              <div className="composer-bar">
                <div className="composer-inner">
                  <Composer
                    onSubmit={handleQuery}
                    loading={isLoading}
                    compact={hasMessages}
                  />
                </div>
              </div>
            </div>
          )}
        </Content>
      </div>
    </Theme>
  );
}

export default App;

// Made with Bob
