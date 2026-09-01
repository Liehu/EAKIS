import { Input, Select } from 'antd';
import './index.css';

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

/**
 * 列表筛选工具栏：容器透明无边框卡壳；flex gap 8px（4px 刻度）；
 * 控件保持 antd 默认形态，随 ConfigProvider 设计令牌换肤（placeholder 字号/色由令牌承接）。
 */
const FilterBar: React.FC<FilterBarProps> = ({ searchPlaceholder, onSearch, filters = [], extra }) => (
  <div className="eakis-filterbar">
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
  </div>
);

export default FilterBar;
