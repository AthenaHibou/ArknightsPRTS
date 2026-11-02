"""ArknightsPRTS 的 AI 工具注册（明日方舟 PRTS.wiki 资料查询）。

供 AI 通过内部工具调用方式查询干员 / 敌人 / 公招信息，进程内直连 PRTS，无 MCP 协议开销。
"""
from __future__ import annotations

from gsuid_core.ai_core.register import ai_tools

from . import enemies, recruit, operators
from .config import DISABLED_MSG, is_tool_enabled, get_default_limit

_DOMAIN = "明日方舟资料查询"


_CONTEXT_TAGS = ["明日方舟", "方舟", "Arknight", "游戏"]


@ai_tools(
    category="common",
    capability_domain=_DOMAIN,
    context_tags=_CONTEXT_TAGS,
    covers=[
        "明日方舟干员详细信息：技能/天赋/属性/精英化材料/模组/语音/档案/稀有度/职业/分支",
        "按干员名或带职业后缀（如 银灰、阿米娅（医疗））查询页面章节内容",
    ],
    aliases=["明日方舟·干员详情", "方舟·查干员", "PRTS·干员信息"],
    timeout=90.0,
)
async def ak_operator_info(name: str, sections: str = "") -> str:
    """
    查询明日方舟单个干员的详细信息（技能、天赋、属性、精英化材料、模组等）。

    当用户需要某个干员的详细数据时调用，返回结构化 Markdown 文本。

    Args:
        name: 干员名称（支持中文/英文/代号/职业后缀，如 银灰 或 阿米娅（医疗））
        sections: 要查询的章节，逗号分隔，如 "天赋,技能"。留空返回全部
    """
    if not is_tool_enabled("enable_operator"):
        return DISABLED_MSG
    return await operators.search_operator(name, sections or None)


@ai_tools(
    category="common",
    capability_domain=_DOMAIN,
    context_tags=_CONTEXT_TAGS,
    covers=[
        "明日方舟敌人详细信息：级别/属性/种族/攻击方式/伤害类型/技能",
        "按敌人名查询 PRTS 敌人页面各章节内容",
    ],
    aliases=["明日方舟·敌人详情", "方舟·查敌人", "PRTS·敌人信息"],
    timeout=90.0,
)
async def ak_enemy_info(name: str, sections: str = "") -> str:
    """
    查询明日方舟单个敌人的详细信息（属性、等级、技能等）。

    当用户需要某个敌人的详细数据时调用，返回结构化 Markdown 文本。

    Args:
        name: 敌人名称，如 源石虫、碎骨
        sections: 要查询的章节，逗号分隔，如 "级别0,级别1"。留空返回全部
    """
    if not is_tool_enabled("enable_enemy"):
        return DISABLED_MSG
    return await enemies.search_enemy(name, sections or None)


@ai_tools(
    category="common",
    capability_domain=_DOMAIN,
    context_tags=_CONTEXT_TAGS,
    covers=[
        "明日方舟干员多维筛选/搜索：按关键词/职业/分支/稀有度/位置/性别/标签/势力/出身地/种族",
        "模糊找干员：如『医疗干员』『六星近卫』『罗德岛速射手』",
    ],
    aliases=["明日方舟·搜索干员", "方舟·找干员", "PRTS·干员筛选"],
    timeout=60.0,
)
async def ak_operator_search(
    keyword: str = "",
    professions: str = "",
    branches: str = "",
    rarities: str = "",
    positions: str = "",
    genders: str = "",
    tags: str = "",
    factions: str = "",
    limit: int | None = None,
) -> str:
    """
    按多维条件筛选或模糊搜索明日方舟干员列表。

    当用户想『找到某个/某类干员』但不知道完整名时调用，返回匹配干员及稀有度/职业/分支。

    Args:
        keyword: 干员名关键词，模糊匹配
        professions: 职业，逗号分隔，如 "医疗,术师"
        branches: 分支，逗号分隔，如 "速射手,决战者"
        rarities: 稀有度，逗号分隔，如 "6,5" 或 "六星,五星"
        positions: 位置，如 "近战位,远程位"
        genders: 性别，如 "女性,男性"
        tags: 标签，逗号分隔，如 "治疗,群攻"
        factions: 势力，如 "罗德岛"
        limit: 返回数量上限，默认取 WebConsole 配置的列表上限
    """
    if not is_tool_enabled("enable_operator"):
        return DISABLED_MSG
    return await operators.list_operators_advanced(
        keyword=keyword or None,
        professions=professions or None,
        branches=branches or None,
        rarities=rarities or None,
        positions=positions or None,
        genders=genders or None,
        tags=tags or None,
        factions=factions or None,
        limit=limit if limit is not None else get_default_limit(),
    )


@ai_tools(
    category="common",
    capability_domain=_DOMAIN,
    context_tags=_CONTEXT_TAGS,
    covers=[
        "明日方舟敌人多维筛选/搜索：按关键词/地位/种族/攻击方式/伤害类型",
        "模糊找敌人：如『精英敌人』『远程术师敌人』",
    ],
    aliases=["明日方舟·搜索敌人", "方舟·找敌人", "PRTS·敌人筛选"],
    timeout=60.0,
)
async def ak_enemy_search(
    keyword: str = "",
    enemy_level: str = "",
    enemy_race: str = "",
    attack_type: str = "",
    damage_type: str = "",
    limit: int | None = None,
) -> str:
    """
    按多维条件筛选或模糊搜索明日方舟敌人列表。

    当用户想『找到某个/某类敌人』但不知道完整名时调用。

    Args:
        keyword: 敌人名关键词，模糊匹配
        enemy_level: 地位/级别，如 "领袖,精英,普通"
        enemy_race: 种族，如 "感染生物,机械"
        attack_type: 攻击方式，如 "近战,远程"
        damage_type: 伤害类型，如 "物理,法术"
        limit: 返回数量上限，默认取 WebConsole 配置的列表上限
    """
    if not is_tool_enabled("enable_enemy"):
        return DISABLED_MSG
    return await enemies.list_enemies_advanced(
        keyword=keyword or None,
        enemy_level=enemy_level or None,
        enemy_race=enemy_race or None,
        attack_type=attack_type or None,
        damage_type=damage_type or None,
        limit=limit if limit is not None else get_default_limit(),
    )


@ai_tools(
    category="common",
    capability_domain=_DOMAIN,
    context_tags=_CONTEXT_TAGS,
    covers=[
        "明日方舟公开招募（公招）词条组合算结果干员",
        "给词条（资历/职业/位置/词缀）求可能出哪些干员，或推荐出金/出高星组合",
    ],
    aliases=["明日方舟·公招计算", "方舟·公招", "PRTS·公开招募"],
    timeout=60.0,
)
async def ak_recruit(terms: str, mode: str = "normal") -> str:
    """
    明日方舟公开招募（公招）计算。

    当用户给出公招词条并想知道可能出什么干员时调用。

    Args:
        terms: 词条，用逗号/顿号/空格分隔，如 "资深干员, 术师, 群攻" 或 "先锋 费用回复"
        mode: 计算模式，normal=常规匹配；suggest=推荐最佳子集组合，默认 normal
    """
    if not is_tool_enabled("enable_recruit"):
        return DISABLED_MSG
    if mode == "suggest":
        return await recruit.recruit_by_tags_suggest(terms)
    return await recruit.recruit_by_tags(terms)
