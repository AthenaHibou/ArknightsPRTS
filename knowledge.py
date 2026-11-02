"""ArknightsPRTS 知识库注册：让模型的 search_cognition 认知到方舟查询能力存在。

插件工具属于按需经向量检索加载的 common 分类，模型需要先"知道有这能力"
才会去 find_tools / 直接调用。这里用 ai_entity 把能力声明写进认知库。
"""
from __future__ import annotations

from gsuid_core.logger import logger


def _register_knowledge() -> None:
    """把方舟查询能力注册为 AI 知识条目（AI 关闭时静默跳过）。"""
    try:
        from gsuid_core.ai_core.models import KnowledgePoint
        from gsuid_core.ai_core.register import ai_entity
    except Exception:
        return

    entries = [
        KnowledgePoint(
            id="arknightsprts_operator",
            plugin="ArknightsPRTS",
            title="明日方舟干员资料查询",
            content=(
                "【明日方舟·干员查询】机器人可直接查询明日方舟干员详细数据："
                "技能/天赋/属性/精英化材料/模组/语音/档案，也可按职业/分支/稀有度/标签多维筛选干员。"
                "用户问『XX干员的数据/查方舟干员/找某个职业的干员』时，"
                "调 AI 工具 ak_operator_info / ak_operator_search。"
            ),
            tags=["明日方舟", "方舟", "arknight", "Arknights", "干员", "整合运动", "游戏"],
            entity="明日方舟干员资料查询",
        ),
        KnowledgePoint(
            id="arknightsprts_enemy",
            plugin="ArknightsPRTS",
            title="明日方舟敌人资料查询",
            content=(
                "【明日方舟·敌人查询】机器人可直接查询明日方舟敌人详细数据与多维筛选敌人列表。"
                "用户问『XX敌人的数据』『查方舟敌人』时，调 AI 工具 ak_enemy_info / ak_enemy_search。"
            ),
            tags=["明日方舟", "方舟", "arknight", "Arknights", "敌人", "游戏"],
            entity="明日方舟敌人资料查询",
        ),
        KnowledgePoint(
            id="arknightsprts_recruit",
            plugin="ArknightsPRTS",
            title="明日方舟公开招募（公招）计算",
            content=(
                "【明日方舟·公招计算】机器人可根据公招词条（资历/职业/位置/词缀）算出可出的干员，"
                "或推荐能出金/出高星的最佳词条组合。用户问『这个公招词条能出什么』『公招怎么选词条』时，"
                "调 AI 工具 ak_recruit。"
            ),
            tags=["明日方舟", "方舟", "arknight", "Arknights", "公招", "公开招募", "游戏"],
            entity="明日方舟公招计算",
        ),
    ]

    for entry in entries:
        try:
            ai_entity(entry)
        except Exception as e:
            logger.warning(f"[ArknightsPRTS] ai_entity 注册失败: {e}")


_register_knowledge()
