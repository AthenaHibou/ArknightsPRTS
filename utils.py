"""PRTS.wiki 通用常量与响应辅助函数（自 Doctah-MCP 移植）。"""

from __future__ import annotations

# PRTS.wiki 基础地址
BASE_URL = "https://prts.wiki"

PROFESSION_TAGS = [
    "（医疗）",
    "（术师）",
    "（狙击）",
    "（重装）",
    "（近卫）",
    "（先锋）",
    "（辅助）",
    "（特种）",
]


def _create_operator_not_found_response(
    name: str, similar_names: list[str] | None = None
) -> str:
    """构造标准化的“干员不存在”响应。"""
    response = f"""# ❌ 干员查询失败

## 🔍 查询状态
- **状态**: 干员不存在
- **查询名称**: {name}
- **错误类型**: OPERATOR_NOT_FOUND

## 📋 可能的原因
1. **拼写错误**: 请检查干员名称的拼写
2. **名称不完整**: 一些干员需要完整名称（如"阿米娅（医疗）"）
3. **干员不存在**: 该名称可能不是有效的明日方舟干员

## 🎯 建议操作"""
    if similar_names:
        response += "\n### 相似干员名称建议：\n"
        for i, similar_name in enumerate(similar_names, 1):
            response += f"{i}. {similar_name}\n"
    else:
        response += """
1. 检查干员名称拼写
2. 尝试使用完整干员名称
3. 查看 PRTS.wiki 确认干员是否存在"""
    response += f"""
## 🔗 相关链接
- [PRTS.wiki 干员列表](https://prts.wiki/w/干员一览)
- [PRTS.wiki 首页]({BASE_URL})

---
💡 **提示**: 这是标准化的"干员不存在"响应，AI可据此判断查询失败原因。
"""
    return response


def _extract_similar_operator_names(
    search_results: list[dict[str, str]], target_name: str
) -> list[str]:
    """从搜索结果中提取与目标相似的干员名称（最多 5 个）。"""
    similar_names: list[str] = []
    target_lower = target_name.lower()
    for result in search_results:
        title = result["title"]
        if any(exclude in title for exclude in ["/干员密录", "/语音记录", "/干员模型", "/悖论模拟", "/", "："]):
            continue
        if any(prof in title for prof in PROFESSION_TAGS):
            similar_names.append(title)
        elif title.lower() != target_lower and len(title) <= 10:
            similar_names.append(title)
        if len(similar_names) >= 5:
            break
    return similar_names
