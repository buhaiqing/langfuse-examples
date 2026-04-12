"""
失败分析演示 - Failure Analysis Demo

本示例演示如何使用Langfuse进行客服系统的失败案例分析，包括:
1. 模拟生成失败案例数据 - 创建各种类型的失败trace
2. 调用failure_analyzer进行分析 - 多维度分析失败原因
3. 生成分析报告 - 输出结构化的分析结果
4. 根因下钻功能 - 深入分析特定失败类型

核心价值:
- 自动化失败检测：基于评分和标签自动识别失败案例
- 多维度根因分析：从意图、置信度、升级原因等角度分析
- 趋势洞察：识别失败模式和系统性问题
-  actionable建议：提供具体的优化方向

运行方式:
    python examples/failure_analysis_demo.py

注意:
- 即使没有真实的Langfuse API也能运行（使用mock模式）
- 所有分析结果都会打印到控制台
- 包含详细的注释说明每一步的作用
"""

import asyncio
import random
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

# ============================================================================
# Mock Langfuse Client (用于模拟数据生成)
# ============================================================================


class MockTrace:
    """模拟Langfuse Trace对象"""

    def __init__(
        self,
        trace_id: str,
        name: str,
        session_id: str,
        user_id: str,
        timestamp: datetime,
        tags: list[str],
        metadata: dict[str, Any],
        scores: dict[str, Any],
        spans: list[dict[str, Any]],
        input_data: dict[str, Any] = None,
        output_data: dict[str, Any] = None,
    ):
        self.id = trace_id
        self.name = name
        self.session_id = session_id
        self.user_id = user_id
        self.timestamp = timestamp
        self.tags = tags
        self.metadata = metadata
        self.scores = scores
        self.spans = spans
        self.input = input_data or {}
        self.output = output_data or {}

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "name": self.name,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags,
            "metadata": self.metadata,
            "scores": self.scores,
            "spans": self.spans,
            "input": self.input,
            "output": self.output,
        }


