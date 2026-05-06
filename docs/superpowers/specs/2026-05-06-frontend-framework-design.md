# AttackScope AI 前端框架设计

**日期**: 2026-05-06
**状态**: 已确认
**范围**: 前端页面框架开发（骨架搭建）

## 1. 技术选型

| 类别 | 选择 | 理由 |
|------|------|------|
| 框架 | React 18 + TypeScript 5 | 生态丰富，社区支持强 |
| 构建工具 | Vite 6 | 快速 HMR，开箱即用 |
| UI 组件库 | Ant Design 5（暗色主题） | 企业级组件，与原型暗色风格一致 |
| 路由 | React Router 6 | 嵌套路由，SPA 标准 |
| 状态管理 | Zustand | 轻量，无 boilerplate |
| HTTP 客户端 | Axios | 拦截器支持好 |
| Mock 层 | MSW (Mock Service Worker) | Service Worker 层拦截，业务代码无感知 |

## 2. 项目结构

```
web/
├── public/
├── src/
│   ├── api/
│   │   ├── client.ts              # Axios 实例 + 拦截器
│   │   ├── mock/
│   │   │   ├── browser.ts         # MSW browser worker
│   │   │   ├── handlers.ts        # MSW request handlers
│   │   │   └── data/              # Mock JSON 数据文件
│   │   ├── tasks.ts
│   │   ├── keywords.ts
│   │   ├── assets.ts
│   │   ├── interfaces.ts
│   │   ├── vulnerabilities.ts
│   │   ├── reports.ts
│   │   └── system.ts
│   ├── components/
│   │   ├── Layout/
│   │   │   ├── AppLayout.tsx      # 主布局 (侧边栏 + 顶栏 + 内容区)
│   │   │   └── Sidebar.tsx        # 侧边栏导航
│   │   ├── AgentPipeline/         # Agent 五层流程管线
│   │   ├── MetricCard/            # 指标卡片
│   │   ├── AgentLog/              # 实时日志流
│   │   ├── RiskTag/               # 风险等级标签
│   │   └── StatusBadge/           # 状态徽章
│   ├── hooks/
│   │   ├── useTaskEvents.ts       # WebSocket 事件流
│   │   └── usePagination.ts       # 分页逻辑
│   ├── pages/
│   │   ├── Dashboard/             # 总览仪表盘
│   │   ├── Keywords/              # 关键词生成
│   │   ├── Assets/                # 资产关联
│   │   ├── Interfaces/            # 接口爬取
│   │   ├── Pentest/               # 自动渗透
│   │   ├── Reports/               # 报告中心
│   │   ├── Vulnerabilities/       # 漏洞库
│   │   └── Settings/              # 系统设置
│   ├── store/
│   │   ├── taskStore.ts           # 任务状态
│   │   └── appStore.ts            # 全局状态 (侧边栏、主题)
│   ├── types/
│   │   ├── api.ts                 # API 通用类型 (分页、错误)
│   │   ├── task.ts
│   │   ├── keyword.ts
│   │   ├── asset.ts
│   │   ├── interface.ts
│   │   └── vulnerability.ts
│   ├── router.tsx                 # 路由配置
│   ├── App.tsx                    # 应用入口
│   └── main.tsx                   # 渲染入口
├── .env.development               # VITE_API_MOCK=true
├── .env.production                # VITE_API_MOCK=false
├── index.html
├── package.json
├── tsconfig.json
└── vite.config.ts
```

## 3. 路由设计

```
/                       → Dashboard（总览仪表盘）
/keywords               → Keywords（关键词列表）
/keywords/:id           → 关键词详情
/assets                 → Assets（资产列表）
/assets/:id             → 资产详情（Drawer）
/interfaces             → Interfaces（接口列表）
/interfaces/:id         → 接口详情（Drawer）
/pentest                → Pentest（渗透测试状态）
/pentest/:id            → 渗透详情
/vulnerabilities        → Vulnerabilities（漏洞库）
/vulnerabilities/:id    → 漏洞详情（Drawer）
/reports                → Reports（报告列表）
/reports/:id            → 报告详情
/settings               → Settings（系统设置）
```

所有列表页统一使用 Ant Design Table + 筛选器 + 分页器。详情页使用 Drawer（抽屉）保持上下文。

## 4. 页面与 API 对接

