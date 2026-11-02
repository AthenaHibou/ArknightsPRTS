"""干员查询功能（自 Doctah-MCP 移植，移除 MCP 与每调用新建客户端的开销）。"""

from __future__ import annotations

import re
import asyncio

from .utils import PROFESSION_TAGS, _extract_similar_operator_names, _create_operator_not_found_response
from .client import get_client

_SUBPAGE_MARKERS = ("/干员密录", "/语音记录", "/干员模型", "/悖论模拟")
_ENEMY_MARKERS = ("级别0", "级别1", "级别2", "敌人模型")
_NON_OPERATOR_MARKERS = (
    "的信物", "的生日蛋糕", "家具", "道具", "材料", "芯片", "模组",
    "技能书", "经验", "龙门币", "合成玉", "源石", "赠礼", "装置",
    "装备", "时装", "皮肤", "立绘", "头像", "名片", "徽章", "陈列",
    "摆件", "柜", "架", "肯德基", "战利品", "古典", "陈旧",
)
_CATEGORY_MARKERS = ("分类:", "一览", "列表", "模板:", "Category:", "Template:")


async def search_operator(name: str, sections: str | None = None) -> str:
    """查询单个干员的详细信息。"""
    if not name:
        return _create_operator_not_found_response("空名称", ["请输入有效的干员名称"])

    client = get_client()
    target_sections = None
    if sections:
        target_sections = [s.strip() for s in sections.split(",") if s.strip()]

    # 策略一：直接尝试访问干员页面（带职业后缀变体）
    potential_titles = [name, *(f"{name}{prof}" for prof in PROFESSION_TAGS)]
    operator_data = None
    for title in potential_titles:
        temp_data = await client.parse_operator_complete(title, target_sections)
        if temp_data and (
            temp_data.get("basic_info")
            or temp_data.get("sections")
            or temp_data.get("table_of_contents")
        ):
            if temp_data.get("type") == "enemy":
                return _enemy_page_hint(name, title)
            operator_data = temp_data
            break

    # 策略二：使用搜索 API 兜底
    if not operator_data:
        search_results = await client.search_pages(f"{name} 干员")
        if not search_results:
            search_results = await client.search_pages(name)
        if not search_results:
            return _create_operator_not_found_response(name)
        best_match = None
        potential_enemy_pages: list[str] = []
        for result in search_results:
            title = result["title"]
            if "/spine" in title:
                potential_enemy_pages.append(title.split("/")[0])
                continue
            if not any(substr in title for substr in _SUBPAGE_MARKERS):
                if client.matches_profession(title) or title == name:
                    best_match = result
                    break
        if not best_match and potential_enemy_pages:
            for enemy_name in set(potential_enemy_pages):
                if enemy_name == name:
                    enemy_data = await client.parse_enemy_complete(enemy_name, target_sections)
                    if enemy_data:
                        return _enemy_page_hint(name, enemy_name)
        if not best_match:
            similar_names = _extract_similar_operator_names(search_results, name)
            if similar_names:
                return _create_operator_not_found_response(name, similar_names)
            best_match = search_results[0]
        operator_data = await client.parse_operator_complete(best_match["title"], target_sections)

    if not operator_data:
        return _create_operator_not_found_response(name)
    return client.format_operator(operator_data, target_sections)


def _enemy_page_hint(name: str, found_title: str) -> str:
    """查询指向敌人页面时的引导响应。"""
    return f"""# ⚠️ 发现敌人页面

## 🔍 查询结果
- **查询名称**: {name}
- **找到页面**: {found_title}
- **页面类型**: 敌人页面

## 💡 建议
该查询结果指向敌人页面，而非干员页面。如需敌人信息请使用敌人查询功能。
若确要查询名为 "{name}" 的干员，可能是：
1. 干员不存在
2. 名称拼写有误
3. 需要完整干员名称（如"阿米娅（医疗）"）

## 🔗 相关链接
- [PRTS.wiki 干员一览](https://prts.wiki/w/干员一览)
- [PRTS.wiki 敌人一览](https://prts.wiki/w/敌人一览)
"""