class MockFailureAnalyzer:
    """
    失败分析器 - 模拟实现

    在实际项目中，这会从Langfuse API获取真实数据进行分析
    这里使用模拟数据进行演示
    """

    def __init__(self):
        self.traces: list[MockTrace] = []

    def add_trace(self, trace: MockTrace):
        """添加trace到分析器"""
        self.traces.append(trace)

    def get_failure_traces(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        failure_types: list[str] | None = None,
    ) -> list[MockTrace]:
        """
        获取失败的traces

        失败定义:
        - issue_resolved = 0 (问题未解决)
        - escalation_required = 1 (需要升级)
        - intent_confidence < 0.5 (低置信度)

        Args:
            start_time: 开始时间
            end_time: 结束时间
            failure_types: 失败类型过滤

        Returns:
            List[MockTrace]: 失败的trace列表
        """
        failure_traces = []

        for trace in self.traces:
            # 时间过滤
            if start_time and trace.timestamp < start_time:
                continue
            if end_time and trace.timestamp > end_time:
                continue

            # 判断是否为失败案例
            is_failure = False
            failure_type = None

            scores = trace.scores

            # 规则1: 问题未解决
            if scores.get("issue_resolved") == 0:
                is_failure = True
                failure_type = "unresolved"

            # 规则2: 需要升级
            elif scores.get("escalation_required") == 1:
                is_failure = True
                failure_type = scores.get("escalation_reason", "unknown_escalation")

            # 规则3: 低置信度
            elif scores.get("intent_confidence", 1.0) < 0.5:
                is_failure = True
                failure_type = "low_confidence"

            # 规则4: 高延迟
            elif scores.get("response_latency_ms", 0) > 5000:
                is_failure = True
                failure_type = "high_latency"

            # 应用失败类型过滤
            if is_failure:
                if failure_types is None or failure_type in failure_types:
                    trace.metadata["failure_type"] = failure_type
                    failure_traces.append(trace)

        return failure_traces

    def analyze_failures(self, failure_traces: list[MockTrace]) -> dict[str, Any]:
        """
        分析失败案例

        分析维度:
        1. 失败类型分布
        2. 时间趋势
        3. 意图类型分布
        4. 渠道分布
        5. 用户情绪影响
        6. 平均处理时间

        Args:
            failure_traces: 失败的trace列表

        Returns:
            Dict: 分析结果
        """
        if not failure_traces:
            return {"total_failures": 0, "message": "没有找到失败案例"}

        # 初始化统计数据结构
        failure_type_dist = defaultdict(int)
        intent_dist = defaultdict(int)
        channel_dist = defaultdict(int)
        hourly_dist = defaultdict(int)
        sentiment_impact = {"negative": 0, "neutral": 0, "positive": 0}
        processing_times = []
        confidence_scores = []

        # 遍历所有失败trace进行统计
        for trace in failure_traces:
            # 失败类型分布
            failure_type = trace.metadata.get("failure_type", "unknown")
            failure_type_dist[failure_type] += 1

            # 意图类型分布
            intent = trace.metadata.get("intent", "unknown")
            intent_dist[intent] += 1

            # 渠道分布
            channel = trace.metadata.get("channel", "unknown")
            channel_dist[channel] += 1

            # 小时分布
            hour = trace.timestamp.hour
            hourly_dist[hour] += 1

            # 情绪影响
            sentiment = trace.metadata.get("sentiment", 0)
            if sentiment < -0.3:
                sentiment_impact["negative"] += 1
            elif sentiment > 0.3:
                sentiment_impact["positive"] += 1
            else:
                sentiment_impact["neutral"] += 1

            # 处理时间
            latency = trace.scores.get("response_latency_ms", 0)
            processing_times.append(latency)

            # 置信度
            confidence = trace.scores.get("intent_confidence", 0)
            confidence_scores.append(confidence)

        # 计算统计指标
        total = len(failure_traces)
        avg_processing_time = (
            sum(processing_times) / len(processing_times) if processing_times else 0
        )
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0

        # 生成分析结果
        analysis_result = {
            "summary": {
                "total_failures": total,
                "analysis_period": {
                    "start": min(t.timestamp for t in failure_traces).isoformat(),
                    "end": max(t.timestamp for t in failure_traces).isoformat(),
                },
                "avg_processing_time_ms": round(avg_processing_time, 2),
                "avg_intent_confidence": round(avg_confidence, 3),
            },
            "failure_type_distribution": dict(failure_type_dist),
            "intent_distribution": dict(intent_dist),
            "channel_distribution": dict(channel_dist),
            "hourly_distribution": dict(sorted(hourly_dist.items())),
            "sentiment_impact": sentiment_impact,
            "top_failed_sessions": [
                {
                    "session_id": t.session_id,
                    "failure_type": t.metadata.get("failure_type"),
                    "intent": t.metadata.get("intent"),
                    "timestamp": t.timestamp.isoformat(),
                    "user_message_preview": t.input.get("user_message", "")[:50],
                }
                for t in sorted(failure_traces, key=lambda x: x.timestamp, reverse=True)[:10]
            ],
        }

        return analysis_result

    def generate_report(self, analysis_result: dict[str, Any]) -> str:
        """
        生成可读的分析报告

        Args:
            analysis_result: 分析结果字典

        Returns:
            str: 格式化的报告文本
        """
        lines = []

        # 标题
        lines.append("=" * 70)
        lines.append("📊 失败案例分析报告")
        lines.append("=" * 70)
        lines.append("")

        # 概要信息
        summary = analysis_result.get("summary", {})
        lines.append("【概要信息】")
        lines.append(f"  • 失败案例总数: {summary.get('total_failures', 0)}")
        lines.append(
            f"  • 分析时间段: {summary.get('analysis_period', {}).get('start', 'N/A')} ~ {summary.get('analysis_period', {}).get('end', 'N/A')}"
        )
        lines.append(f"  • 平均处理时间: {summary.get('avg_processing_time_ms', 0):.0f}ms")
        lines.append(f"  • 平均意图置信度: {summary.get('avg_intent_confidence', 0):.3f}")
        lines.append("")

        # 失败类型分布
        lines.append("【失败类型分布】")
        failure_dist = analysis_result.get("failure_type_distribution", {})
        total = summary.get("total_failures", 1)
        for failure_type, count in sorted(failure_dist.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total) * 100
            bar = "█" * int(percentage / 2)
            lines.append(f"  • {failure_type:<25} {count:>3} ({percentage:>5.1f}%) {bar}")
        lines.append("")

        # 意图类型分布
        lines.append("【意图类型分布】")
        intent_dist = analysis_result.get("intent_distribution", {})
        for intent, count in sorted(intent_dist.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total) * 100
            lines.append(f"  • {intent:<30} {count:>3} ({percentage:>5.1f}%)")
        lines.append("")

        # 渠道分布
        lines.append("【渠道分布】")
        channel_dist = analysis_result.get("channel_distribution", {})
        for channel, count in sorted(channel_dist.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total) * 100
            lines.append(f"  • {channel:<20} {count:>3} ({percentage:>5.1f}%)")
        lines.append("")

        # 情绪影响
        lines.append("【用户情绪影响】")
        sentiment = analysis_result.get("sentiment_impact", {})
        for emotion, count in sentiment.items():
            percentage = (count / total) * 100 if total > 0 else 0
            emoji = {"negative": "😞", "neutral": "😐", "positive": "😊"}.get(emotion, "")
            lines.append(f"  • {emoji} {emotion:<10} {count:>3} ({percentage:>5.1f}%)")
        lines.append("")

        # 时段分布
        lines.append("【时段分布（按小时）】")
        hourly_dist = analysis_result.get("hourly_distribution", {})
        for hour, count in sorted(hourly_dist.items()):
            bar = "▓" * count
            lines.append(f"  • {hour:02d}:00  {count:>3} {bar}")
        lines.append("")

        # Top失败会话
        lines.append("【Top 10 最近失败会话】")
        top_sessions = analysis_result.get("top_failed_sessions", [])
        for i, session in enumerate(top_sessions, 1):
            lines.append(f"  {i}. Session: {session['session_id']}")
            lines.append(f"     失败类型: {session['failure_type']}")
            lines.append(f"     意图: {session['intent']}")
            lines.append(f"     时间: {session['timestamp']}")
            lines.append(f"     用户消息: {session['user_message_preview']}...")
            lines.append("")

        # 优化建议
        lines.append("=" * 70)
        lines.append("💡 优化建议")
        lines.append("=" * 70)
        lines.extend(self._generate_recommendations(analysis_result))
        lines.append("")

        return "\n".join(lines)

    def _generate_recommendations(self, analysis_result: dict[str, Any]) -> list[str]:
        """
        基于分析结果生成优化建议

        Args:
            analysis_result: 分析结果

        Returns:
            List[str]: 建议列表
        """
        recommendations = []

        failure_dist = analysis_result.get("failure_type_distribution", {})
        intent_dist = analysis_result.get("intent_distribution", {})
        avg_confidence = analysis_result.get("summary", {}).get("avg_intent_confidence", 1.0)

        # 建议1: 针对高频失败类型
        if "user_requested" in failure_dist and failure_dist["user_requested"] > 5:
            recommendations.append(
                "🔧 [优先级: 高] 用户主动转人工比例较高\n"
                "   建议: 优化对话流程，增加澄清问题环节，减少用户挫败感"
            )

        if "low_confidence" in failure_dist and failure_dist["low_confidence"] > 3:
            recommendations.append(
                "🔧 [优先级: 高] 低置信度失败较多\n"
                "   建议: 扩充训练数据，优化意图识别模型，增加fallback策略"
            )

        if "max_turns_exceeded" in failure_dist:
            recommendations.append(
                "🔧 [优先级: 中] 存在多轮对话仍未解决的案例\n"
                "   建议: 设置更早的升级触发点，避免用户长时间等待"
            )

        # 建议2: 针对特定意图
        problematic_intents = [
            intent
            for intent, count in intent_dist.items()
            if count > 3 and intent != "request_human_agent"
        ]
        if problematic_intents:
            recommendations.append(
                f"📚 [优先级: 中] 以下意图类型失败率较高: {', '.join(problematic_intents)}\n"
                f"   建议: 针对这些意图补充知识库内容，优化响应模板"
            )

        # 建议3: 置信度整体偏低
        if avg_confidence < 0.7:
            recommendations.append(
                "🎯 [优先级: 高] 整体意图置信度偏低\n"
                "   建议: 重新评估意图分类模型，考虑引入更多特征或调整阈值"
            )

        # 建议4: 通用建议
        recommendations.append(
            "📊 [优先级: 持续] 建立定期失败分析机制\n"
            "   建议: 每周运行此分析，跟踪改进效果，持续优化系统"
        )

        return recommendations

    def drill_down_by_root_cause(self, failure_type: str, limit: int = 5) -> dict[str, Any]:
        """
        根因下钻分析

        针对特定失败类型进行深入分析，提取典型案例

        Args:
            failure_type: 失败类型
            limit: 返回的案例数量

        Returns:
            Dict: 下钻分析结果
        """
        # 筛选指定失败类型的traces
        filtered_traces = [t for t in self.traces if t.metadata.get("failure_type") == failure_type]

        if not filtered_traces:
            return {
                "failure_type": failure_type,
                "total_cases": 0,
                "message": f"未找到类型为 '{failure_type}' 的失败案例",
            }

        # 提取共同特征
        intents = defaultdict(int)
        channels = defaultdict(int)
        sentiments = []

        for trace in filtered_traces:
            intents[trace.metadata.get("intent", "unknown")] += 1
            channels[trace.metadata.get("channel", "unknown")] += 1
            sentiments.append(trace.metadata.get("sentiment", 0))

        avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0

        # 选择典型案例
        typical_cases = []
        for trace in filtered_traces[:limit]:
            case = {
                "session_id": trace.session_id,
                "timestamp": trace.timestamp.isoformat(),
                "user_message": trace.input.get("user_message", ""),
                "bot_response": trace.output.get("response", "")[:200] if trace.output else "",
                "intent": trace.metadata.get("intent"),
                "confidence": trace.scores.get("intent_confidence"),
                "turn_count": trace.metadata.get("turn_count"),
                "sentiment": trace.metadata.get("sentiment"),
            }
            typical_cases.append(case)

        result = {
            "failure_type": failure_type,
            "total_cases": len(filtered_traces),
            "intent_distribution": dict(intents),
            "channel_distribution": dict(channels),
            "avg_sentiment": round(avg_sentiment, 3),
            "typical_cases": typical_cases,
            "root_cause_analysis": self._analyze_root_cause(failure_type, filtered_traces),
        }

        return result

    def _analyze_root_cause(self, failure_type: str, traces: list[MockTrace]) -> str:
        """
        根因分析 - 基于失败类型给出可能的根本原因

        Args:
            failure_type: 失败类型
            traces: 相关traces

        Returns:
            str: 根因分析文本
        """
        analyses = {
            "user_requested": (
                "根因分析: 用户主动要求转人工\n"
                "可能原因:\n"
                "  1. 机器人回答不够精准，用户失去耐心\n"
                "  2. 问题本身复杂，超出机器人能力范围\n"
                "  3. 用户偏好人工服务（某些场景下）\n"
                "建议措施:\n"
                "  - 优化响应质量，提供更具体、可操作的建议\n"
                "  - 在对话早期主动询问是否需要人工帮助\n"
                "  - 分析高频转人工的问题类型，针对性优化"
            ),
            "low_confidence": (
                "根因分析: 意图识别置信度过低\n"
                "可能原因:\n"
                "  1. 用户表达方式多样化，训练数据覆盖不足\n"
                "  2. 新出现的问题类型，模型未学习过\n"
                "  3. 用户输入模糊或不完整\n"
                "建议措施:\n"
                "  - 收集低置信度案例，扩充训练数据集\n"
                "  - 实现主动澄清机制，引导用户明确表达\n"
                "  - 考虑引入few-shot learning提升泛化能力"
            ),
            "max_turns_exceeded": (
                "根因分析: 对话轮次超过阈值\n"
                "可能原因:\n"
                "  1. 问题需要多轮澄清才能理解\n"
                "  2. 机器人未能有效推进对话\n"
                "  3. 用户在多个问题间切换\n"
                "建议措施:\n"
                "  - 优化对话管理策略，更快收敛到核心问题\n"
                "  - 设置更智能的轮次阈值（根据问题复杂度动态调整）\n"
                "  - 在第3轮后主动提供转人工选项"
            ),
            "negative_sentiment": (
                "根因分析: 用户情绪负面触发升级\n"
                "可能原因:\n"
                "  1. 之前的交互体验不佳\n"
                "  2. 问题紧急且未得到及时响应\n"
                "  3. 用户对自动化服务有抵触\n"
                "建议措施:\n"
                "  - 实现情绪实时监控，负面情绪早期干预\n"
                "  - 为负面情绪用户提供优先转人工通道\n"
                "  - 优化语气和表达方式，增强共情能力"
            ),
            "unresolved": (
                "根因分析: 问题未解决\n"
                "可能原因:\n"
                "  1. 知识库缺少相关解决方案\n"
                "  2. 工具调用失败或返回空结果\n"
                "  3. 响应质量不高，用户不满意\n"
                "建议措施:\n"
                "  - 定期更新知识库，补充常见问题\n"
                "  - 加强工具调用的错误处理和重试机制\n"
                "  - 引入用户反馈机制，持续优化响应质量"
            ),
        }

        return analyses.get(
            failure_type,
            f"根因分析: 未知失败类型 '{failure_type}'\n建议: 手动分析此类案例，确定根本原因",
        )

    def print_drill_down_report(self, drill_result: dict[str, Any]):
        """
        打印根因下钻报告

        Args:
            drill_result: 下钻分析结果
        """
        lines = []

        lines.append("\n" + "=" * 70)
        lines.append(f"🔍 根因下钻分析: {drill_result['failure_type']}")
        lines.append("=" * 70)
        lines.append("")

        if drill_result.get("message"):
            lines.append(f"⚠️  {drill_result['message']}")
            print("\n".join(lines))
            return

        lines.append(f"案例总数: {drill_result['total_cases']}")
        lines.append(f"平均情绪分数: {drill_result.get('avg_sentiment', 0):.3f}")
        lines.append("")

        # 意图分布
        lines.append("【意图分布】")
        for intent, count in drill_result.get("intent_distribution", {}).items():
            lines.append(f"  • {intent}: {count}")
        lines.append("")

        # 渠道分布
        lines.append("【渠道分布】")
        for channel, count in drill_result.get("channel_distribution", {}).items():
            lines.append(f"  • {channel}: {count}")
        lines.append("")

        # 根因分析
        lines.append("【根因分析】")
        lines.append(drill_result.get("root_cause_analysis", "无"))
        lines.append("")

        # 典型案例
        lines.append("【典型案例】")
        cases = drill_result.get("typical_cases", [])
        for i, case in enumerate(cases, 1):
            lines.append(f"\n  案例 {i}:")
            lines.append(f"    Session ID: {case['session_id']}")
            lines.append(f"    时间: {case['timestamp']}")
            lines.append(f"    用户消息: {case['user_message']}")
            lines.append(f"    意图: {case['intent']} (置信度: {case['confidence']})")
            lines.append(f"    对话轮次: {case['turn_count']}")
            lines.append(f"    情绪分数: {case['sentiment']}")
            if case["bot_response"]:
                lines.append(f"    机器人响应: {case['bot_response'][:100]}...")

        lines.append("")

        print("\n".join(lines))


