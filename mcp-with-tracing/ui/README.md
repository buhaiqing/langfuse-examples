# MCP Langfuse Observability - Streamlit UI 使用指南

## 概述

这是一个基于 Streamlit 构建的监控仪表板，用于可视化展示 MCP Langfuse 可观测性平台的核心功能和数据。

## 功能特性

### 1. 🏠 系统总览
- 系统健康状态监控
- 组件状态卡片（Langfuse、告警管理器、监控调度器、智能告警、缓存）
- 快速指标概览（成功率、P95 延迟、请求率、用户满意度）
- 最近告警列表

### 2. 📊 实时指标监控
- 4 个核心指标的趋势图（成功率、延迟、QPS、满意度）
- 时间范围选择（1小时/6小时/24小时/7天）
- 交互式 Plotly 图表
- 当前指标值展示

### 3. 🚨 告警管理
- 告警规则列表与 CRUD 操作
- 触发历史查询与筛选
- ML 智能告警统计
- 告警统计分析（按严重性、按规则）

### 4. 💬 反馈分析
- 反馈统计卡片（总反馈数、接受率、平均评分）
- 评分分布柱状图
- 反馈类型饼图
- 接受/拒绝对比图
- 最新反馈列表与筛选

### 5. 📝 提示词版本管理
- 提示词列表（版本数、A/B 测试状态）
- 版本详情查看
- 注册新版本功能
- 元数据管理

### 6. ⚙️ 系统设置
- 健康检查详情
- 缓存管理与统计
- 环境变量查看（脱敏显示）
- 系统信息

## 快速开始

### 1. 安装依赖

```bash
cd mcp-with-tracing/ui
pip install -r requirements.txt

# 或使用 uv
uv pip install -r requirements.txt
```

### 2. 启动 UI

```bash
# 方式 1: 直接运行
cd mcp-with-tracing
streamlit run ui/app.py

# 方式 2: 使用 Makefile（如果已添加）
make ui
```

### 3. 访问仪表板

启动后，浏览器会自动打开 `http://localhost:8501`

## 配置要求

### 必需配置

确保 `.env` 文件已配置：

```bash
LANGFUSE_PUBLIC_KEY=pk-lf-xxx
LANGFUSE_SECRET_KEY=sk-lf-xxx
LANGFUSE_HOST=https://cloud.langfuse.com
```

### 可选配置

```bash
# 告警检查间隔
ALERT_CHECK_INTERVAL_MINUTES=5
SMART_ALERT_CHECK_INTERVAL_MINUTES=10

# 企业微信 Webhook（告警通知）
WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY
```

## 数据源

UI 直接导入项目模块获取数据，无需额外 API 层：

- `src/observability/health.py` - 健康状态
- `src/observability/metrics_collector.py` - 指标数据
- `src/observability/alerting.py` - 告警规则与历史
- `src/observability/smart_alerting.py` - ML 智能告警
- `src/observability/feedback.py` - 反馈数据
- `src/observability/prompt_versioning.py` - 提示词版本

## 架构设计

```
Streamlit UI (ui/)
    ↓ 直接导入
src/observability/ 模块
    ↓ 调用 Langfuse SDK
Langfuse Cloud/API
```

### 关键设计决策

1. **零 API 开发**: 直接导入项目模块
2. **复用缓存机制**: 使用 TTLCache 避免重复 API 调用
3. **只读展示为主**: 仅告警规则和提示词版本支持 CRUD
4. **独立运行**: 与 MCP Server 互不影响

## 常见问题

### Q: 数据未显示？
A: 检查 `.env` 配置是否正确，确保 Langfuse API Keys 有效。

### Q: 指标趋势图为空？
A: 需要 MCP Server 运行一段时间以积累数据。

### Q: 如何刷新数据？
A: 使用页面右上角的"手动刷新"按钮，或启用自动刷新。

### Q: 缓存如何管理？
A: 在"系统设置"页面可以查看缓存统计和清除缓存。

## 开发指南

### 目录结构

```
ui/
├── app.py                    # 主应用入口
├── pages/                    # 多页面应用
│   ├── 1_🏠_首页.py
│   ├── 2_📊_指标监控.py
│   ├── 3_🚨_告警管理.py
│   ├── 4_💬_反馈分析.py
│   ├── 5_📝_提示词版本.py
│   └── 6_⚙️_系统设置.py
├── components/               # 可复用 UI 组件（预留）
├── utils/                    # 工具函数
│   ├── data_loader.py        # 数据加载器
│   └── formatters.py         # 数据格式化
└── requirements.txt          # UI 依赖
```

### 添加新页面

1. 在 `ui/pages/` 目录创建新文件
2. 文件名格式: `N_🔥_页面名称.py`（N 为排序序号）
3. 使用 `st.set_page_config()` 配置页面
4. 从 `ui.utils.data_loader` 导入数据加载函数

### 添加新指标

1. 在 `src/observability/metrics_collector.py` 添加收集方法
2. 在 `ui/utils/data_loader.py` 添加数据加载函数
3. 在相应页面展示新指标

## 性能优化

- **TTL 缓存**: 指标数据默认缓存 5 分钟
- **按需加载**: 仅在页面切换时加载数据
- **数据分页**: 反馈列表支持分页显示
- **异步刷新**: 自动刷新不阻塞 UI

## 安全注意事项

1. **环境变量脱敏**: API Keys 在 UI 中部分隐藏
2. **只读访问**: 大部分数据为只读展示
3. **本地运行**: 默认仅本地访问，生产环境需添加认证

## 未来规划

- [ ] 用户认证（Streamlit 密码保护）
- [ ] 数据导出功能（CSV/Excel）
- [ ] 自定义仪表板布局
- [ ] 暗色主题支持
- [ ] 移动端响应式优化
- [ ] 实时 WebSocket 推送

## 技术支持

- **项目文档**: `../docs/`
- **API 参考**: `../manuals/`
- **问题反馈**: 提交 GitHub Issue

---

**版本**: v1.0  
**最后更新**: 2026-04-30  
**技术栈**: Streamlit 1.30+ + Plotly 5.18+ + Pandas 2.0+
