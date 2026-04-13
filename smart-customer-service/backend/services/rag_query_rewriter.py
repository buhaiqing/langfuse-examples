"""查询重写模块 - 同义词扩展、拼写纠错"""

from typing import List, Dict
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from core.config import settings


class QueryRewriter:
    """查询重写器"""

    def __init__(self):
        self.llm = ChatOpenAI(model=settings.openai_model, temperature=0.1)

        # 同义词扩展提示词
        self.synonym_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """你是一个查询优化助手。为用户查询生成同义词扩展，帮助提高检索效果。

要求：
1. 生成 3-5 个同义词或相关词
2. 保持语义一致性
3. 输出 JSON 格式：{"original": "原查询", "expanded": ["同义词 1", "同义词 2", ...]}

示例：
用户查询：API 403 错误
输出：{"original": "API 403 错误", "expanded": ["API 权限错误", "403 Forbidden", "API 访问被拒绝", "身份验证失败"]}""",
                ),
                ("user", "用户查询：{query}"),
            ]
        )

    async def rewrite(self, query: str) -> Dict:
        """
        重写查询

        Args:
            query: 原始查询

        Returns:
            包含原始查询和扩展词的字典
        """
        response = await self.llm.ainvoke(await self.synonym_prompt.ainvoke({"query": query}))

        # 解析响应（简化处理，实际应该用 JSON 解析器）
        content = response.content if hasattr(response, "content") else str(response)

        return {
            "original": query,
            "expanded": [query],  # TODO: 解析 LLM 响应获取扩展词
            "rewritten": query,
        }

    def _extract_keywords(self, query: str) -> List[str]:
        """提取关键词"""
        # 简单的空格分词，实际应该用更高级的分词器
        return query.split()


# 全局实例
query_rewriter = QueryRewriter()
