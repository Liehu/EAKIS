import React from 'react';

interface PlaceholderPageProps {
  title: string;
  description?: string;
}

/**
 * 空态/占位页（规范 §06 空态 + §09 图标体系）：
 * 垂直居中；feather 风内联 SVG（24 viewBox / stroke currentColor / 圆头圆角），色 --text-muted；
 * 标题 15px/600 --text-primary；描述 13px --text-secondary。文案语义与原实现完全一致。
 */
const PlaceholderPage: React.FC<PlaceholderPageProps> = ({ title, description }) => (
  <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
    <div style={{ textAlign: 'center', padding: '40px 20px' }}>
      <svg
        width={44}
        height={44}
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
        style={{ color: 'var(--text-muted)' }}
      >
        <path d="M9 3h6" />
        <path d="M10 3v6.26L4.66 17.5A2 2 0 0 0 6.4 20.5h11.2a2 2 0 0 0 1.74-3L14 9.26V3" />
        <path d="M6.5 15h11" />
      </svg>
      <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-primary)', lineHeight: 1.45, marginTop: 16 }}>
        {title}
      </div>
      <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6, marginTop: 8, maxWidth: 360 }}>
        {description || '该功能后端API尚未实现，当前为占位页面，后续将对接真实API。'}
      </div>
    </div>
  </div>
);

export default PlaceholderPage;
