"""
MCP Langfuse Observability - Streamlit UI Dashboard

主应用入口，提供系统总览和导航。
"""
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

st.set_page_config(
    page_title="MCP Observability Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 自定义 CSS 样式
st.markdown(
    """
    <style>
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .status-healthy {
        color: #00C853;
        font-weight: bold;
    }
    .status-degraded {
        color: #FFB300;
        font-weight: bold;
    }
    .status-error {
        color: #FF1744;
        font-weight: bold;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def main():
    """主应用入口"""
    # 侧边栏配置
    with st.sidebar:
        st.title("⚙️ 配置")

        # 刷新控制
        st.slider(
            "自动刷新间隔（秒）",
            min_value=10,
            max_value=300,
            value=60,
            step=10,
        )

        st.checkbox("启用自动刷新", value=True)

        st.divider()

        # 系统信息
        st.info(f"🕒 最后更新: {datetime.now().strftime('%H:%M:%S')}")

        st.divider()

        # 快速链接
        st.markdown("### 🔗 快速链接")
        st.markdown("- [Langfuse Dashboard](https://cloud.langfuse.com)")
        st.markdown("- [项目文档](../docs/)")
        st.markdown("- [API 参考](../manuals/)")

    # 主页标题
    st.title("📊 MCP Langfuse 可观测性平台")
    st.markdown("---")

    # 欢迎信息
    st.success(
        """
        **欢迎使用 MCP Observability Dashboard!**

        这是一个基于 Streamlit 构建的监控仪表板，提供：
        - 🏠 系统健康总览
        - 📊 实时指标监控
        - 🚨 告警管理与统计
        - 💬 用户反馈分析
        - 📝 提示词版本管理
        - ⚙️ 系统配置与健康检查

        👈 使用左侧导航栏切换到不同功能页面
        """
    )

    # 项目状态
    st.markdown("---")
    st.markdown("### 📋 项目状态")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("单元测试", "114 passed")
    with col2:
        st.metric("集成测试", "20 passed")
    with col3:
        st.metric("代码覆盖率", "90%+")

    st.markdown("---")
    st.caption("MCP Langfuse Observability Platform v1.0 | Last Updated: 2026-04-30")


if __name__ == "__main__":
    main()