| 页面 | API 端点 | 核心内容 |
|------|----------|----------|
| Dashboard | `GET /tasks/{id}` + WebSocket | 4 个指标卡片、Agent 流程管线、高风险资产表、实时日志 |
| Keywords | `GET/POST/DELETE /tasks/{id}/keywords` | 关键词表格（按类型分 tab）、增删操作、覆盖率统计 |
| Assets | `GET/PATCH /tasks/{id}/assets` + `GET .../export` | 筛选表格、详情抽屉（技术栈/端口/证书/漏洞）、导出 |
| Interfaces | `GET/PATCH /tasks/{id}/interfaces` | 接口表格、参数展示、优先级标记、爬取方法标识 |
| Pentest | WebSocket 事件流 | 渗透进度、实时日志、发现漏洞列表 |
| Vulnerabilities | `GET/PATCH /tasks/{id}/vulnerabilities` + `GET .../statistics` | 漏洞表格、证据展示（请求/响应）、CVSS 评分、状态流转 |
| Reports | `POST/GET /tasks/{id}/reports` + `GET .../download` | 生成触发、状态轮询、质量评分、PDF/MD 下载 |
| Settings | `GET/PUT /config/agents` + `GET /health` + `GET /metrics` | Agent 配置表单、系统健康状态、指标面板 |

## 5. 共享组件

### AppLayout
- 三层布局：可折叠侧边栏 + 顶栏（任务选择器、状态徽章）+ 内容区
- 侧边栏高亮当前路由，分组显示（核心流程 / 输出管理）

### AgentPipeline
- 五层 Agent 流程管线可视化
- 每层：图标 + 名称 + 描述 + 进度条 + 状态徽章
- 状态颜色：完成(绿) / 运行中(蓝，脉冲动画) / 等待(灰)

### MetricCard
- 指标卡片：标签 + 大号数值 + 变化量
- 趋势标识：↑ 绿色 / ↓ 红色

### AgentLog
- 实时日志流，等宽字体
- 三级颜色：✓ 成功(绿) / → 信息(蓝) / ! 警告(橙)
- 自动滚动到底部

### RiskTag
- 5 级风险标签：critical(深红) / high(红) / medium(橙) / low(绿) / info(蓝)

### StatusBadge
- 状态徽章：running / idle / completed / failed
- 运行中状态带脉冲动画

## 6. 数据流

### REST 请求流
```
Page Component → API Module (tasks.ts) → client.ts (Axios)
  → Mock 模式? → 是: MSW Handler 返回 Mock JSON
                  → 否: FastAPI Backend (http://localhost:8000)
```

### 实时事件流
```
WebSocket (/v1/tasks/{id}/events) → useTaskEvents hook → Zustand store → Component re-render
```

### Mock/API 双模式
- 环境变量 `VITE_API_MOCK=true` 启用 MSW
- `main.tsx` 中条件注册 MSW Service Worker
- 所有 Mock 数据放在 `api/mock/data/` 目录
- 生产环境直接请求 FastAPI，不加载 MSW

### 状态管理
- **全局 (Zustand)**：当前选中任务、侧边栏折叠状态
- **页面级**：组件内置 useState（表格筛选、分页）
- **服务端**：Axios + 自定义 hooks，不引入 React Query

## 7. Ant Design 主题配置

暗色主题，对齐原型 CSS 变量风格：

```typescript
{
  algorithm: theme.darkAlgorithm,
  token: {
    colorPrimary: '#378ADD',
    borderRadius: 6,
    fontSize: 13,
    colorBgContainer: '#1a1a2e',
    colorBgElevated: '#1a1a2e',
    colorBorderSecondary: '#2a2a4e',
  }
}
```

## 8. 实现边界

### 本次包含（框架层）
- Vite + React + TS 项目初始化与配置
- Ant Design 5 暗色主题配置
- AppLayout 布局（侧边栏 + 顶栏）
- React Router 全部路由
- 8 个页面骨架组件（基础内容展示）
- 6 个共享组件基础实现
- API client + TypeScript 类型定义（对齐 API 规范）
- MSW Mock 数据层（覆盖全部端点）
- Zustand store 基础结构
- WebSocket hook 骨架

### 本次不包含（后续迭代）
- 复杂业务逻辑实现
- 高级图表/可视化（ECharts 等）
- 完善的错误处理和重试机制
- 国际化 (i18n)
- 单元测试和 E2E 测试
- CI/CD 配置
- 性能优化（懒加载、虚拟列表）
- 真实 API 对接调试

## 9. 预计产出

约 45-50 个文件，涵盖：
- 配置文件 6 个
- TypeScript 类型定义 6 个
- API 层 9 个（含 Mock handlers 和 data）
- 共享组件 7 个
- 页面组件 8 个
- Hooks + Store + 路由 7 个