# ============================================================================
# 模拟数据生成器
# ============================================================================


def generate_mock_failure_data(analyzer: MockFailureAnalyzer, num_cases: int = 50):
    """
    生成模拟的失败案例数据

    生成各种类型的失败案例，用于演示分析功能

    Args:
        analyzer: 失败分析器实例
        num_cases: 生成的案例数量
    """
    print(f"\n{'='*70}")
    print(f"📝 生成模拟失败案例数据 ({num_cases} 个案例)")
    print(f"{'='*70}\n")

    # 定义失败类型及其权重
    failure_scenarios = [
        {
            "type": "user_requested",
            "weight": 0.30,
            "intents": ["general_inquiry", "api_error_troubleshooting", "general_technical_issue"],
            "channels": ["web_chat", "mobile_app", "phone"],
            "sentiment_range": (-0.8, 0.3),
        },
        {
            "type": "low_confidence",
            "weight": 0.25,
            "intents": ["general_inquiry", "product_information", "general_technical_issue"],
            "channels": ["web_chat", "mobile_app"],
            "sentiment_range": (-0.5, 0.5),
        },
        {
            "type": "max_turns_exceeded",
            "weight": 0.20,
            "intents": ["api_error_troubleshooting", "general_technical_issue"],
            "channels": ["web_chat"],
            "sentiment_range": (-0.6, 0.2),
        },
        {
            "type": "negative_sentiment",
            "weight": 0.15,
            "intents": ["api_error_troubleshooting", "ticket_status_query"],
            "channels": ["web_chat", "phone"],
            "sentiment_range": (-0.9, -0.5),
        },
        {
            "type": "unresolved",
            "weight": 0.10,
            "intents": ["product_information", "general_inquiry"],
            "channels": ["web_chat", "mobile_app", "email"],
            "sentiment_range": (-0.3, 0.3),
        },
    ]

    # 示例用户消息模板
    message_templates = {
        "api_error_troubleshooting": [
            "API调用返回{error_code}错误",
            "接口请求失败，错误码{error_code}",
            "调用API时出现{error_code}异常",
            "为什么我的API请求被拒绝？",
        ],
        "ticket_status_query": [
            "查询工单{ticket_id}的状态",
            "工单{ticket_id}处理得怎么样了？",
            "帮我看看{ticket_id}这个工单",
            "{ticket_id}的进度如何？",
        ],
        "general_technical_issue": [
            "系统出问题了",
            "功能无法正常使用",
            "遇到一个技术问题",
            "服务好像有问题",
        ],
        "product_information": [
            "介绍一下{product}产品",
            "{product}有什么功能？",
            "想了解{product}的详细信息",
            "{product}的价格是多少？",
        ],
        "general_inquiry": [
            "怎么使用这个功能？",
            "有个问题想咨询",
            "能帮我解答一下吗？",
            "我不太明白这个怎么用",
        ],
        "request_human_agent": ["我要转人工客服", "给我接人工", "我需要人工帮助", "转人工"],
    }

    base_time = datetime.now() - timedelta(hours=48)

    for i in range(num_cases):
        # 随机选择失败场景
        scenario = random.choices(
            failure_scenarios, weights=[s["weight"] for s in failure_scenarios], k=1
        )[0]

        # 生成随机属性
        intent = random.choice(scenario["intents"])
        channel = random.choice(scenario["channels"])
        sentiment = round(random.uniform(*scenario["sentiment_range"]), 2)
        confidence = round(
            (
                random.uniform(0.3, 0.6)
                if scenario["type"] == "low_confidence"
                else random.uniform(0.6, 0.95)
            ),
            3,
        )
        turn_count = (
            random.randint(1, 8)
            if scenario["type"] == "max_turns_exceeded"
            else random.randint(1, 5)
        )
        processing_time = round(random.uniform(100, 3000), 0)

        # 生成时间戳（分布在48小时内）
        timestamp = base_time + timedelta(
            hours=random.randint(0, 47),
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59),
        )

        # 生成用户消息
        template = random.choice(message_templates.get(intent, ["我有一个问题"]))
        user_message = template.format(
            error_code=random.choice(["403", "404", "500", "502"]),
            ticket_id=f"TKT-{random.randint(10000, 99999)}",
            product=random.choice(["产品A", "产品B", "产品C"]),
        )

        # 创建trace
        trace_id = f"trace_failure_{i+1:03d}"
        session_id = f"session_failure_{i+1:03d}"
        user_id = f"user_{random.randint(1000, 9999)}"

        # 构建scores
        scores = {
            "intent_confidence": confidence,
            "issue_resolved": 0 if scenario["type"] == "unresolved" else 1,
            "escalation_required": 1 if scenario["type"] != "unresolved" else 0,
            "response_latency_ms": processing_time,
        }

        if scenario["type"] in [
            "user_requested",
            "low_confidence",
            "max_turns_exceeded",
            "negative_sentiment",
        ]:
            scores["escalation_reason"] = scenario["type"]

        # 构建metadata
        metadata = {
            "channel": channel,
            "intent": intent,
            "sentiment": sentiment,
            "turn_count": turn_count,
            "customer_tier": random.choice(["standard", "premium", "enterprise"]),
            "product_version": "v2.3",
        }

        # 构建spans（简化版）
        spans = [
            {"name": "step_1_intent_recognition", "duration_ms": random.uniform(50, 200)},
            {"name": "step_2_state_update", "duration_ms": random.uniform(10, 50)},
            {"name": "step_3_escalation_evaluation", "duration_ms": random.uniform(20, 100)},
            {"name": "step_4_response_generation", "duration_ms": random.uniform(100, 1500)},
        ]

        # 创建MockTrace
        trace = MockTrace(
            trace_id=trace_id,
            name="customer_service_interaction",
            session_id=session_id,
            user_id=user_id,
            timestamp=timestamp,
            tags=["tech_support", channel, "failure_case"],
            metadata=metadata,
            scores=scores,
            spans=spans,
            input_data={"user_message": user_message},
            output_data={
                "response": "这是模拟的响应内容...",
                "escalated": scenario["type"] != "unresolved",
            },
        )

        analyzer.add_trace(trace)

        if (i + 1) % 10 == 0:
            print(f"  ✓ 已生成 {i + 1}/{num_cases} 个案例")

    print(f"\n✓ 成功生成 {num_cases} 个模拟失败案例")
    print("  失败类型分布:")
    for scenario in failure_scenarios:
        count = sum(
            1 for t in analyzer.traces if t.metadata.get("failure_type") == scenario["type"]
        )
        print(f"    - {scenario['type']}: {count} 个")


