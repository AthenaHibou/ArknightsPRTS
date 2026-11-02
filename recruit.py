"""公招计算（公开招募标签匹配，自 Doctah-MCP 移植，数据源为 PRTS cargoquery）。"""

from __future__ import annotations

from urllib.parse import quote

from .client import BASE_URL, get_client

PROFESSIONS = ["近卫", "狙击", "重装", "医疗", "辅助", "术师", "特种", "先锋"]
POSITIONS = ["近战位", "远程位"]
RARITY_TAGS = ["高级资深干员", "资深干员", "新手"]
TAG_WORDS = [
    "支援机械", "控场", "爆发", "治疗", "支援", "费用回复", "输出", "生存",
    "群攻", "防护", "减速", "削弱", "快速复活", "位移", "召唤", "元素",
]

PROF_ALIASES = {
    "近卫干员": "近卫", "狙击干员": "狙击", "重装干员": "重装", "医疗干员": "医疗",
    "辅助干员": "辅助", "术师干员": "术师", "特种干员": "特种", "先锋干员": "先锋",
}
POS_ALIASES = {"近战": "近战位", "远程": "远程位", "近战位": "近战位", "远程位": "远程位"}
RARITY_ALIASES = {
    "高资": "高级资深干员",
    "高资深": "高级资深干员",
    "资深": "资深干员",
    "资深干员": "资深干员",
    "新手干员": "新手",
}
TAG_ALIASES = {"费用回收": "费用回复"}

_CARGO_PARAMS = {
    "action": "cargoquery",
    "format": "json",
    "tables": "chara,char_obtain",
    "limit": "5000",
    "fields": "chara.profession,chara.position,chara.rarity,chara.tag,chara.cn,char_obtain.obtainMethod",
    "where": 'char_obtain.obtainMethod like "%公开%招募%" AND chara.charIndex>0',
    "join_on": "chara._pageName=char_obtain._pageName",
}


def _split_terms(terms: str | None) -> list[str]:
    if not terms:
        return []
    text = terms
    for sep in [",", "，", "、", "|", " "]:
        text = text.replace(sep, ",")
    tokens = [t.strip() for t in text.split(",") if t.strip()]
    normed: list[str] = []
    for token in tokens:
        t2 = RARITY_ALIASES.get(token, PROF_ALIASES.get(token, POS_ALIASES.get(token, TAG_ALIASES.get(token, token))))
        if t2.endswith("干员"):
            t2 = t2[:-2]
        normed.append(t2)
    return normed


def _classify_terms(terms: list[str]) -> tuple[set[str], set[str], set[str], list[str]]:
    pros: set[str] = set()
    poss: set[str] = set()
    rars: set[str] = set()
    tags: list[str] = []
    for term in terms:
        if term in PROFESSIONS:
            pros.add(term)
        elif term in POSITIONS or term in POS_ALIASES.values():
            poss.add(POS_ALIASES.get(term, term))
        elif term in RARITY_TAGS or term in RARITY_ALIASES.values():
            rars.add(RARITY_ALIASES.get(term, term))
        elif term in TAG_WORDS or term in TAG_ALIASES.values():
            tags.append(TAG_ALIASES.get(term, term))
        else:
            if term.endswith("干员") and term[:-2] in PROFESSIONS:
                pros.add(term[:-2])
            else:
                tags.append(term)
    return pros, poss, rars, tags


