# RAG知识库模块 - 研究发现

**开始时间**: 2026-04-13

---

## 1. 文档解析技术调研

### PDF解析方案

| 方案 | 优点 | 缺点 | 推荐 |
|------|------|------|------|
| PyPDF2 | 简单易用 | 功能有限 | ⭐ |
| pdfplumber | 表格提取好 | 速度慢 | ⭐⭐ |
| pymupdf | 速度快 | 依赖C库 | ⭐⭐⭐ |
| LangChain PDFLoader | 集成好 | 定制性差 | ⭐⭐ |

**结论**: 选用 `PyMuPDF` 作为主要解析器，辅以 `pdfplumber` 处理复杂表格

### Word解析方案

| 方案 | 优点 | 缺点 | 推荐 |
|------|------|------|------|
| python-docx | 纯Python | 格式有限 | ⭐⭐⭐ |
| docx2txt | 速度快 | 功能简单 | ⭐⭐ |

**结论**: 选用 `python-docx` 作为主要解析器

---

## 2. 分块策略研究

### 常用分块策略

1. **RecursiveCharacterTextSplitter** (LangChain默认)
   - 按字符数递归分割
   - 保留段落完整性
   - 适合通用场景

2. **TitleBasedTextSplitter** (自定义)
   - 按Markdown/HTML标题层级分割
   - 保持语义完整性
   - 适合结构化文档

3. **SemanticChunker** (高级)
   - 使用语义相似度判断分割点
   - 计算成本高
   - 适合高精度场景

**结论**: 实现前两种策略，支持可配置切换

---

## 3. 向量数据库选型

### 主流方案对比

| 数据库 | 部署方式 | 优点 | 缺点 | 推荐场景 |
|--------|----------|------|------|----------|
| ChromaDB | 本地/嵌入 | 简单轻量 | 扩展性一般 | 开发/小规模 ⭐⭐⭐ |
| Pinecone | 云服务 | 全托管 | 成本高 | 生产环境 ⭐⭐⭐ |
| Milvus | 自部署 | 功能强大 | 运维复杂 | 超大规模 ⭐⭐ |
| Weaviate | 混合 | 原生混合搜索 | 社区较小 | 混合检索 ⭐⭐⭐ |

**结论**: 采用 ChromaDB + Pinecone 双后端架构

---

## 4. 嵌入模型选型

| 模型 | 维度 | 效果 | 成本 | 推荐 |
|------|------|------|------|------|
| text-embedding-3-small | 1536 | ⭐⭐⭐ | 低 | ⭐⭐⭐ |
| text-embedding-3-large | 3072 | ⭐⭐⭐⭐ | 中 | ⭐⭐ |
| bge-m3 | 1024 | ⭐⭐⭐⭐ | 免费 | ⭐⭐⭐⭐ |
| mxbai-embed-large | 1024 | ⭐⭐⭐⭐ | 免费 | ⭐⭐⭐⭐ |

**结论**: 支持 OpenAI 和 BGE-M3，可配置切换

---

## 5. 混合检索方案

### BM25 vs 向量检索

| 维度 | BM25 | 向量检索 |
|------|------|----------|
| 语义理解 | ❌ | ✅ |
| 关键词匹配 | ✅ | ❌ |
| 扩展性 | ✅ | ✅ |
| 计算成本 | 低 | 高 |

**混合策略**: `score = α * vector_score + β * bm25_score`

### MMR (Maximal Marginal Relevance) 去重

原理: 在相关性和多样性之间取得平衡
公式: `MMR = argmax [λ * sim(q,doc) - (1-λ) * max(sim(doc_i,doc_j))]`

---

## 6. 定时任务方案

| 方案 | 优点 | 缺点 | 推荐 |
|------|------|------|------|
| APScheduler | 轻量 | 无分布式 | ⭐⭐⭐ |
| Celery Beat | 分布式 | 依赖Celery | ⭐⭐ |
| Cron | 简单 | 无持久化 | ⭐ |

**结论**: 选用 APScheduler，支持持久化调度

---

## 7. 依赖库清单

```toml
# pyproject.toml 新增依赖

# 文档解析
PyMuPDF = "^1.23.0"
pdfplumber = "^0.10.0"
python-docx = "^0.8.11"
markdown = "^3.5.0"
beautifulsoup4 = "^4.12.0"

# 向量数据库
chromadb = "^0.4.0"
pinecone-client = "^2.2.0"

# 混合检索
rank-bm25 = "^0.2.2"

# 嵌入模型
openai = "^1.0.0"
sentence-transformers = "^2.2.0"

# 定时任务
apscheduler = "^3.10.0"

# 数据库
aiosqlite = "^0.19.0"
```

---

**最后更新**: 2026-04-13