# ============================================================================
# 演示函数
# ============================================================================


async def demo_1_generate_and_analyze():
    """
    演示1: 生成数据并执行基础分析

    展示:
    - 如何生成模拟失败案例数据
    - 如何调用分析器获取失败traces
    - 如何执行多维度分析
    - 如何生成和查看分析报告
    """
    print("\n" + "=" * 70)
    print("📌 演示1: 生成数据并执行基础分析")
    print("=" * 70)
    print("\n本演示将展示:")
    print("  1. 生成50个模拟失败案例")
    print("  2. 从所有案例中筛选出失败案例")
    print("  3. 执行多维度分析")
    print("  4. 生成完整的分析报告")
    print("=" * 70)

    # 创建分析器
    analyzer = MockFailureAnalyzer()

    # 生成模拟数据
    generate_mock_failure_data(analyzer, num_cases=50)

    # 获取失败traces
    print(f"\n{'─'*70}")
    print("🔍 步骤1: 筛选失败案例")
    print(f"{'─'*70}")

    failure_traces = analyzer.get_failure_traces()
    print(f"  总trace数: {len(analyzer.traces)}")
    print(f"  失败trace数: {len(failure_traces)}")
    print(f"  失败率: {len(failure_traces) / len(analyzer.traces) * 100:.1f}%")

    # 执行分析
    print(f"\n{'─'*70}")
    print("📊 步骤2: 执行多维度分析")
    print(f"{'─'*70}")

    analysis_result = analyzer.analyze_failures(failure_traces)
    print("  ✓ 分析完成")
    print("  分析维度包括:")
    print("    - 失败类型分布")
    print("    - 意图类型分布")
    print("    - 渠道分布")
    print("    - 时段分布")
    print("    - 情绪影响分析")
    print("    - 处理时间统计")

    # 生成报告
    print(f"\n{'─'*70}")
    print("📄 步骤3: 生成分析报告")
    print(f"{'─'*70}")

    report = analyzer.generate_report(analysis_result)
    print(report)


