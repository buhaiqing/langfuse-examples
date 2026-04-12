# Phase 2 模块1: RAG知识库增强 - 任务计划

**项目**: Langfuse Smart Customer Service System
**模块**: RAG知识库增强 (RAG-01 ~ RAG-04)
**开始时间**: 2026-04-13
**预计工期**: 8天 (4个子任务 × 2天)

---

## 目标
完成RAG知识库的四个子任务:
1. **RAG-01**: 文档导入与分块引擎
2. **RAG-02**: 向量数据库集成与持久化
3. **RAG-03**: 混合检索策略实现
4. **RAG-04**: 知识库管理与增量更新

---

## 当前阶段
**Phase**: 开发阶段 - 四个任务并发执行

---

## 四个子任务概览

| 任务 | 功能 | 优先级 | 状态 |
|------|------|--------|------|
| RAG-01 | 文档导入与分块引擎 | P0 | 🔄 进行中 |
| RAG-02 | 向量数据库集成 | P0 | 🔄 进行中 |
| RAG-03 | 混合检索策略 | P1 | 🔄 进行中 |
| RAG-04 | 知识库管理与增量更新 | P1 | 🔄 进行中 |

---

## 阶段1: RAG-01 文档导入与分块引擎

**目标**: 支持PDF/DOCX/MD/HTML四种格式文档解析和智能分块

### 验收标准
- [ ] 支持4种文档格式解析
- [ ] 分块策略可配置(recursive/title-based)
- [ ] 元数据完整保留
- [ ] 100页PDF处理<30秒

### 文件变更
- 新增: `modules/rag_knowledge/document_loader.py`
- 新增: `modules/rag_knowledge/chunkers.py`
- 新增: `tests/test_document_loader.py`
- 新增: `tests/test_chunkers.py`

### 开发任务
- [x] RAG-01-1: 设计文档解析接口
- [ ] RAG-01-2: 实现PyPDF2解析器
- [ ] RAG-01-3: 实现python-docx解析器
- [ ] RAG-01-4: 实现RecursiveCharacterTextSplitter
- [ ] RAG-01-5: 实现TitleBasedTextSplitter
- [ ] RAG-01-6: 集成Langfuse追踪
- [ ] RAG-01-7: 单元测试
- [ ] RAG-01-8: 安全检查与代码评审

---

## 阶段2: RAG-02 向量数据库集成

**目标**: 集成ChromaDB和Pinecone，实现向量嵌入和检索

### 验收标准
- [ ] 支持ChromaDB和Pinecone双后端
- [ ] 支持增量更新
- [ ] 检索延迟<200ms
- [ ] 元数据过滤功能

### 文件变更
- 新增: `modules/rag_knowledge/vector_store.py`
- 新增: `modules/rag_knowledge/adapters/`
- 新增: `tests/test_vector_store.py`

### 开发任务
- [ ] RAG-02-1: 设计VectorStore抽象接口
- [ ] RAG-02-2: 实现ChromaDBAdapter
- [ ] RAG-02-3: 实现PineconeAdapter
- [ ] RAG-02-4: 实现嵌入生成服务
- [ ] RAG-02-5: 实现连接池管理
- [ ] RAG-02-6: 集成Langfuse追踪
- [ ] RAG-02-7: 单元测试和性能测试
- [ ] RAG-02-8: 安全检查与代码评审

---

## 阶段3: RAG-03 混合检索策略

**目标**: 实现向量检索+BM25关键词检索+重排序的混合检索

### 验收标准
- [ ] 支持三种检索模式(vector/keyword/hybrid)
- [ ] 混合检索相关性提升>15%
- [ ] 支持MMR去重

### 文件变更
- 新增: `modules/rag_knowledge/retrieval_strategy.py`
- 新增: `modules/rag_knowledge/bm25_retriever.py`
- 新增: `tests/test_hybrid_retrieval.py`

### 开发任务
- [ ] RAG-03-1: 设计混合检索接口
- [ ] RAG-03-2: 实现BM25Retriever
- [ ] RAG-03-3: 实现HybridRetriever
- [ ] RAG-03-4: 实现MMRReranker
- [ ] RAG-03-5: 实现查询预处理
- [ ] RAG-03-6: 集成Langfuse追踪
- [ ] RAG-03-7: A/B对比测试
- [ ] RAG-03-8: 安全检查与代码评审

---

## 阶段4: RAG-04 知识库管理与增量更新

**目标**: 实现CRUD、版本管理、定时增量更新

### 验收标准
- [ ] CRUD操作完整
- [ ] 版本历史保留
- [ ] 每日凌晨2点自动更新
- [ ] 统计信息API

### 文件变更
- 新增: `modules/rag_knowledge/kb_manager.py`
- 新增: `modules/rag_knowledge/metadata_store.py`
- 新增: `tests/test_kb_manager.py`

### 开发任务
- [ ] RAG-04-1: 设计KnowledgeBaseManager接口
- [ ] RAG-04-2: 实现SQLite元数据存储
- [ ] RAG-04-3: 实现文档CRUD
- [ ] RAG-04-4: 实现版本控制
- [ ] RAG-04-5: 实现APScheduler定时任务
- [ ] RAG-04-6: 实现增量更新
- [ ] RAG-04-7: 集成Langfuse追踪
- [ ] RAG-04-8: 单元测试和回归测试
- [ ] RAG-04-9: 安全检查与代码评审

---

## 依赖关系

```
RAG-01 (文档导入)
    ↓
RAG-02 (向量存储) ← RAG-01完成后开始
    ↓
RAG-03 (混合检索) ← RAG-02完成后开始
    ↓
RAG-04 (增量更新) ← RAG-03完成后开始
```

---

## 错误记录

| 错误 | 尝试次数 | 解决方案 |
|------|----------|----------|
| - | - | - |

---

## 决策记录

| 决策 | 理由 |
|------|------|
| 采用适配器模式实现多向量库支持 | 便于扩展和维护 |
| 使用SQLite存储元数据 | 轻量级，无需额外服务 |

---

**最后更新**: 2026-04-13
