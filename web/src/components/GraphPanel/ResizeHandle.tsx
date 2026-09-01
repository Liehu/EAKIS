import React, { useEffect, useRef, useState } from 'react';

interface ResizeHandleProps {
  onResize: (width: number) => void;
  minWidth?: number;
  maxWidth?: number;
}

const ResizeHandle: React.FC<ResizeHandleProps> = ({ onResize, minWidth = 200, maxWidth = 800 }) => {
  const isDragging = useRef(false);
  const startX = useRef(0);
  const startWidth = useRef(0);
  // 仅用于拖拽态/hover 配色（accent 令牌），不影响交互逻辑
  const [dragging, setDragging] = useState(false);
  const [hovered, setHovered] = useState(false);

  const handleMouseDown = (e: React.MouseEvent) => {
    isDragging.current = true;
    setDragging(true);
    startX.current = e.clientX;
    startWidth.current = (e.target as HTMLElement).nextElementSibling?.clientWidth || 400;
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  };

  const handleMouseMove = (e: MouseEvent) => {
    if (!isDragging.current) return;
    const newWidth = startWidth.current - (e.clientX - startX.current);
    const clampedWidth = Math.max(minWidth, Math.min(maxWidth, newWidth));
    onResize(clampedWidth);
  };

  const handleMouseUp = () => {
    isDragging.current = false;
    setDragging(false);
    document.removeEventListener('mousemove', handleMouseMove);
    document.removeEventListener('mouseup', handleMouseUp);
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
  };

  useEffect(() => {
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, []);

  return (
    <div
      onMouseDown={handleMouseDown}
      onMouseEnter={() => { setHovered(true); }}
      onMouseLeave={() => { setHovered(false); }}
      style={{
        width: 6,
        background: dragging ? 'var(--accent-alpha-20)' : (hovered ? 'var(--accent-color)' : 'var(--border-color)'),
        cursor: 'col-resize',
        transition: 'background 0.1s',
        flexShrink: 0,
      }}
    />
  );
};

export default ResizeHandle;
