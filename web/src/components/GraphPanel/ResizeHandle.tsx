import React, { useEffect, useRef } from 'react';

interface ResizeHandleProps {
  onResize: (width: number) => void;
  minWidth?: number;
  maxWidth?: number;
}

const ResizeHandle: React.FC<ResizeHandleProps> = ({ onResize, minWidth = 200, maxWidth = 800 }) => {
  const isDragging = useRef(false);
  const startX = useRef(0);
  const startWidth = useRef(0);

  const handleMouseDown = (e: React.MouseEvent) => {
    isDragging.current = true;
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
      style={{
        width: 6,
        background: '#2a2a4e',
        cursor: 'col-resize',
        transition: 'background 0.1s',
        flexShrink: 0,
      }}
      onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = '#378ADD'; }}
      onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = '#2a2a4e'; }}
    />
  );
};

export default ResizeHandle;