async def demo_2_filter_by_failure_type():
    """
    演示2: 按失败类型过滤分析

    展示:
    - 如何针对特定失败类型进行分析
    - 对比不同失败类型的特征
    """
    print("\n" + "=" * 70)
    print("📌 演示2: 按失败类型过滤分析")
    print("=" * 70)
    print("\n本演示将展示:")
    print("  1. 针对'user_requested'类型进行分析")
    print("  2. 针对'low_confidence'类型进行分析")
    print("  3. 对比两种失败类型的差异")
    print("=" * 70)

    # 创建分析器并生成数据
    analyzer = MockFailureAnalyzer()
    generate_mock_failure_data(analyzer, num_cases=40)

    # 分析user_requested类型
    print(f"\n{'─'*70}")
    print("🔍 分析 'user_requested' 类型失败")
    print(f"{'─'*70}")

    user_requested_traces = analyzer.get_failure_traces(failure_types=["user_requested"])
    print(f"  找到 {len(user_requested_traces)} 个案例")

    if user_requested_traces:
        result = analyzer.analyze_failures(user_requested_traces)
        report = analyzer.generate_report(result)
        print(report)

    # 分析low_confidence类型
    print(f"\n{'─'*70}")
    print("🔍 分析 'low_confidence' 类型失败")
    print(f"{'─'*70}")

    low_conf_traces = analyzer.get_failure_traces(failure_types=["low_confidence"])
    print(f"  找到 {len(low_conf_traces)} 个案例")

    if low_conf_traces:
        result = analyzer.analyze_failures(low_conf_traces)
        report = analyzer.generate_report(result)
        print(report)


