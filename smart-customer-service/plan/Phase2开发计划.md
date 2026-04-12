# 智能客服系统 Phase 2 开发计划

**项目名称**: Langfuse Smart Customer Service System
**版本**: 1.1.0
**制定日期**: 2026-04-13
**计划周期**: 8周 (40个工作日)

---

## 📋 目录

1. [计划概述](#计划概述)
2. [模块一: RAG知识库增强](#模块一-rag知识库增强)
3. [模块二: 工具API真实对接](#模块二-工具api真实对接)
4. [模块三: 对话状态持久化](#模块三-对话状态持久化)
5. [模块四: 人工客服系统集成](#模块四-人工客服系统集成)
6. [质量保障](#质量保障)
7. [里程碑](#里程碑)

---

## 计划概述

### 功能开发点总览

| 模块 | 功能点 | 优先级 | 工期 | 状态 |
|------|--------|--------|------|------|
| RAG知识库 | 文档导入与分块引擎 | P0 | 2天 | ⏸️ |
| RAG知识库 | 向量数据库集成 | P0 | 2天 | ⏸️ |
| RAG知识库 | 混合检索策略 | P1 | 2天 | ⏸️ |
| RAG知识库 | 知识库管理与增量更新 | P1 | 2天 | ⏸️ |
| 工具API | API客户端基础框架 | P0 | 2天 | ⏸️ |
| 工具API | 工单系统对接 | P0 | 2天 | ⏸️ |
| 工具API | 账户系统集成 | P0 | 2天 | ⏸️ |
| 工具API | 产品信息系统 | P1 | 2天 | ⏸️ |
| 工具API | 监控系统集成 | P1 | 2天 | ⏸️ |
| 状态持久化 | Redis会话存储 | P0 | 2天 | ⏸️ |
| 状态持久化 | 会话恢复与同步 | P0 | 2天 | ⏸️ |
| 状态持久化 | 会话清理与归档 | P1 | 2天 | ⏸️ |
| 人工客服 | WebSocket实时通信 | P0 | 2天 | ⏸️ |
| 人工客服 | 上下文传递与排队 | P0 | 2天 | ⏸️ |
| 人工客服 | 双向同步与协作 | P1 | 2天 | ⏸️ |

### 优先级说明

- **P0 (紧急)**: 核心功能，必须在第一阶段完成
- **P1 (重要)**: 增强功能，可在第二阶段完成
- **P2 (优化)**: 体验优化，可后续迭代

### 开发节奏

```
Week 1-2: P0核心功能开发 (RAG-01, TOOL-01, STATE-01, ESC-01)
Week 3-4: P0功能收尾 + P1功能启动 (RAG-02, TOOL-02, STATE-02, ESC-02)
Week 5-6: P1功能开发 (RAG-03, TOOL-03, STATE-03)
Week 7-8: P1功能收尾 + 集成测试 + 性能优化
```

---

## 模块一: RAG知识库增强

### RAG-01: 文档导入与分块引擎

**任务拆解**:

| 子任务 | 描述 | 预估工时 | 依赖 |
|--------|------|----------|------|
| RAG-01-1 | 设计文档解析接口，支持PDF/DOCX/MD/HTML四种格式 | 0.5天 | - |
| RAG-01-2 | 实现PyPDF2解析器，提取文本和元数据 | 0.5天 | RAG-01-1 |
| RAG-01-3 | 实现python-docx解析器 | 0.25天 | RAG-01-1 |
| RAG-01-4 | 实现RecursiveCharacterTextSplitter分块器 | 0.5天 | - |
| RAG-01-5 | 实现TitleBasedTextSplitter分块器 | 0.5天 | - |
| RAG-01-6 | 集成Langfuse追踪和评分 | 0.25天 | - |
| RAG-01-7 | 单元测试(覆盖率>90%) | 0.5天 | RAG-01-2~6 |
| RAG-01-8 | 安全检查与代码评审 | 0.25天 | RAG-01-7 |

**验收标准**:
- [ ] 支持4种文档格式解析
- [ ] 分块策略可配置
- [ ] 元数据完整保留
- [ ] 100页PDF处理<30秒

**文件变更**:
- 新增: `modules/rag_knowledge/document_loader.py`
- 新增: `modules/rag_knowledge/chunkers.py`
- 新增: `tests/test_document_loader.py`
- 新增: `tests/test_chunkers.py`

---

### RAG-02: 向量数据库集成与持久化

**任务拆解**:

| 子任务 | 描述 | 预估工时 | 依赖 |
|--------|------|----------|------|
| RAG-02-1 | 设计VectorStore抽象接口和适配器模式 | 0.5天 | - |
| RAG-02-2 | 实现ChromaDBAdapter本地向量存储 | 0.75天 | RAG-01 |
| RAG-02-3 | 实现PineconeAdapter云端向量存储 | 0.75天 | RAG-01 |
| RAG-02-4 | 实现嵌入生成服务(OpenAI/bge-m3) | 0.5天 | - |
| RAG-02-5 | 实现连接池管理 | 0.25天 | RAG-02-2 |
| RAG-02-6 | 集成Langfuse追踪 | 0.25天 | - |
| RAG-02-7 | 单元测试和性能测试 | 0.5天 | RAG-02-2~6 |
| RAG-02-8 | 安全检查与代码评审 | 0.25天 | RAG-02-7 |

**验收标准**:
- [ ] 支持ChromaDB和Pinecone双后端
- [ ] 支持增量更新
- [ ] 检索延迟<200ms
- [ ] 元数据过滤功能

**文件变更**:
- 新增: `modules/rag_knowledge/vector_store.py`
- 新增: `modules/rag_knowledge/adapters/`
- 新增: `tests/test_vector_store.py`

---

### RAG-03: 混合检索策略实现

**任务拆解**:

| 子任务 | 描述 | 预估工时 | 依赖 |
|--------|------|----------|------|
| RAG-03-1 | 设计混合检索接口和评分融合算法 | 0.5天 | - |
| RAG-03-2 | 实现BM25Retriever关键词检索器 | 0.5天 | - |
| RAG-03-3 | 实现HybridRetriever混合检索器 | 0.5天 | RAG-03-2 |
| RAG-03-4 | 实现MMRReranker去重器 | 0.5天 | RAG-03-3 |
| RAG-03-5 | 实现查询预处理(同义词/拼写纠错) | 0.25天 | - |
| RAG-03-6 | 集成Langfuse追踪 | 0.25天 | - |
| RAG-03-7 | A/B对比测试 | 0.5天 | RAG-03-4~6 |
| RAG-03-8 | 安全检查与代码评审 | 0.25天 | RAG-03-7 |

**验收标准**:
- [ ] 支持三种检索模式
- [ ] 混合检索相关性提升>15%
- [ ] 支持MMR去重

**文件变更**:
- 新增: `modules/rag_knowledge/retrieval_strategy.py`
- 新增: `modules/rag_knowledge/bm25_retriever.py`
- 新增: `tests/test_hybrid_retrieval.py`

---

### RAG-04: 知识库管理与增量更新

**任务拆解**:

| 子任务 | 描述 | 预估工时 | 依赖 |
|--------|------|----------|------|
| RAG-04-1 | 设计KnowledgeBaseManager接口 | 0.25天 | - |
| RAG-04-2 | 实现SQLite元数据存储 | 0.5天 | - |
| RAG-04-3 | 实现文档CRUD操作 | 0.5天 | RAG-04-2 |
| RAG-04-4 | 实现版本控制(历史版本保留) | 0.5天 | RAG-04-3 |
| RAG-04-5 | 实现APScheduler定时任务 | 0.25天 | - |
| RAG-04-6 | 实现增量更新(MD5对比) | 0.5天 | RAG-04-5 |
| RAG-04-7 | 集成Langfuse追踪 | 0.25天 | - |
| RAG-04-8 | 单元测试和回归测试 | 0.5天 | RAG-04-4~7 |
| RAG-04-9 | 安全检查与代码评审 | 0.25天 | RAG-04-8 |

**验收标准**:
- [ ] CRUD操作完整
- [ ] 版本历史保留
- [ ] 每日凌晨2点自动更新
- [ ] 统计信息API

**文件变更**:
- 新增: `modules/rag_knowledge/kb_manager.py`
- 新增: `modules/rag_knowledge/metadata_store.py`
- 新增: `tests/test_kb_manager.py`

---

## 模块二: 工具API真实对接

### TOOL-01: API客户端基础框架

**任务拆解**:

| 子任务 | 描述 | 预估工时 | 依赖 |
|--------|------|----------|------|
| TOOL-01-1 | 设计APIClient基类接口 | 0.25天 | - |
| TOOL-01-2 | 实现httpx异步HTTP客户端封装 | 0.5天 | - |
| TOOL-01-3 | 实现tenacity指数退避重试 | 0.5天 | TOOL-01-2 |
| TOOL-01-4 | 实现pybreaker熔断器 | 0.5天 | TOOL-01-3 |
| TOOL-01-5 | 实现请求/响应日志(脱敏) | 0.25天 | TOOL-01-2 |
| TOOL-01-6 | 实现健康检查方法 | 0.25天 | TOOL-01-4 |
| TOOL-01-7 | 集成Langfuse追踪 | 0.25天 | - |
| TOOL-01-8 | 单元测试(重试/熔断/超时) | 0.5天 | TOOL-01-3~7 |
| TOOL-01-9 | 安全检查与代码评审 | 0.25天 | TOOL-01-8 |

**验收标准**:
- [ ] 指数退避重试(最多3次)
- [ ] 熔断器(失败率>50%熔断30秒)
- [ ] 请求/响应日志
- [ ] API延迟<500ms

**文件变更**:
- 新增: `modules/tool_calling/api_client.py`
- 新增: `modules/tool_calling/circuit_breaker.py`
- 新增: `tests/test_api_client.py`

---

### TOOL-02: 工单系统对接(Jira/Zendesk)

**任务拆解**:

| 子任务 | 描述 | 预估工时 | 依赖 |
|--------|------|----------|------|
| TOOL-02-1 | 设计工单工具接口(Jira/Zendesk适配器) | 0.25天 | - |
| TOOL-02-2 | 实现JiraAdapter(Jira REST API) | 0.75天 | TOOL-01 |
| TOOL-02-3 | 实现ZendeskAdapter | 0.5天 | TOOL-01 |
| TOOL-02-4 | 实现TicketTool类(5个方法) | 0.5天 | TOOL-02-2 |
| TOOL-02-5 | 添加工具注册机制 | 0.25天 | TOOL-02-4 |
| TOOL-02-6 | 集成Langfuse追踪 | 0.25天 | - |
| TOOL-02-7 | 单元测试(Mock API响应) | 0.5天 | TOOL-02-3~6 |
| TOOL-02-8 | 安全检查与代码评审 | 0.25天 | TOOL-02-7 |

**验收标准**:
- [ ] 工单查询/创建/更新功能
- [ ] API成功率>95%
- [ ] 工单ID格式校验
- [ ] 429限流处理

**文件变更**:
- 新增: `modules/tool_calling/ticket_tools.py`
- 新增: `modules/tool_calling/adapters/jira_adapter.py`
- 新增: `modules/tool_calling/adapters/zendesk_adapter.py`
- 新增: `tests/test_ticket_tools.py`

---

### TOOL-03: 账户系统集成

**任务拆解**:

| 子任务 | 描述 | 预估工时 | 依赖 |
|--------|------|----------|------|
| TOOL-03-1 | 设计账户工具接口 | 0.25天 | - |
| TOOL-03-2 | 实现AccountAPIClient | 0.5天 | TOOL-01 |
| TOOL-03-3 | 实现账户状态查询 | 0.25天 | TOOL-03-2 |
| TOOL-03-4 | 实现密码重置(邮件/SMS) | 0.5天 | TOOL-03-3 |
| TOOL-03-5 | 实现信息修改(邮箱/手机) | 0.25天 | TOOL-03-3 |
| TOOL-03-6 | 添加审计日志 | 0.25天 | TOOL-03-4 |
| TOOL-03-7 | 集成Langfuse追踪 | 0.25天 | - |
| TOOL-03-8 | 安全测试(暴力破解防护) | 0.5天 | TOOL-03-4~7 |
| TOOL-03-9 | 安全检查与代码评审 | 0.25天 | TOOL-03-8 |

**验收标准**:
- [ ] 账户状态查询
- [ ] 密码重置(验证码5分钟有效)
- [ ] 敏感操作二次验证
- [ ] 审计日志完整

**文件变更**:
- 新增: `modules/tool_calling/account_tools.py`
- 新增: `tests/test_account_tools.py`

---

### TOOL-04: 产品信息系统集成

**任务拆解**:

| 子任务 | 描述 | 预估工时 | 依赖 |
|--------|------|----------|------|
| TOOL-04-1 | 设计产品工具接口 | 0.25天 | - |
| TOOL-04-2 | 实现ProductAPIClient | 0.5天 | TOOL-01 |
| TOOL-04-3 | 实现产品信息查询 | 0.25天 | TOOL-04-2 |
| TOOL-04-4 | 实现定价查询 | 0.25天 | TOOL-04-3 |
| TOOL-04-5 | 集成Redis缓存(TTL 24h) | 0.5天 | TOOL-04-3 |
| TOOL-04-6 | 实现缓存穿透保护 | 0.25天 | TOOL-04-5 |
| TOOL-04-7 | 集成Langfuse追踪 | 0.25天 | - |
| TOOL-04-8 | 单元测试(缓存逻辑) | 0.5天 | TOOL-04-5~7 |
| TOOL-04-9 | 安全检查与代码评审 | 0.25天 | TOOL-04-8 |

**验收标准**:
- [ ] 产品信息查询
- [ ] 定价对比
- [ ] 缓存命中率>80%
- [ ] 缓存预热机制

**文件变更**:
- 新增: `modules/tool_calling/product_tools.py`
- 新增: `tests/test_product_tools.py`

---

### TOOL-05: 监控系统集成

**任务拆解**:

| 子任务 | 描述 | 预估工时 | 依赖 |
|--------|------|----------|------|
| TOOL-05-1 | 设计监控工具接口 | 0.25天 | - |
| TOOL-05-2 | 实现PrometheusClient | 0.5天 | TOOL-01 |
| TOOL-05-3 | 实现GrafanaClient | 0.5天 | TOOL-01 |
| TOOL-05-4 | 实现MonitoringTool(状态/告警/健康度) | 0.5天 | TOOL-05-2 |
| TOOL-05-5 | 实现健康度评分算法 | 0.25天 | TOOL-05-4 |
| TOOL-05-6 | 集成Langfuse追踪 | 0.25天 | - |
| TOOL-05-7 | 单元测试(PromQL/健康度) | 0.5天 | TOOL-05-4~6 |
| TOOL-05-8 | 安全检查与代码评审 | 0.25天 | TOOL-05-7 |

**验收标准**:
- [ ] 服务状态查询
- [ ] 24小时告警列表
- [ ] 健康度评分(0-100)
- [ ] 数据新鲜度指标

**文件变更**:
- 新增: `modules/tool_calling/monitoring_tools.py`
- 新增: `tests/test_monitoring_tools.py`

---

## 模块三: 对话状态持久化

### STATE-01: Redis会话存储后端

**任务拆解**:

| 子任务 | 描述 | 预估工时 | 依赖 |
|--------|------|----------|------|
| STATE-01-1 | 设计SessionStore接口 | 0.25天 | - |
| STATE-01-2 | 实现Redis连接池管理 | 0.5天 | - |
| STATE-01-3 | 实现MessagePack序列化 | 0.25天 | - |
| STATE-01-4 | 实现LZ4压缩 | 0.25天 | STATE-01-3 |
| STATE-01-5 | 实现save_session/load_session | 0.5天 | STATE-01-4 |
| STATE-01-6 | 实现TTL过期管理 | 0.25天 | STATE-01-5 |
| STATE-01-7 | 集成Langfuse追踪 | 0.25天 | - |
| STATE-01-8 | 性能测试(<10ms延迟) | 0.5天 | STATE-01-5~7 |
| STATE-01-9 | 安全检查与代码评审 | 0.25天 | STATE-01-8 |

**验收标准**:
- [ ] 读写延迟<10ms
- [ ] MessagePack序列化
- [ ] LZ4压缩(节省50%空间)
- [ ] TTL可配置

**文件变更**:
- 新增: `modules/dialogue_manager/session_store.py`
- 新增: `tests/test_session_store.py`

---

### STATE-02: 会话恢复与上下文同步

**任务拆解**:

| 子任务 | 描述 | 预估工时 | 依赖 |
|--------|------|----------|------|
| STATE-02-1 | 设计SessionRecovery接口 | 0.25天 | - |
| STATE-02-2 | 实现会话加载逻辑 | 0.5天 | STATE-01 |
| STATE-02-3 | 实现上下文重建 | 0.5天 | STATE-02-2 |
| STATE-02-4 | 实现Langfuse Trace续传 | 0.5天 | STATE-02-3 |
| STATE-02-5 | 实现断点续聊 | 0.25天 | STATE-02-4 |
| STATE-02-6 | 集成Langfuse追踪 | 0.25天 | - |
| STATE-02-7 | 单元测试(恢复逻辑) | 0.5天 | STATE-02-4~6 |
| STATE-02-8 | 安全检查与代码评审 | 0.25天 | STATE-02-7 |

**验收标准**:
- [ ] 恢复成功率>99%
- [ ] 对话历史完整性100%
- [ ] 支持断点续聊

**文件变更**:
- 新增: `modules/dialogue_manager/session_recovery.py`
- 新增: `tests/test_session_recovery.py`

---

### STATE-03: 会话清理与归档

**任务拆解**:

| 子任务 | 描述 | 预估工时 | 依赖 |
|--------|------|----------|------|
| STATE-03-1 | 设计SessionCleanup接口 | 0.25天 | - |
| STATE-03-2 | 实现过期会话识别 | 0.25天 | - |
| STATE-03-3 | 集成MinIO客户端 | 0.5天 | - |
| STATE-03-4 | 实现归档流程(压缩+上传) | 0.5天 | STATE-03-3 |
| STATE-03-5 | 实现APScheduler定时清理 | 0.25天 | STATE-03-4 |
| STATE-03-6 | 集成脱敏(归档前) | 0.25天 | STATE-03-4 |
| STATE-03-7 | 集成Langfuse追踪 | 0.25天 | - |
| STATE-03-8 | 单元测试(清理/归档) | 0.5天 | STATE-03-5~7 |
| STATE-03-9 | 安全检查与代码评审 | 0.25天 | STATE-03-8 |

**验收标准**:
- [ ] 每日凌晨3点自动清理
- [ ] 归档到MinIO
- [ ] 清理后释放Redis空间
- [ ] 归档数据加密

**文件变更**:
- 新增: `modules/dialogue_manager/session_cleanup.py`
- 新增: `tests/test_session_cleanup.py`

---

## 模块四: 人工客服系统集成

### ESC-01: WebSocket实时通信

**任务拆解**:

| 子任务 | 描述 | 预估工时 | 依赖 |
|--------|------|----------|------|
| ESC-01-1 | 设计WebSocketClient接口 | 0.25天 | - |
| ESC-01-2 | 实现WebSocket连接管理 | 0.5天 | - |
| ESC-01-3 | 实现消息发送/接收 | 0.25天 | ESC-01-2 |
| ESC-01-4 | 实现指数退避重连(最多5次) | 0.5天 | ESC-01-3 |
| ESC-01-5 | 实现心跳检测(30秒间隔) | 0.25天 | ESC-01-4 |
| ESC-01-6 | 实现消息队列(防丢失) | 0.25天 | ESC-01-5 |
| ESC-01-7 | 集成Langfuse追踪 | 0.25天 | - |
| ESC-01-8 | 单元测试(重连/心跳) | 0.5天 | ESC-01-4~7 |
| ESC-01-9 | 安全检查与代码评审 | 0.25天 | ESC-01-8 |

**验收标准**:
- [ ] 连接稳定性>99%
- [ ] 消息延迟<100ms
- [ ] 断线自动重连
- [ ] WSS加密

**文件变更**:
- 新增: `modules/escalation/websocket_client.py`
- 新增: `tests/test_websocket.py`

---

### ESC-02: 上下文传递与排队管理

**任务拆解**:

| 子任务 | 描述 | 预估工时 | 依赖 |
|--------|------|----------|------|
| ESC-02-1 | 设计QueueManager接口 | 0.25天 | - |
| ESC-02-2 | 设计EscalationContext结构 | 0.25天 | - |
| ESC-02-3 | 实现优先级队列 | 0.5天 | - |
| ESC-02-4 | 实现入队/位置查询 | 0.25天 | ESC-02-3 |
| ESC-02-5 | 实现等待时间估算 | 0.25天 | ESC-02-4 |
| ESC-02-6 | 实现上下文打包 | 0.25天 | ESC-02-2 |
| ESC-02-7 | 集成Langfuse追踪 | 0.25天 | - |
| ESC-02-8 | 单元测试(优先级/等待时间) | 0.5天 | ESC-02-5~7 |
| ESC-02-9 | 安全检查与代码评审 | 0.25天 | ESC-02-8 |

**验收标准**:
- [ ] 上下文完整性100%
- [ ] VIP优先排队
- [ ] 等待时间准确率>80%

**文件变更**:
- 新增: `modules/escalation/queue_manager.py`
- 新增: `tests/test_queue_manager.py`

---

### ESC-03: 双向同步与协作模式

**任务拆解**:

| 子任务 | 描述 | 预估工时 | 依赖 |
|--------|------|----------|------|
| ESC-03-1 | 设计BidirectionalSync接口 | 0.25天 | - |
| ESC-03-2 | 实现客服消息同步 | 0.5天 | ESC-01 |
| ESC-03-3 | 实现答案推荐(RAG调用) | 0.5天 | - |
| ESC-03-4 | 实现Co-pilot协作模式 | 0.25天 | ESC-03-2 |
| ESC-03-5 | 实现Auto-pilot协作模式 | 0.25天 | ESC-03-4 |
| ESC-03-6 | 实现模式切换(交还机器人) | 0.25天 | ESC-03-5 |
| ESC-03-7 | 集成Langfuse追踪 | 0.25天 | - |
| ESC-03-8 | 协作流程集成测试 | 0.5天 | ESC-03-3~7 |
| ESC-03-9 | 安全检查与代码评审 | 0.25天 | ESC-03-8 |

**验收标准**:
- [ ] 客服消息实时同步
- [ ] 机器人推荐答案
- [ ] 支持模式切换

**文件变更**:
- 新增: `modules/escalation/bidirectional_sync.py`
- 新增: `tests/test_collaboration.py`

---

## 质量保障

### 开发规范遵循

每个子任务必须通过五阶段检查:

| 阶段 | 检查项 | 工具 |
|------|--------|------|
| Design | 接口设计评审 | - |
| Dev | 代码开发 | - |
| Test | 单元测试覆盖率>90% | pytest --cov |
| Review | 代码风格检查 | black/isort/ruff/mypy |
| Security | 安全扫描 | pip-audit |

### 自动化检查脚本

```bash
# scripts/quality_check.sh
#!/bin/bash
set -e

echo "=== Quality Checks ==="

# Format
black --check modules/ core/ analysis/ utils/
isort --check-only .

# Lint
ruff check .

# Type
mypy modules/ core/ analysis/ utils/

# Test
pytest tests/ --cov=modules --cov-report=term-missing

# Security
pip-audit
```

---

## 里程碑

| 里程碑 | 日期 | 完成标准 |
|--------|------|----------|
| M1: P0核心功能 | Week 2结束 | RAG-01, TOOL-01, STATE-01, ESC-01 可用 |
| M2: P0功能完整 | Week 4结束 | RAG-02, TOOL-02, STATE-02, ESC-02 可用 |
| M3: P1功能开发 | Week 6结束 | RAG-03, TOOL-03, STATE-03 可用 |
| M4: 集成测试 | Week 7结束 | 端到端测试通过 |
| M5: 性能优化 | Week 8结束 | 所有P0指标达标 |

---

## 附录: 任务依赖图

```
RAG-01 ─┬─> RAG-02 ─> RAG-03 ─> RAG-04
         │                        ↑
         └────────────────────────┘

TOOL-01 ─┬─> TOOL-02
         ├─> TOOL-03
         ├─> TOOL-04
         └─> TOOL-05

STATE-01 ─> STATE-02 ─> STATE-03

ESC-01 ──> ESC-02 ──> ESC-03
              ↑
              └────────────────┐
                                │
              RAG-02 ──────────┘
              (答案推荐)
```

---

**文档版本**: v1.0
**最后更新**: 2026-04-13
**维护人**: 开发团队
