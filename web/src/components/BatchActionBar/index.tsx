import { Space, Button } from 'antd';
import './index.css';

interface BatchAction {
  label: string;
  icon?: React.ReactNode;
  danger?: boolean;
  confirm?: string;
  onClick: () => void;
}

interface BatchActionBarProps {
  selectedCount: number;
  actions: BatchAction[];
  children?: React.ReactNode;
}

/**
 * 批量操作条（规范 §06）：--accent-alpha-04 底 + 1px --accent-alpha-20 描边 + --radius-sm，
 * 高度 40-44px；选中计数 13px/500 accent 色；危险操作保持 antd danger。
 */
const BatchActionBar: React.FC<BatchActionBarProps> = ({ selectedCount, actions, children }) => {
  if (selectedCount === 0) return null;

  return (
    <div className="eakis-batch-bar">
      <span className="eakis-batch-bar-count">已选择 {selectedCount} 项</span>
      <Space size={8}>
        {actions.map((action, i) => (
          <Button
            key={i}
            size="small"
            type={action.danger ? 'primary' : 'default'}
            danger={action.danger}
            icon={action.icon}
            onClick={action.onClick}
          >
            {action.label}
          </Button>
        ))}
      </Space>
      {children}
    </div>
  );
};

export default BatchActionBar;