async def demo_3_root_cause_drill_down():
    """
    演示3: 根因下钻分析

    展示:
    - 如何对特定失败类型进行深入分析
    - 查看典型案例详情
    - 获取根因分析和建议
    """
    print("\n" + "=" * 70)
    print("📌 演示3: 根因下钻分析")
    print("=" * 70)
    print("\n本演示将展示:")
    print("  1. 对'user_requested'进行根因下钻")
    print("  2. 对'low_confidence'进行根因下钻")
    print("  3. 对'max_turns_exceeded'进行根因下钻")
    print("  4. 查看每个类型的典型案例和根因分析")
    print("=" * 70)

    # 创建分析器并生成数据
    analyzer = MockFailureAnalyzer()
    generate_mock_failure_data(analyzer, num_cases=60)

    # 对每种失败类型进行下钻
    failure_types_to_analyze = ["user_requested", "low_confidence", "max_turns_exceeded"]

    for failure_type in failure_types_to_analyze:
        print(f"\n{'─'*70}")
        print(f"🔬 下钻分析: {failure_type}")
        print(f"{'─'*70}")

        drill_result = analyzer.drill_down_by_root_cause(failure_type, limit=3)
        analyzer.print_drill_down_report(drill_result)


async def demo_4_time_range_analysis():
    """
    演示4: 时间范围分析

    展示:
    - 如何分析特定时间段内的失败案例
    - 识别失败趋势和模式
    """
    print("\n" + "=" * 70)
    print("📌 演示4: 时间范围分析")
    print("=" * 70)
    print("\n本演示将展示:")
    print("  1. 分析最近24小时的失败案例")
    print("  2. 分析24-48小时前的失败案例")
    print("  3. 对比两个时间段的差异，识别趋势")
    print("=" * 70)

    # 创建分析器并生成数据
    analyzer = MockFailureAnalyzer()
    generate_mock_failure_data(analyzer, num_cases=80)

    now = datetime.now()

    # 分析最近24小时
    print(f"\n{'─'*70}")
    print("🕐 分析最近24小时")
    print(f"{'─'*70}")

    start_recent = now - timedelta(hours=24)
    recent_traces = analyzer.get_failure_traces(start_time=start_recent, end_time=now)
    print(f"  找到 {len(recent_traces)} 个失败案例")

    if recent_traces:
        result = analyzer.analyze_failures(recent_traces)
        report = analyzer.generate_report(result)
        print(report)

    # 分析24-48小时前
    print(f"\n{'─'*70}")
    print("🕐 分析24-48小时前")
    print(f"{'─'*70}")

    start_older = now - timedelta(hours=48)
    end_older = now - timedelta(hours=24)
    older_traces = analyzer.get_failure_traces(start_time=start_older, end_time=end_older)
    print(f"  找到 {len(older_traces)} 个失败案例")

    if older_traces:
        result = analyzer.analyze_failures(older_traces)
        report = analyzer.generate_report(result)
        print(report)

    # 对比总结
    print(f"\n{'─'*70}")
    print("📈 趋势对比总结")
    print(f"{'─'*70}")
    print(f"  最近24小时失败数: {len(recent_traces)}")
    print(f"  前24小时失败数: {len(older_traces)}")

    if len(older_traces) > 0:
        change_rate = ((len(recent_traces) - len(older_traces)) / len(older_traces)) * 100
        trend = "上升 ↑" if change_rate > 10 else ("下降 ↓" if change_rate < -10 else "持平 →")
        print(f"  变化率: {change_rate:+.1f}% ({trend})")

        if change_rate > 20:
            print("\n  ⚠️  警告: 失败率显著上升，建议立即排查!")
        elif change_rate < -20:
            print("\n  ✓ 好消息: 失败率明显下降，优化措施见效!")
        else:
            print("\n  ℹ️  失败率相对稳定，继续监控即可")