async def _fetch_recruit_candidates() -> list[dict[str, object]]:
    """从 PRTS cargoquery 拉取可公开招募的干员原始数据。"""
    client = get_client()
    resp = await client.session.get(f"{BASE_URL}/api.php", params=_CARGO_PARAMS)
    resp.raise_for_status()
    data = resp.json().get("cargoquery", [])
    candidates: list[dict[str, object]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        title = item.get("title", {})
        if not isinstance(title, dict):
            continue
        name = title.get("cn")
        if not name:
            continue
        candidates.append(title)
    return candidates


async def recruit_by_tags(terms: str) -> str:
    """按词条计算公招可能出现的干员（职业/位置/资历 OR，词缀 AND）。"""
    selected = _split_terms(terms)
    if not selected:
        return "# ❌ 公招计算失败\n\n- **状态**: 缺少筛选词条\n- **示例**: 资深干员, 术师, 群攻 或 先锋 费用回复"

    pros, poss, rars, tag_need = _classify_terms(selected)
    candidates = await _fetch_recruit_candidates()
    matched: list[dict[str, object]] = []
    for title in candidates:
        name = str(title.get("cn"))
        rarity_num = int(title.get("rarity", "0") or 0)
        tags = str(title.get("tag", "") or "").split(" ") if title.get("tag") else []
        rarity_tag = "高级资深干员" if rarity_num == 5 else ("资深干员" if rarity_num == 4 else None)
        if pros and (title.get("profession") not in pros):
            continue
        if poss and (title.get("position") not in poss):
            continue
        if rars and (rarity_tag not in rars):
            continue
        if tag_need and not set(tag_need).issubset(set(tags)):
            continue
        matched.append({
            "name": name,
            "rarity": rarity_num + 1,
            "profession": str(title.get("profession", "")),
            "position": str(title.get("position", "")),
            "tags": tags,
            "rarity_tag": rarity_tag or "",
            "hit_tags": [t for t in tag_need if t in tags],
            "url": f"{BASE_URL}/w/{quote(name)}",
        })

    if not matched:
        return "# 🔍 公招计算\n\n" f"- **匹配数量**: 0\n- **词条**: {', '.join(selected)}\n" \
               "- 可能原因：互斥职业 / 词缀组合过苛 / 词条拼写或别名不一致。"

    matched.sort(key=lambda x: (-int(x["rarity"]), str(x["profession"]), str(x["name"])))
    groups: dict[int, list[dict[str, object]]] = {}
    for item in matched:
        groups.setdefault(int(item["rarity"]), []).append(item)

    lines = ["# 🎯 公招计算结果", "", f"- **词条**: {', '.join(selected)}", f"- **匹配干员**: {len(matched)}", ""]
    for rarity in sorted(groups.keys(), reverse=True):
        lines.append(f"## {rarity}★")
        for op in groups[rarity]:
            meta = [str(op["profession"]), str(op["position"]), " ".join(op["tags"])[:60]]
            meta = [m for m in meta if m]
            lines.append(f"- **{op['name']}**（{' / '.join(meta)}）")
            reason = []
            if op.get("profession"):
                reason.append(f"职业={op['profession']}")
            if op.get("position"):
                reason.append(f"位置={op['position']}")
            if op.get("rarity_tag"):
                reason.append(f"资历={op['rarity_tag']}")
            if op.get("hit_tags"):
                reason.append(f"词缀命中={','.join(op['hit_tags'])}")
            if reason:
                lines.append(f"  匹配依据: {'；'.join(reason)}")
            lines.append(f"  链接: {op['url']}")
        lines.append("")
    lines.append("---")
    lines.append("数据来源: 公招计算 / cargoquery")
    return "\n".join(lines)


async def recruit_by_tags_suggest(terms: str, top_k: int = 8) -> str:
    """自动寻找能产出结果的最佳词条子集组合。"""
    selected = _split_terms(terms)
    if not selected:
        return "# ❌ 公招计算（建议组合）\n\n- **状态**: 缺少词条"

    universe = PROFESSIONS + POSITIONS + RARITY_TAGS + TAG_WORDS
    idx = {name: i for i, name in enumerate(universe)}
    sel_bits = 0
    for t in selected:
        if t in idx:
            sel_bits |= 1 << idx[t]

    candidates = await _fetch_recruit_candidates()
    groups: dict[int, dict[str, object]] = {}
    high_bit = idx.get("高级资深干员", -1)

    for title in candidates:
        name = str(title.get("cn"))
        star = int(title.get("rarity", "0") or 0) + 1
        tags = str(title.get("tag", "") or "").split(" ") if title.get("tag") else []
        profession = str(title.get("profession", ""))
        position = str(title.get("position", ""))
        rarity_tag = "高级资深干员" if star == 6 else ("资深干员" if star == 5 else None)
        op_bits = 0
        if profession in idx:
            op_bits |= 1 << idx[profession]
        if position in idx:
            op_bits |= 1 << idx[position]
        if rarity_tag and rarity_tag in idx:
            op_bits |= 1 << idx[rarity_tag]
        for tg in tags:
            if tg in idx:
                op_bits |= 1 << idx[tg]
        for subset in _subset_bitsets(op_bits):
            if (sel_bits | subset) != sel_bits:
                continue
            if star == 6 and high_bit >= 0 and not (subset & (1 << high_bit)):
                continue
            g = groups.setdefault(subset, {"ops": [], "stars": []})
            ops = g["ops"]
            assert isinstance(ops, list)
            stars = g["stars"]
            assert isinstance(stars, list)
            ops.append({"name": name, "star": star, "profession": profession, "position": position,
                        "url": f"{BASE_URL}/w/{quote(name)}"})
            stars.append(star)

    if not groups:
        return "# 🔍 公招计算（建议组合）\n\n" f"- **词条**: {', '.join(selected)}\n- 没有能产生结果的组合"

    def score(item: tuple[int, dict[str, object]]) -> tuple[float, int]:
        subset, g = item
        stars = g.get("stars", [])
        if isinstance(stars, list):
            avg = sum(int(x) for x in stars) / max(1, len(stars))
            return (avg, len(stars))
        return (0.0, 0)

    ordered = sorted(groups.items(), key=score, reverse=True)[:top_k]

    def names(subset_key: int) -> list[str]:
        out: list[str] = []
        for i, name_t in enumerate(universe):
            if subset_key & (1 << i):
                out.append(name_t)
        return out

    lines = ["# 🎯 公招计算建议组合", "", f"- **词条**: {', '.join(selected)}", f"- **组合数**: {len(ordered)}", ""]
    for subset, g in ordered:
        title_str = "+".join(names(subset))
        stars = g.get("stars", [])
        ops = g.get("ops", [])
        if isinstance(stars, list):
            avg = sum(int(x) for x in stars) / max(1, len(stars))
            lines.append(f"## {title_str}  — 平均星级≈{avg:.2f}，人数={len(stars)}")
        if isinstance(ops, list):
            for op in sorted(ops, key=lambda x: (-int(x["star"]), str(x["profession"]), str(x["name"]))):
                lines.append(f"- **{op['name']}**（{op['star']}★ / {op['profession']} / {op['position']}）")
                lines.append(f"  链接: {op['url']}")
        lines.append("")
    lines.append("---")
    lines.append("数据来源: 公招计算 / cargoquery（建议组合）")
    return "\n".join(lines)


def _subset_bitsets(bitmask: int) -> list[int]:
    """返回 bitmask 的所有非空子集位图。"""
    bits: list[int] = []
    i = 0
    while (1 << i) <= bitmask:
        if bitmask & (1 << i):
            bits.append(i)
        i += 1
    res: list[int] = []
    total = 1 << len(bits)
    for s in range(1, total):
        v = 0
        for j, bi in enumerate(bits):
            if s & (1 << j):
                v |= 1 << bi
        res.append(v)
    return res
