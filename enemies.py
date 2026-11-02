"""敌人查询功能（自 Doctah-MCP 移植，移除 MCP 与每调用新建客户端的开销）。"""

from __future__ import annotations

from .utils import BASE_URL
from .client import get_client

_SUBPAGE_MARKERS = ("/spine", "/语音记录", "/敌人模型")


async def search_enemy(name: str, sections: str | None = None) -> str:
    """查询单个敌人的详细信息。"""
    if not name:
        return (
            "# ❌ 敌人查询失败\n\n"
            "## 🔍 查询状态\n- **状态**: 查询参数为空\n- **错误类型**: EMPTY_QUERY\n\n"
            "请提供敌人名称进行查询。"
        )

    client = get_client()
    target_sections = None
    if sections:
        target_sections = [s.strip() for s in sections.split(",") if s.strip()]

    enemy_data = await client.parse_enemy_complete(name, target_sections)
    if not enemy_data:
        search_results = await client.search_pages(f"{name} 敌人")
        if not search_results:
            search_results = await client.search_pages(name)
        if not search_results:
            return _enemy_not_found(name)
        best_match = None
        for result in search_results:
            title = result["title"]
            if not any(substr in title for substr in _SUBPAGE_MARKERS):
                best_match = result
                break
        if not best_match:
            best_match = search_results[0]
        enemy_data = await client.parse_enemy_complete(best_match["title"], target_sections)

    if not enemy_data:
        return _enemy_not_found(name)
    return client.format_enemy_info(enemy_data, target_sections)


def _enemy_not_found(name: str) -> str:
    return f"""# ❌ 敌人查询失败

## 🔍 查询状态
- **状态**: 敌人不存在或解析失败
- **查询名称**: {name}
- **错误类型**: ENEMY_NOT_FOUND

## 📋 可能的原因
1. **拼写错误**: 请检查敌人名称的拼写
2. **敌人不存在**: 该名称可能不是有效的明日方舟敌人

## 🎯 建议操作
1. 检查敌人名称拼写
2. 查看 [PRTS.wiki 敌人一览](https://prts.wiki/w/敌人一览) 确认敌人是否存在
- [PRTS.wiki 首页]({BASE_URL})
"""


def _parse_multi(v: str | None) -> set[str]:
    if not v:
        return set()
    for sep in [",", "，", "、", "|", " "]:
        v = v.replace(sep, ",")
    return {x.strip() for x in v.split(",") if x.strip()}


async def list_enemies_advanced(
    keyword: str | None = None,
    enemy_level: str | None = None,
    enemy_race: str | None = None,
    attack_type: str | None = None,
    damage_type: str | None = None,
    endure: str | None = None,
    attack: str | None = None,
    defence: str | None = None,
    move_speed: str | None = None,
    attack_speed: str | None = None,
    resistance: str | None = None,
    limit: int = 50,
) -> str:
    """按多维条件筛选敌人列表（参考 PRTS『敌人一览』）。"""
    cond: dict[str, set[str]] = {
        "enemyLevel": _parse_multi(enemy_level),
        "enemyRace": _parse_multi(enemy_race),
        "attackType": _parse_multi(attack_type),
        "damageType": _parse_multi(damage_type),
        "endure": _parse_multi(endure),
        "attack": _parse_multi(attack),
        "defence": _parse_multi(defence),
        "moveSpeed": _parse_multi(move_speed),
        "attackSpeed": _parse_multi(attack_speed),
        "resistance": _parse_multi(resistance),
    }
    if not any([keyword] + [bool(v) for v in cond.values()]):
        return (
            "# ❌ 敌人多维筛选失败\n\n"
            "- **状态**: 缺少筛选条件\n"
            "请至少提供一个条件，如 enemy_level=精英 或 attack_type=远程。"
        )

    client = get_client()
    data = await client.get_enemy_filter_data()
    if not data:
        return "# ❌ 敌人多维筛选失败\n\n- **状态**: 未获取到数据"

    strict_fields = {"endure", "attack", "defence", "moveSpeed", "attackSpeed", "resistance"}
    items: list[dict[str, object]] = []
    for row in data:
        name = str(row.get("name", ""))
        if keyword and keyword not in name and keyword not in str(row.get("ability", "") or ""):
            continue
        ok = True
        for k, needs in cond.items():
            if not needs:
                continue
            v = str(row.get(k, "") or "")
            if k in strict_fields:
                if v not in needs:
                    ok = False
                    break
            else:
                if not any(n in v for n in needs):
                    ok = False
                    break
        if not ok:
            continue
        items.append({
            "name": name,
            "url": row.get("url", ""),
            "enemyLevel": str(row.get("enemyLevel", "") or ""),
            "enemyRace": str(row.get("enemyRace", "") or ""),
            "attackType": str(row.get("attackType", "") or ""),
            "damageType": str(row.get("damageType", "") or ""),
        })

    rank = {"领袖": 3, "精英": 2, "普通": 1}
    items.sort(key=lambda x: (-rank.get(str(x.get("enemyLevel")), 0), str(x.get("name"))))

    if not items:
        return "# 🔍 敌人多维筛选\n\n- **匹配数量**: 0"

    lines = ["# 🔎 敌人多维筛选结果", "", "## 📊 统计", f"- **匹配敌人**: {len(items)}", "\n## 📋 敌人列表"]
    for i, item in enumerate(items[:limit], 1):
        meta = " / ".join(
            [v for v in [str(item.get(k)) for k in ("enemyLevel", "enemyRace", "attackType", "damageType")] if v]
        )
        lines.append(f"{i:2d}. **{item.get('name')}**（{meta}）")
        if item.get("url"):
            lines.append(f"   链接: {item.get('url')}")
    lines.append("\n---\n数据来源: 敌人一览/数据")
    return "\n".join(lines)