async def run_all_demos():
    """运行所有失败分析演示"""
    print("\n" + "=" * 70)
    print("🚀 Langfuse 失败分析系统 - 完整演示")
    print("=" * 70)
    print(f"\n演示时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("演示版本: Failure Analysis Demo v1.0")
    print("\n本演示包含4个部分:")
    print("  演示1: 生成数据并执行基础分析")
    print("  演示2: 按失败类型过滤分析")
    print("  演示3: 根因下钻分析")
    print("  演示4: 时间范围分析")
    print("=" * 70)

    # 运行所有演示
    await demo_1_generate_and_analyze()
    await demo_2_filter_by_failure_type()
    await demo_3_root_cause_drill_down()
    await demo_4_time_range_analysis()

    # 最终总结
    print("\n" + "=" * 70)
    print("🎉 所有失败分析演示完成!")
    print("=" * 70)
    print("\n📚 演示回顾:")
    print("  演示1: 展示了如何生成模拟数据、筛选失败案例、生成完整报告")
    print("  演示2: 展示了如何针对特定失败类型进行专项分析")
    print("  演示3: 展示了根因下钻功能，深入分析典型案例")
    print("  演示4: 展示了时间范围分析，识别失败趋势")
    print("\n💡 核心价值:")
    print("  1. 自动化失败检测: 基于多维规则自动识别失败案例")
    print("  2. 全面分析视角: 从类型、意图、渠道、时段等多维度分析")
    print("  3. 根因定位能力: 深入分析失败根本原因，提供典型案例")
    print("  4. actionable建议: 基于分析结果生成具体优化建议")
    print("  5. 趋势监控: 支持时间范围分析，跟踪改进效果")
    print("\n🔗 在实际项目中使用:")
    print("  1. 替换MockFailureAnalyzer为真实的Langfuse API调用")
    print("  2. 配置定时任务定期运行分析（如每天凌晨）")
    print("  3. 将分析报告发送到团队邮箱或Slack")
    print("  4. 集成到Dashboard，可视化展示失败趋势")
    print("=" * 70)


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("⚙️  初始化演示环境...")
    print("=" * 70)

    # 加载环境变量（如果有的话）
    try:
        from dotenv import load_dotenv

        load_dotenv()
        print("✓ .env 文件加载成功")
    except ImportError:
        print("⚠ python-dotenv 未安装，跳过.env加载")
    except Exception as e:
        print(f"⚠ .env 加载警告: {e}")

    print("✓ 演示环境就绪\n")

    # 运行所有演示
    asyncio.run(run_all_demos())