def _parse_multi(value: str | None) -> set[str]:
    """把逗号/顿号/竖线/空格分隔的多值为集合。"""
    if not value:
        return set()
    normalized = value
    for sep in [",", "，", "、", "|", " "]:
        normalized = normalized.replace(sep, ",")
    return {x.strip() for x in normalized.split(",") if x.strip()}


def _normalize_text(s: str) -> str:
    return s.replace("：", ":").replace("（", "(").replace("）", ")").strip()


def _normalize_rarity_set(values: set[str]) -> set[str]:
    cn_map = {"一": "1", "二": "2", "三": "3", "四": "4", "五": "5", "六": "6"}
    mapped: set[str] = set()
    for v in values:
        v = v.replace("★", "").replace("星", "").replace("稀有度", "").strip()
        if v in cn_map:
            v = cn_map[v]
        if v.isdigit():
            mapped.add(v)
    return mapped


async def list_operators_advanced(
    keyword: str | None = None,
    professions: str | None = None,
    branches: str | None = None,
    rarities: str | None = None,
    positions: str | None = None,
    genders: str | None = None,
    obtains: str | None = None,
    tags: str | None = None,
    factions: str | None = None,
    birthplaces: str | None = None,
    races: str | None = None,
    limit: int = 50,
) -> str:
    """按多维条件筛选干员列表（参考 PRTS『干员一览』）。"""
    professions_set = _parse_multi(professions)
    branches_set = _parse_multi(branches)
    rarities_set = _normalize_rarity_set(_parse_multi(rarities))
    positions_set = _parse_multi(positions)
    genders_set = _parse_multi(genders)
    obtains_set = _parse_multi(obtains)
    tags_set = _parse_multi(tags)
    factions_set = _parse_multi(factions)
    birthplaces_set = _parse_multi(birthplaces)
    races_set = _parse_multi(races)

    if not any([
        keyword, professions_set, branches_set, rarities_set, positions_set,
        genders_set, obtains_set, tags_set, factions_set, birthplaces_set, races_set,
    ]):
        return (
            "# ❌ 干员多维筛选失败\n\n"
            "- **状态**: 缺少筛选条件\n"
            "请至少提供一个条件，如 professions=医疗 或 tags=治疗。"
        )

    client = get_client()

    def match_contains(value: str | None, need: set[str]) -> bool:
        if not need:
            return True
        if value is None:
            return False
        v = _normalize_text(value)
        return any(n in v for n in need)

    def match_rarity(value: str | None) -> bool:
        if not rarities_set:
            return True
        v = str(value or "").replace("★", "").strip()
        return v in rarities_set

    filtered: list[dict[str, str]] = []
    filter_data = await client.get_operator_filter_data()
    for row in filter_data:
        if not row.get("zh") and not row.get("name"):
            continue
        name = row.get("zh") or row.get("name")
        if keyword and keyword not in name:
            continue
        branch_val = row.get("branch") or row.get("subprofession") or ""
        gender_val = row.get("gender") or row.get("sex") or ""
        obtain_val = row.get("obtain") or row.get("obtain_method") or ""
        tags_val = row.get("tags") or row.get("tag") or ""
        faction_val = row.get("logo") or row.get("group") or row.get("nation") or ""
        rarity_raw = str(row.get("rarity") or "").strip()
        rarity_star = ""
        if rarity_raw.isdigit():
            rarity_star = str(int(rarity_raw) + 1)
        else:
            rarity_star = rarity_raw
        if not (
            match_contains(row.get("profession"), professions_set)
            and match_contains(branch_val, branches_set)
            and match_rarity(rarity_star)
            and match_contains(row.get("position"), positions_set)
            and match_contains(gender_val, genders_set)
            and match_contains(obtain_val, obtains_set)
            and match_contains(tags_val, tags_set)
            and match_contains(faction_val, factions_set)
            and match_contains(row.get("birth_place"), birthplaces_set)
            and match_contains(row.get("race"), races_set)
        ):
            continue
        filtered.append({
            "title": name,
            "profession": row.get("profession", ""),
            "branch": branch_val,
            "rarity": rarity_star,
            "position": row.get("position", ""),
            "gender": gender_val,
            "obtain": obtain_val,
            "tags": tags_val,
            "faction": faction_val,
            "birthplace": row.get("birth_place", ""),
            "race": row.get("race", ""),
            "url": row.get("url", ""),
        })

    # filter-data 不可用时回退到逐页验证旧策略
    if not filtered:
        search_terms: set[str] = set()
        if keyword:
            search_terms.add(keyword)
        for s in (professions_set, branches_set, tags_set, factions_set):
            search_terms.update(s)
        if not search_terms:
            search_terms.add("干员")
        seen: set[str] = set()
        candidates: list[str] = []
        for term in search_terms:
            for res in await client.search_pages(f"{term} 干员", limit=50):
                t = res["title"]
                if any(x in t for x in ("/", "：", "列表", "一览")):
                    continue
                if t in seen:
                    continue
                candidates.append(t)
                seen.add(t)

        semaphore = asyncio.Semaphore(8)

        async def verify(title: str) -> dict[str, object] | None:
            async with semaphore:
                if not await client._verify_operator_page(title):
                    return None
                return await client.parse_operator_complete(title)

        pages = await asyncio.gather(*(verify(c) for c in candidates))
        for data in pages:
            if data is None:
                continue
            profession = str(data.get("profession", ""))
            rarity_text = str(data.get("rarity", ""))
            m = re.search(r"(\d+)", rarity_text)
            rarity_num = m.group(1) if m else ""
            basic = data.get("basic_info") or {}
            if not isinstance(basic, dict):
                basic = {}
            row: dict[str, str] = {
                "title": str(data.get("name", "")),
                "profession": profession,
                "branch": str(basic.get("分支", "")),
                "rarity": rarity_num or rarity_text,
                "position": str(basic.get("位置", "")),
                "gender": str(basic.get("性别", "")),
                "obtain": str(basic.get("获得方式", "")),
                "tags": " ".join([str(basic.get("标签", ""))]).strip(),
                "faction": str(basic.get("所属势力", "")),
                "birthplace": str(basic.get("出身地", "")),
                "race": str(basic.get("种族", "")),
                "url": str(data.get("url", "")),
            }
            if not (
                match_contains(row["profession"], professions_set)
                and match_contains(row["branch"], branches_set)
                and match_rarity(row["rarity"])
                and match_contains(row["position"], positions_set)
                and match_contains(row["gender"], genders_set)
                and match_contains(row["obtain"], obtains_set)
                and match_contains(row["tags"], tags_set)
                and match_contains(row["faction"], factions_set)
                and match_contains(row["birthplace"], birthplaces_set)
                and match_contains(row["race"], races_set)
            ):
                continue
            filtered.append(row)

    if not filtered:
        return "# 🔍 干员多维筛选\n\n- **匹配数量**: 0\n- 如需更精准结果，可减少条件或放宽关键词。"

    def sort_key(item: dict[str, str]):
        try:
            r = int(str(item.get("rarity") or 0).replace("★", ""))
        except ValueError:
            r = 0
        return (-r, item.get("profession", ""), item.get("title", ""))

    filtered.sort(key=sort_key)
    lines = ["# 🔎 干员多维筛选结果", "", "## 📊 统计", f"- **匹配干员**: {len(filtered)}"]
    if keyword:
        lines.append(f"- **关键词**: {keyword}")
    lines.append("\n## 📋 干员列表")
    for idx, op in enumerate(filtered[:limit], 1):
        meta = [op.get("rarity", ""), op.get("profession", ""), op.get("branch", "")]
        meta = [m for m in meta if m]
        line = f"{idx:2d}. **{op['title']}**"
        if meta:
            line += f"（{' / '.join(meta)}）"
        if op.get("tags"):
            line += f" - {op['tags']}"
        lines.append(line)
    lines.append("\n---\n数据来源: https://prts.wiki/w/干员一览")
    return "\n".join(lines)
