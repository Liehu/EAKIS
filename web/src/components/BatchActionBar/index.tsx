import { Space, Button, Tag } from 'antd';

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

const BatchActionBar: React.FC<BatchActionBarProps> = ({ selectedCount, actions, children }) => {
  if (selectedCount === 0) return null;

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        padding: '8px 12px',
        marginBottom: 12,
        background: '#378ADD11',
        border: '1px solid #378ADD33',
        borderRadius: 6,
      }}
    >
      <Tag color="blue">已选择 {selectedCount} 项</Tag>
      <Space size="small">
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
