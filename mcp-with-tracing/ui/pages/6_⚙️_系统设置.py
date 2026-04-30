"""
系统设置页面

实现健康检查详情、缓存管理、环境变量查看。
"""
import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ui.utils.data_loader import (
    load_cache_stats,
    load_health_status,
)
from ui.utils.formatters import format_status

st.set_page_config(
    page_title="系统设置 - MCP Observability",
    page_icon="⚙️",
    layout="wide",
)

st.title("⚙️ 系统设置")
st.markdown("---")

# 加载健康状态
health = load_health_status()

# 健康检查详情
st.subheader("🏥 健康检查详情")

components = health.get("components", {})

if components:
    df_components = []

    for component_name, component_data in components.items():
        status = component_data.get("status", "unknown")
        df_components.append({
            "组件": component_name,
            "状态": format_status(status),
            "详情": str(component_data),
        })

    df_comp = pd.DataFrame(df_components)

    st.dataframe(
        df_comp[["组件", "状态", "详情"]],
        use_container_width=True,
        hide_index=True,
    )
else:
    st.warning("暂无组件数据")

st.markdown("---")

# 缓存管理
st.subheader("💾 缓存管理")

cache_stats = load_cache_stats()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "缓存命中率",
        f"{cache_stats.get('hit_rate', 0):.1%}",
    )

with col2:
    st.metric(
        "当前缓存大小",
        f"{cache_stats.get('size', 0)}",
    )

with col3:
    st.metric(
        "最大缓存容量",
        f"{cache_stats.get('max_size', 0)}",
    )

with col4:
    st.metric(
        "TTL",
        f"{cache_stats.get('ttl_seconds', 0)}s",
    )

# 缓存操作
col1, col2 = st.columns(2)

with col1:
    if st.button("🗑️ 清除所有缓存", type="secondary"):
        try:
            from src.observability.metrics_collector import MetricsCollector

            collector = MetricsCollector()
            collector.clear_cache()

            st.success("✅ 缓存已清除！")
            st.rerun()
        except Exception as e:
            st.error(f"❌ 清除缓存失败: {e}")

with col2:
    if st.button("🔄 刷新缓存统计"):
        st.rerun()

st.markdown("---")

# 环境变量查看
st.subheader("🔧 环境变量配置")

# 关键环境变量
env_vars = {
    "LANGFUSE_PUBLIC_KEY": "Langfuse Public Key",
    "LANGFUSE_SECRET_KEY": "Langfuse Secret Key",
    "LANGFUSE_HOST": "Langfuse Host",
    "ALERT_CHECK_INTERVAL_MINUTES": "告警检查间隔",
    "SMART_ALERT_CHECK_INTERVAL_MINUTES": "智能告警检查间隔",
    "WECOM_WEBHOOK_URL": "企业微信 Webhook",
    "ENVIRONMENT": "运行环境",
    "LOG_LEVEL": "日志级别",
}

df_env = []
for var_name, var_desc in env_vars.items():
    value = os.getenv(var_name)

    # 脱敏处理
    if value:
        if "KEY" in var_name or "SECRET" in var_name:
            display_value = value[:10] + "..." + value[-4:]
        elif "URL" in var_name:
            display_value = value[:30] + "..."
        else:
            display_value = value
    else:
        display_value = "未设置"

    df_env.append({
        "变量名": var_name,
        "描述": var_desc,
        "值": display_value,
    })

df_env_data = pd.DataFrame(df_env)

st.dataframe(
    df_env_data[["变量名", "描述", "值"]],
    use_container_width=True,
    hide_index=True,
)

st.markdown("---")

# 系统信息
st.subheader("ℹ️ 系统信息")

col1, col2, col3 = st.columns(3)

with col1:
    st.write(f"**Python 版本**: {sys.version}")

with col2:
    st.write(f"**项目路径**: {project_root}")

with col3:
    st.write(f"**Streamlit 版本**: {st.__version__}")

st.markdown("---")
st.caption("系统设置页面 | 只读查看，修改需编辑 .env 文件")
