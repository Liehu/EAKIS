import React from 'react';

interface InfoCardGridProps {
  data: Array<{ label: string; value: string; span?: number }>;
}

const InfoCardGrid: React.FC<InfoCardGridProps> = ({ data }) => (
  <div style={{
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: 16,
    padding: 16,
  }}>
    {data.map((item) => (
      <div
        key={item.label}
        style={{
          background: '#1a1a2e',
          borderRadius: 12,
          padding: 16,
          gridColumn: item.span === 2 ? 'span 2' : undefined,
          border: '1px solid #2a2a4e',
        }}
      >
        <div style={{ fontSize: 12, color: '#888', marginBottom: 4 }}>{item.label}</div>
        <div style={{ fontSize: 14, color: '#e2e8f0', wordBreak: 'break-all' }}>{item.value || '-'}</div>
      </div>
    ))}
  </div>
);

export default InfoCardGrid;
