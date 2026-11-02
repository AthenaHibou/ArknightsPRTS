"""ArknightsPRTS 插件配置（自动挂载到 WebConsole 进行统一管理）。"""

from __future__ import annotations

from typing import Dict

from gsuid_core.data_store import get_res_path
from gsuid_core.utils.plugins_config.models import (
    GSC,
    GsDivider,
    GsIntConfig,
    GsBoolConfig,
)
from gsuid_core.utils.plugins_config.gs_config import StringConfig

CONFIG_DEFAULT: Dict[str, GSC] = {
    "总开关": GsDivider(title="总开关", desc="一键启停整套明日方舟资料查询", data="总开关"),
    "enable": GsBoolConfig(
        title="启用插件",
        desc="关闭后所有明日方舟查询工具直接返回“已关闭”，不影响机器人其它功能",
        data=True,
    ),
    "单项开关": GsDivider(title="单项开关", desc="按功能关闭，适合只保留你常用的能力", data="单项开关"),
    "enable_operator": GsBoolConfig(
        title="干员查询",
        desc="干员详情（ak_operator_info）+ 干员筛选（ak_operator_search）",
        data=True,
    ),
    "enable_enemy": GsBoolConfig(
        title="敌人查询",
        desc="敌人详情（ak_enemy_info）+ 敌人筛选（ak_enemy_search）",
        data=True,
    ),
    "enable_recruit": GsBoolConfig(
        title="公招计算",
        desc="公开招募词条算结果（ak_recruit）",
        data=True,
    ),
    "其它": GsDivider(title="其它", desc="查询行为相关设置", data="其它"),
    "default_limit": GsIntConfig(
        title="列表默认上限",
        desc="干员/敌人筛选结果默认返回条数上限",
        data=30,
        max_value=200,
    ),
}

CONFIG_PATH = get_res_path("ArknightsPRTS") / "config.json"

arknightsprts_config = StringConfig("ArknightsPRTS", CONFIG_PATH, CONFIG_DEFAULT)


def is_tool_enabled(tool_key: str) -> bool:
    """判断某个 AI 工具是否在 WebConsole 中开启。"""
    if not arknightsprts_config.get_config("enable").data:
        return False
    return bool(arknightsprts_config.get_config(tool_key).data)


def get_default_limit() -> int:
    """读取列表查询默认条数上限。"""
    return int(arknightsprts_config.get_config("default_limit").data)

DISABLED_MSG = "该查询功能已在 WebConsole 中关闭，如需使用请到控制台插件配置里开启。"
