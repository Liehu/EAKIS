import { Input, Select, Space } from 'antd';

interface FilterItem {
  key: string;
  label: string;
  options: Array<{ value: string; label: string }>;
  value?: string;
  onChange: (value: string | undefined) => void;
}

interface FilterBarProps {
  searchPlaceholder?: string;
  onSearch: (value: string) => void;
  filters?: FilterItem[];
  extra?: React.ReactNode;
}

const FilterBar: React.FC<FilterBarProps> = ({ searchPlaceholder, onSearch, filters = [], extra }) => (
  <Space size="small" wrap style={{ marginBottom: 12 }}>
    <Input.Search
      placeholder={searchPlaceholder}
      allowClear
      size="small"
      style={{ width: 200 }}
      onSearch={onSearch}
    />
    {filters.map((f) => (
      <Select
        key={f.key}
        placeholder={f.label}
        allowClear
        size="small"
        style={{ width: 120 }}
        value={f.value}
        onChange={f.onChange}
        options={f.options}
      />
    ))}
    {extra}
  </Space>
);

export default FilterBar;
