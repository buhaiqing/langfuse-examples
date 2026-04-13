# 后端测试用例开发计划

**日期**: 2026-04-13  
**目标**: 达到 90% + 单元测试覆盖率

---

## 测试覆盖清单

### 核心服务层测试 (6 个模块)

#### 1. 意图识别服务
- [ ] `test_intent_recognition.py` - 意图识别测试
- [ ] `test_text_preprocessing.py` - 文本预处理测试
- [ ] `test_entity_recognition.py` - 实体识别测试

#### 2. RAG 知识库服务
- [ ] `test_rag_service.py` - RAG 查询测试
- [ ] `test_document_importer.py` - 文档导入测试
- [ ] `test_query_rewriter.py` - 查询重写测试

#### 3. 工具调用服务
- [ ] `test_api_client.py` - API 客户端测试
- [ ] `test_adapters.py` - 适配器测试（Jira/Zendesk/账户/产品/监控）

#### 4. 对话状态管理
- [ ] `test_redis_client.py` - Redis 客户端测试
- [ ] `test_session_storage.py` - 会话存储测试

#### 5. 升级管理服务
- [ ] `test_escalation_service.py` - 升级检查测试
- [ ] `test_sentiment_analysis.py` - 情绪分析测试

#### 6. Langfuse 可观测性
- [ ] `test_langfuse_client.py` - Langfuse 客户端测试
- [ ] `test_tracing.py` - 追踪装饰器测试
- [ ] `test_scoring.py` - 评分体系测试

### API 层测试 (6 个路由)

#### 7. API 网关与中间件
- [ ] `test_auth_middleware.py` - 认证中间件测试
- [ ] `test_rate_limit.py` - 限流中间件测试

#### 8. API 路由测试
- [ ] `test_intent_routes.py` - 意图识别路由测试
- [ ] `test_rag_routes.py` - RAG 路由测试
- [ ] `test_tools_routes.py` - 工具调用路由测试
- [ ] `test_conversations_routes.py` - 会话管理路由测试
- [ ] `test_escalations_routes.py` - 升级管理路由测试
- [ ] `test_documents_routes.py` - 文档管理路由测试

### 集成测试

#### 9. 端到端测试
- [ ] `test_integration.py` - API 集成测试
- [ ] `test_e2e_workflow.py` - 完整工作流程测试

---

## 优先级

### P0 - 高优先级（必须完成）
1. 意图识别服务测试
2. API 网关中间件测试
3. 核心 API 路由测试

### P1 - 中优先级（应该完成）
1. RAG 服务测试
2. 工具调用测试
3. 升级管理测试

### P2 - 低优先级（可以延后）
1. 文档导入测试
2. Langfuse 追踪测试
3. 集成测试

---

## 测试框架配置

### pytest 配置 (已存在)
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
addopts = -v --tb=short
```

### 测试依赖
```
pytest>=7.0.0
pytest-asyncio>=0.21.0
pytest-cov>=4.0.0  # 覆盖率
httpx>=0.23.0      # HTTP 客户端 Mock
pytest-mock>=3.10.0
```

---

## 执行命令

### 运行所有测试
```bash
cd backend
pytest
```

### 运行特定模块测试
```bash
pytest tests/services/test_intent_recognition.py -v
pytest tests/api/test_auth_middleware.py -v
```

### 运行测试并生成覆盖率报告
```bash
pytest --cov=backend --cov-report=html
```

### 覆盖率目标
- 行覆盖率：> 90%
- 分支覆盖率：> 80%

---

**状态**: 📋 计划已制定，等待执行
