# Langfuse Smart Customer Service System

基于Langfuse构建的智能客服系统,实现会话路径全链路追踪与高频失败问题分析。

## 🎯 核心价值

- **全链路可观测**: 打破智能客服会话黑盒,从进线到结束完整追踪
- **失败根因定位**: 标准化埋点体系,快速定位问题根因
- **数据驱动优化**: A/B测试验证,量化优化效果
- **降低人工成本**: 提升问题解决率,降低转接率

## 🚀 快速开始

### 方式一: 使用 Makefile (推荐)

```bash
# 1. 初始化项目(创建.env,安装依赖)
make setup

# 2. 编辑 .env 文件填入API密钥

# 3. 验证项目
make verify

# 4. 运行示例
make run-basic    # 基础追踪示例
make run-demo     # 完整客服流程
make run-tech     # 技术支持演示
make run-failure  # 失败分析演示
```

**其他常用命令:**
```bash
make test         # 运行测试
make lint         # 代码检查
make format       # 代码格式化
make clean        # 清理缓存
make help         # 查看所有命令
```

### 方式二: 手动安装

#### 1. 安装依赖

**使用 uv (推荐):**
```bash
uv sync
```

**或使用 pip:**
```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件,填入你的API密钥:

```env
LANGFUSE_PUBLIC_KEY=pk-lf-xxxxxxxxxxxxxxxxxxxx
LANGFUSE_SECRET_KEY=sk-lf-xxxxxxxxxxxxxxxxxxxx
LANGFUSE_HOST=https://cloud.langfuse.com

OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
```

获取Langfuse密钥:
- 访问 [Langfuse Cloud](https://cloud.langfuse.com)
- 注册账号并创建项目
- 在Project Settings中获取Public Key和Secret Key

### 3. 运行示例

**基础追踪示例:**
```bash
python examples/basic_tracing.py
```

**完整客服流程演示:**
```bash
python main.py
```

### 4. 查看追踪数据

访问 [Langfuse Dashboard](https://cloud.langfuse.com) 查看:
- Traces: 完整的会话链路
- Scores: 质量评分趋势
- Sessions: 用户会话历史

## 📁 项目结构

```
langfuse-smart-cs/
├── config/                  # 配置模块
│   └── settings.py         # 环境变量配置
├── core/                    # 核心追踪功能
│   ├── langfuse_client.py  # Langfuse客户端初始化
│   ├── tracing.py          # 追踪装饰器和工具
│   └── scoring.py          # 评分体系
├── modules/                 # 业务模块
│   ├── intent_recognition.py    # 意图识别
│   ├── rag_knowledge.py         # RAG知识库
│   ├── tool_calling.py          # 工具调用
│   ├── dialogue_manager.py      # 对话状态管理
│   └── escalation.py            # 转接管理
├── analysis/                # 分析模块(待实现)
│   ├── failure_analyzer.py      # 失败分析
│   ├── dashboard.py             # 仪表盘
│   └── ab_testing.py            # A/B测试
├── utils/                   # 工具函数
│   └── data_masking.py     # 数据脱敏
├── examples/                # 示例代码
│   └── basic_tracing.py    # 基础追踪示例
├── main.py                  # 主入口
├── requirements.txt         # Python依赖
└── README.md               # 本文档
```

## 🔑 核心概念

### Trace (追踪)
一次完整的用户会话,绑定session_id和user_id,包含所有交互环节。

### Span (跨度)
会话中的单个业务节点,如意图识别、RAG检索、工具调用等。

### Generation (生成)
每次LLM调用,自动记录Prompt、Completion、Token用量。

### Event (事件)
关键业务事件,如转接触发、用户差评等。

### Score (评分)
量化评估指标,支持NUMERIC、CATEGORICAL、BOOLEAN三种类型。

## 📊 评分体系

| 评分项 | 类型 | 说明 |
|-------|------|------|
| intent_confidence | NUMERIC | 意图识别置信度 (0-1) |
| retrieval_relevance | NUMERIC | RAG检索相关性 (0-1) |
| tool_success_rate | NUMERIC | 工具调用成功率 (0-1) |
| issue_resolved | BOOLEAN | 问题是否解决 |
| user_satisfaction | NUMERIC | 用户满意度 (1-5) |
| response_latency_ms | NUMERIC | 响应延迟 (毫秒) |
| failure_type | CATEGORICAL | 失败类型分类 |
| escalation_required | BOOLEAN | 是否需要转接 |

## 🛡️ 数据安全

系统内置敏感数据脱敏功能,自动处理:
- 手机号: `138****5678`
- 邮箱: `zh***@example.com`
- 身份证: `110101********1234`
- 用户ID: SHA-256哈希

## 💡 使用示例

### 基础追踪

```python
from core.tracing import trace_customer_service, create_span, score_trace

@trace_customer_service(
    name="api_error_troubleshooting",
    session_id="session_123",
    user_id="user_456"
)
async def handle_api_error(query: str):
    with create_span("intent_recognition") as span:
        intent = await recognize_intent(query)
        span.end(output_data={"intent": intent})

    score_trace("intent_confidence", 0.92)
    return "Response"
```

### 完整客服流程

```python
from main import SmartCustomerService

service = SmartCustomerService()

response = await service.handle_message(
    user_message="我的API返回403错误",
    session_id="session_001",
    user_id="user_123",
    metadata={"channel": "web_chat"}
)

print(response["response"])
print(f"Escalated: {response['escalated']}")
```

## 🔧 技术栈

- **Langfuse**: LLM应用可观测性平台
- **LangChain**: LLM应用开发框架
- **ChromaDB**: 向量数据库(RAG)
- **OpenAI GPT**: 大语言模型
- **Python 3.9+**: 编程语言

## 📈 最佳实践

### 1. Trace层级设计
- 一个用户会话 = 一个Trace
- 每个业务节点 = 一个Span
- 每次LLM调用 = Generation
- 关键事件 = Event
- 量化评估 = Score

### 2. 元数据规范
```python
metadata = {
    "channel": "web_chat",           # 渠道
    "customer_tier": "enterprise",   # 客户等级
    "product_version": "v2.3",       # 产品版本
    "processing_time_ms": 1200,      # 处理时间
}
```

### 3. 标签命名
- 使用小写和下划线: `tech_support`, `api_error`
- 保持标签集合一致性
- 避免过多标签(建议<10个/trace)

## 🐛 故障排查

### 问题: Traces未出现在Dashboard

**解决方案:**
1. 检查API密钥是否正确
2. 确认网络连接正常
3. 调用 `flush_traces()` 确保数据发送
4. 检查Langfuse项目设置中的环境过滤

### 问题: OpenAI API调用失败

**解决方案:**
1. 确认OPENAI_API_KEY已设置
2. 检查API配额是否充足
3. 验证网络连接(可能需要代理)

## 📝 许可证

MIT License

## 🔗 相关链接

- [Langfuse官方文档](https://langfuse.com/docs)
- [LangChain文档](https://python.langchain.com/)
- [项目Spec文档](specs/langfuse-smart-cs-analysis.md)

## 🤝 贡献

欢迎提交Issue和Pull Request!

---

**注意**: 本项目为演示版本,生产环境需要:
1. 实现真实的RAG知识库(当前为示例文档)
2. 集成真实的工具API(当前为Mock实现)
3. 添加数据库持久化(当前为内存存储)
4. 完善错误处理和重试机制
5. 添加认证和授权机制
