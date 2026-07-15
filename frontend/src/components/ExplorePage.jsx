import React from 'react';
import {
  Grid,
  Column,
  ClickableTile,
  Tag,
} from '@carbon/react';
import {
  Security,
  Flash,
  MachineLearning,
  ServerDns,
  VirtualMachine,
} from '@carbon/icons-react';

const categories = [
  {
    id: 'security',
    title: 'Security',
    Icon: Security,
    tagType: 'green',
    description: 'Explore encryption, compliance, and threat protection',
    topics: [
      'How does LinuxONE ensure data security?',
      'What encryption features are available?',
      'Secure container implementation',
      'Compliance and regulatory features',
    ],
  },
  {
    id: 'performance',
    title: 'Performance',
    Icon: Flash,
    tagType: 'teal',
    description: 'Learn about optimization and benchmarks',
    topics: [
      'Performance optimization techniques',
      'Workload performance benchmarks',
      'Resource utilization best practices',
      'Scaling strategies',
    ],
  },
  {
    id: 'ai',
    title: 'AI Workloads',
    Icon: MachineLearning,
    tagType: 'blue',
    description: 'Discover AI frameworks and deployment strategies',
    topics: [
      'Supported AI frameworks',
      'Deploying AI models on LinuxONE',
      'AI workload optimization',
      'Machine learning best practices',
    ],
  },
  {
    id: 'architecture',
    title: 'Architecture',
    Icon: ServerDns,
    tagType: 'gray',
    description: 'Understand system design and components',
    topics: [
      'LinuxONE system architecture',
      'Hardware capabilities',
      'System design principles',
      'Infrastructure planning',
    ],
  },
  {
    id: 'virtualization',
    title: 'Virtualization',
    Icon: VirtualMachine,
    tagType: 'purple',
    description: 'Master containers and virtual machines',
    topics: [
      'Container orchestration with Kubernetes',
      'Virtual machine management',
      'Containerization benefits',
      'Hybrid cloud strategies',
    ],
  },
];

const ExplorePage = ({ onQuerySubmit }) => {
  return (
    <div>
      {/* Header */}
      <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
        <h2 className="cds--type-productive-heading-04">Explore LinuxONE Knowledge</h2>
        <p className="cds--type-body-long-01" style={{ color: 'var(--cds-text-secondary)', maxWidth: 560, margin: '0.5rem auto 0' }}>
          Browse curated topics and discover insights about LinuxONE capabilities
        </p>
      </div>

      {/* Category grid */}
      <Grid narrow>
        {categories.map(({ id, title, Icon, tagType, description, topics }) => (
          <Column key={id} sm={4} md={4} lg={8} style={{ marginBottom: '1rem' }}>
            <div style={{
              background: 'var(--cds-layer-01, #f4f4f4)',
              border: '1px solid var(--cds-border-subtle-01, #e0e0e0)',
              padding: '1.25rem',
              height: '100%',
            }}>
              {/* Category header */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
                <Icon size={24} />
                <div>
                  <p className="cds--type-body-short-02" style={{ fontWeight: 600, margin: 0 }}>{title}</p>
                  <p className="cds--type-helper-text-01" style={{ color: 'var(--cds-text-secondary)', margin: 0 }}>{description}</p>
                </div>
              </div>

              {/* Topics */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {topics.map((topic, i) => (
                  <ClickableTile
                    key={i}
                    onClick={() => onQuerySubmit && onQuerySubmit(topic, null)}
                    style={{ padding: '0.5rem 0.75rem' }}
                  >
                    <span className="cds--type-body-short-01">{topic}</span>
                  </ClickableTile>
                ))}
              </div>
            </div>
          </Column>
        ))}
      </Grid>
    </div>
  );
};

export default ExplorePage;

// Made with Bob
