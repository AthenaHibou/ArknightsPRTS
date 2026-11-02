"""ArknightsPRTS 插件入口：明日方舟 PRTS.wiki 资料查询（进程内 AI 工具）。

将 Doctah-MCP 的核心抓取/解析逻辑移植为 GsCore 的 @ai_tools 工具，
由 AI 在内部直接进程内调用，去掉 MCP 协议与子进程开销。
"""
from __future__ import annotations

from gsuid_core.sv import Plugins

from . import knowledge  # noqa: F401  # 注册 ai_entity 认知（模型据此得知能力存在）
from . import tools  # noqa: F401  # 导入即触发 @ai_tools 注册

Plugins(
    name="ArknightsPRTS",
    alias=["明日方舟PRTS", "prts", "明日方舟资料"],
)
