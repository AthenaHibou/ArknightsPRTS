"""PRTS.wiki 数据抓取与解析客户端（自 Doctah-MCP 的核心逻辑移植，去掉 MCP 包装层）。

供插件查询干员 / 敌人 / 筛选数据等，全部走 httpx + BeautifulSoup。
"""
from __future__ import annotations

import re
from urllib.parse import quote

import httpx
from bs4 import Comment, BeautifulSoup

from .utils import BASE_URL, PROFESSION_TAGS

SEARCH_API = f"{BASE_URL}/api.php"

# 模块级共享客户端：避免每次调用新建/关闭 httpx 会话（延迟友好）
_client: PRTSWikiClient | None = None


def get_client() -> "PRTSWikiClient":
    """获取进程内共享的 PRTS 客户端实例。"""
    global _client
    if _client is None:
        _client = PRTSWikiClient()
    return _client


class PRTSWikiClient:
    """PRTS.wiki 页面抓取与解析客户端。"""

    def __init__(self) -> None:
        self.session = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            headers={"User-Agent": "GsCore-ArknightsPRTS/1.0 (GsCore plugin)"},
        )

    async def search_pages(self, query: str, limit: int = 10) -> list[dict[str, str]]:
        """使用 wiki 搜索 API 检索页面。"""
        try:
            params = {
                "action": "query",
                "format": "json",
                "list": "search",
                "srsearch": query,
                "srlimit": limit,
                "srprop": "title|snippet",
            }
            response = await self.session.get(SEARCH_API, params=params)
            response.raise_for_status()
            data = response.json()
            results: list[dict[str, str]] = []
            for item in data.get("query", {}).get("search", []):
                title = item["title"]
                results.append(
                    {
                        "title": title,
                        "snippet": item.get("snippet", ""),
                        "url": f"{BASE_URL}/w/{quote(title)}",
                    }
                )
            return results
        except Exception:
            return []

    async def get_page_html(self, title: str) -> str:
        """抓取页面 HTML 文本。"""
        try:
            url = f"{BASE_URL}/w/{quote(title)}"
            response = await self.session.get(url)
            response.raise_for_status()
            return response.text
        except Exception:
            return ""

    def extract_text_from_cell(self, cell) -> str:
        """从表格单元格提取纯文本，清理 HTML 标签与特殊标记。"""
        if cell is None:
            return ""
        for comment in cell.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()
        for tag in cell.find_all(["script", "style"]):
            tag.decompose()
        try:
            for span in cell.find_all("span"):
                if span and span.get("style"):
                    if "display:none" in span.get("style", ""):
                        span.decompose()
        except Exception:
            pass
        text = cell.get_text(separator=" ", strip=True)
        text = re.sub(r"显示算法.*?(?=\s|$)", "", text)
        text = re.sub(r"直接乘算.*?(?=\s|$)", "", text)
        text = re.sub(r"里属于叠加.*?(?=\s|$)", "", text)
        text = re.sub(r"为.*?乘算", "", text)
        text = re.sub(r"\[\s*注\s*\d+\s*\]", "", text)
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"^\s*：\s*", "", text)
        return text.strip()

    def extract_table_of_contents(self, soup: BeautifulSoup) -> dict[str, dict[str, object]]:
        """提取页面目录结构，返回 {section_id: {title, level, anchor}}。"""
        toc: dict[str, dict[str, object]] = {}
        toc_div = soup.find("div", {"id": "toc"}) or soup.find("div", class_="toc")
        if toc_div:
            for link in toc_div.find_all("a"):
                href = link.get("href", "")
                if href.startswith("#"):
                    section_id = href[1:]
                    toc[section_id] = {
                        "title": link.get_text(strip=True),
                        "level": len(link.find_parents("li", recursive=False)),
                        "anchor": section_id,
                    }
        else:
            for heading in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
                if heading.get("id"):
                    section_id = heading.get("id")
                    toc[section_id] = {
                        "title": heading.get_text(strip=True),
                        "level": int(heading.name[1]),
                        "anchor": section_id,
                    }
        return toc

    def extract_section_content(self, soup: BeautifulSoup, section_id: str) -> str:
        """提取指定章节的文本与表格内容。"""
        content: list[str] = []
        section_heading = soup.find(id=section_id)
        if not section_heading:
            return ""
        if section_heading.name not in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            section_heading = section_heading.find_parent(["h1", "h2", "h3", "h4", "h5", "h6"])
        if not section_heading:
            return ""
        current_level = int(section_heading.name[1])
        next_element = section_heading.next_sibling
        while next_element:
            if hasattr(next_element, "name"):
                if next_element.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                    next_level = int(next_element.name[1])
                    if next_level <= current_level:
                        break
                if next_element.name == "table":
                    table_content = self.extract_table_content(next_element)
                    if table_content:
                        content.append(table_content)
                elif next_element.name in ["p", "div", "ul", "ol", "dl"]:
                    text = self.extract_text_from_cell(next_element)
                    if text:
                        content.append(text)
            next_element = next_element.next_sibling
        return "\n\n".join(content) if content else ""

    def extract_table_content(self, table) -> str:
        """把表格转换为按行用 `|` 拼接的 markdown 文本。"""
        content: list[str] = []
        for row in table.find_all("tr"):
            cells = row.find_all(["th", "td"])
            if cells:
                row_data = [self.extract_text_from_cell(cell) for cell in cells]
                if any(row_data):
                    content.append(" | ".join(row_data))
        return "\n".join(content) if content else ""

    async def _verify_operator_page(self, title: str) -> bool:
        """验证页面是否真的是干员页面。"""
        try:
            html = await self.get_page_html(title)
            if not html:
                return False
            soup = BeautifulSoup(html, "lxml")
            for heading in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
                if "干员信息" in heading.get_text(strip=True):
                    return True
            page_text = soup.get_text()
            if any(indicator in page_text for indicator in ["★★★★★★", "★★★★★", "★★★★", "★★★", "精英化", "潜能提升"]):
                return True
            if any(prof in page_text for prof in
                   ["医疗干员", "术师干员", "狙击干员", "重装干员", "近卫干员", "先锋干员", "辅助干员", "特种干员"]):
                return True
            return False
        except Exception:
            return False

    async def _verify_enemy_page(self, title: str) -> bool:
        """验证页面是否真的是敌人页面。"""
        try:
            html = await self.get_page_html(title)
            if not html:
                return False
            soup = BeautifulSoup(html, "lxml")
            for heading in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
                heading_text = heading.get_text(strip=True)
                if "敌人模型" in heading_text or any(lv in heading_text for lv in ["级别0", "级别1", "级别2"]):
                    return True
            page_text = soup.get_text()
            if "移动速度" in page_text and "攻击间隔" in page_text and "重量" in page_text:
                return True
            return False
        except Exception:
            return False

    def _is_enemy_page(self, soup: BeautifulSoup) -> bool:
        """判断当前解析的页面是否为敌人页面。"""
        if soup.find("a", href="/w/敌人一览"):
            return True
        enemy_sections = ["级别0", "级别1", "级别2", "敌人模型"]
        for heading in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
            if any(section in heading.get_text(strip=True) for section in enemy_sections):
                return True
        toc_div = soup.find("div", {"id": "toc"}) or soup.find("div", class_="toc")
        if toc_div and any(section in toc_div.get_text() for section in enemy_sections):
            return True
        for table in soup.find_all("table"):
            table_text = table.get_text()
            if "生命值" in table_text and "攻击力" in table_text and "防御力" in table_text:
                if any(attr in table_text for attr in ["移动速度", "攻击间隔", "重量", "阻挡数"]):
                    return True
        return False

    def _extract_basic_info(self, soup: BeautifulSoup) -> dict[str, str]:
        """提取干员基本信息表。"""
        basic_info: dict[str, str] = {}
        for table in soup.find_all("table"):
            for row in table.find_all("tr"):
                cells = row.find_all(["th", "td"])
                if len(cells) >= 2:
                    key = self.extract_text_from_cell(cells[0])
                    value = self.extract_text_from_cell(cells[1])
                    if not key or not value:
                        continue
                    key_norm = key.replace("：", "").replace(":", "").strip()
                    def contains_any(text: str, keywords: list[str]) -> bool:
                        return any(k in text for k in keywords)
                    if contains_any(key_norm, ["再部署", "部署时间"]):
                        basic_info["再部署时间"] = value
                    elif "阻挡" in key_norm:
                        basic_info["阻挡数"] = value
                    elif contains_any(key_norm, ["所属势力", "势力", "组织", "阵营"]) and "隐藏" not in key_norm:
                        basic_info["所属势力"] = value
                    elif "隐藏势力" in key_norm:
                        basic_info["隐藏势力仅在战斗中所使用的数据"] = value
                    elif "攻击间隔" in key_norm:
                        basic_info["攻击间隔"] = value
                    elif "部署费用" in key_norm:
                        basic_info["部署费用"] = value
                    elif contains_any(key_norm, ["职业", "职能"]) and "分支" not in key_norm:
                        basic_info["职业"] = value
                    elif "分支" in key_norm or contains_any(key_norm, ["子职业", "子职"]):
                        basic_info["分支"] = value
                    elif "位置" in key_norm:
                        basic_info["位置"] = value
                    elif "性别" in key_norm:
                        basic_info["性别"] = value
                    elif contains_any(key_norm, ["出身地", "籍贯"]):
                        basic_info["出身地"] = value
                    elif "种族" in key_norm:
                        basic_info["种族"] = value
                    elif contains_any(key_norm, ["标签", "词缀"]):
                        basic_info["标签"] = value
                    elif contains_any(key_norm, ["获得方式", "获取方式", "获取途径"]):
                        basic_info["获得方式"] = value
        return basic_info

    def _extract_profession_rarity(self, soup: BeautifulSoup) -> tuple[str, str]:
        """提取职业与稀有度，返回 (profession, rarity)。"""
        profession = ""
        rarity = ""
        star_imgs = soup.find_all("img", alt=re.compile(r"稀有度"))
        for img in star_imgs:
            alt_text = img.get("alt", "")
            if "星" in alt_text:
                rarity = alt_text
                break
        profession_imgs = soup.find_all("img", alt=re.compile(r"(医疗|术师|狙击|重装|近卫|先锋|辅助|特种)"))
        for img in profession_imgs:
            alt_text = img.get("alt", "")
            for prof in ["医疗", "术师", "狙击", "重装", "近卫", "先锋", "辅助", "特种"]:
                if prof in alt_text:
                    profession = prof
                    break
            if profession:
                break
        return profession, rarity

    _SECTION_MAPPING: dict[str, str] = {
        "干员信息": "operator_info",
        "特性": "characteristics",
        "获得方式": "acquisition",
        "属性": "attributes",
        "攻击范围": "attack_range",
        "天赋": "talents",
        "潜能提升": "potential",
        "技能": "skills",
        "后勤技能": "base_skills",
        "精英化材料": "elite_materials",
        "技能升级材料": "skill_materials",
        "模组": "modules",
        "相关道具": "related_items",
        "干员档案": "operator_record",
        "语音记录": "voice_records",
        "干员密录": "operator_files",
        "悖论模拟": "paradox_simulation",
        "干员模型": "operator_model",
        "注释与链接": "notes_and_links",
    }

    _SECTION_ICONS: dict[str, str] = {
        "characteristics": "⚡",
        "acquisition": "🎁",
        "attributes": "📊",
        "attack_range": "🎯",
        "talents": "🌟",
        "potential": "💎",
        "skills": "🎯",
        "base_skills": "🏢",
        "elite_materials": "⭐",
        "skill_materials": "📚",
        "modules": "🔧",
        "related_items": "🎒",
        "operator_record": "📜",
        "voice_records": "🎤",
        "operator_files": "📁",
        "paradox_simulation": "🎮",
        "operator_model": "🎨",
        "notes_and_links": "🔗",
    }

    async def parse_operator_complete(
        self, title: str, sections: list[str] | None = None
    ) -> dict[str, object] | None:
        """完整解析干员页面，支持章节过滤；敌人页返回 type='enemy'。"""
        html = await self.get_page_html(title)
        if not html:
            return None
        soup = BeautifulSoup(html, "html.parser")
        if self._is_enemy_page(soup):
            return {"type": "enemy", "name": title, "url": f"{BASE_URL}/w/{quote(title)}"}

        toc = self.extract_table_of_contents(soup)
        operator_data: dict[str, object] = {
            "type": "operator",
            "name": title,
            "url": f"{BASE_URL}/w/{quote(title)}",
            "table_of_contents": toc,
            "sections": {},
        }
        target = sections if sections else [
            s for s in self._SECTION_MAPPING
            if not any(skip in s for skip in ("注释与链接", "干员模型"))
        ]
        for section_title in target:
            section_key = self._SECTION_MAPPING.get(section_title)
            if not section_key:
                continue
            section_id = None
            for toc_id, toc_info in toc.items():
                toc_title = str(toc_info["title"])
                if section_title == toc_id or section_title in toc_title or toc_title.endswith(section_title):
                    section_id = toc_id
                    break
            if section_id:
                content = self.extract_section_content(soup, section_id)
                if content:
                    cast_sections = operator_data["sections"]
                    assert isinstance(cast_sections, dict)
                    cast_sections[section_key] = {"title": section_title, "content": content}

        operator_data["basic_info"] = self._extract_basic_info(soup)
        profession, rarity = self._extract_profession_rarity(soup)
        if profession:
            operator_data["profession"] = profession
        if rarity:
            operator_data["rarity"] = rarity
        return operator_data

    async def parse_enemy_complete(
        self, title: str, target_sections: list[str] | None = None
    ) -> dict[str, object] | None:
        """解析敌人页面完整信息。"""
        try:
            html = await self.get_page_html(title)
            if not html:
                return None
            soup = BeautifulSoup(html, "lxml")
            if not self._is_enemy_page(soup):
                return None
            enemy_data: dict[str, object] = {
                "title": title,
                "type": "enemy",
                "basic_info": {},
                "levels": {},
                "table_of_contents": {},
                "sections": {},
            }
            toc = self.extract_table_of_contents(soup)
            enemy_data["table_of_contents"] = toc
            enemy_data["basic_info"] = self._extract_enemy_basic_info(soup)

            all_sections: dict[str, object] = {}
            skip_sections = ("敌人模型", "导航菜单")
            for section_id, section_info in toc.items():
                section_title = str(section_info["title"])
                if any(skip in section_title for skip in skip_sections):
                    continue
                if target_sections and not any(target in section_title for target in target_sections):
                    continue
                content = self.extract_section_content(soup, section_id)
                if content:
                    all_sections[section_id] = {"title": section_title, "content": content}
            enemy_data["sections"] = all_sections
            return enemy_data
        except Exception:
            return None

    def _extract_enemy_basic_info(self, soup: BeautifulSoup) -> dict[str, str]:
        """提取敌人基本信息。"""
        basic_info: dict[str, str] = {}
        for table in soup.find_all("table"):
            for row in table.find_all("tr"):
                cells = row.find_all(["th", "td"])
                if len(cells) >= 2:
                    header = self.extract_text_from_cell(cells[0])
                    value = self.extract_text_from_cell(cells[1])
                    if any(keyword in header for keyword in ["分类", "种族", "重量", "阻挡数"]):
                        basic_info[header] = value
        return basic_info

    def format_enemy_info(
        self, enemy_data: dict[str, object], target_sections: list[str] | None = None
    ) -> str:
        """格式化敌人信息为 markdown 文本。"""
        if not enemy_data:
            return "敌人信息解析失败"
        title = str(enemy_data.get("title", "未知敌人"))
        result: list[str] = [f"# {title}"]
        basic_info = enemy_data.get("basic_info", {})
        if basic_info:
            result.append("\n## 📋 基本信息")
            for k, v in basic_info.items():
                result.append(f"- **{k}**: {v}")
        sections = enemy_data.get("sections", {})
        if isinstance(sections, dict):
            for section_id, section_info in sections.items():
                if isinstance(section_info, dict):
                    result.append(f"\n## {section_info.get('title', section_id)}")
                    result.append(str(section_info.get("content", "")))
        if not target_sections:
            toc = enemy_data.get("table_of_contents", {})
            if isinstance(toc, dict) and toc:
                result.append("\n## 📚 页面目录")
                for section_id, section_info in toc.items():
                    if isinstance(section_info, dict):
                        level = int(section_info.get("level", 1))
                        indent = "  " * (level - 1)
                        result.append(f"{indent}- {section_info.get('title', section_id)}")
        return "\n".join(result)

    async def get_operator_filter_data(self) -> list[dict[str, str]]:
        """解析『干员一览』隐藏节点 #filter-data 的筛选数据。"""
        html = await self.get_page_html("干员一览")
        if not html:
            return []
        soup = BeautifulSoup(html, "lxml")
        filter_div = soup.find(id="filter-data")
        if not filter_div:
            return []
        operators: list[dict[str, str]] = []
        for div in filter_div.find_all("div"):
            attrs: dict[str, str] = {}
            for k, v in div.attrs.items():
                if not k.startswith("data-"):
                    continue
                if v is None:
                    continue
                attrs[k[5:]] = v
            if not attrs:
                continue
            name_zh = attrs.get("zh") or attrs.get("name")
            if name_zh:
                attrs["url"] = f"{BASE_URL}/w/{quote(name_zh)}"
            operators.append(attrs)
        return operators

    async def get_enemy_filter_data(self) -> list[dict[str, object]]:
        """获取『敌人一览/数据』JSON 列表。"""
        try:
            params = {
                "title": "敌人一览/数据",
                "action": "raw",
                "ctype": "application/json",
            }
            resp = await self.session.get(f"{BASE_URL}/index.php", params=params)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                items: list[dict[str, object]] = []
                for item in data:
                    if isinstance(item, dict):
                        link = item.get("enemyLink") or item.get("name")
                        if link:
                            item["url"] = f"{BASE_URL}/w/{quote(str(link))}"
                        items.append(item)
                return items
            return []
        except Exception:
            return []

    def format_operator(
        self, operator_data: dict[str, object], target_sections: list[str] | None = None
    ) -> str:
        """把干员解析结果格式化为 markdown 文本。"""
        name = str(operator_data.get("name", ""))
        result: list[str] = [f"# {name}", ""]
        basic_info = operator_data.get("basic_info", {})
        if isinstance(basic_info, dict) and not target_sections:
            if basic_info:
                result.append("## 📋 基本信息")
                for k, v in basic_info.items():
                    result.append(f"- **{k}**: {v}")
                result.append("")
            profession = operator_data.get("profession")
            rarity = operator_data.get("rarity")
            if profession or rarity:
                result.append("## 📊 基础数据")
                if profession:
                    result.append(f"- **职业**: {profession}")
                if rarity:
                    result.append(f"- **稀有度**: {rarity}")
                result.append("")
            toc = operator_data.get("table_of_contents", {})
            if isinstance(toc, dict) and toc:
                result.append("## 📚 页面目录")
                for toc_id, toc_info in toc.items():
                    if isinstance(toc_info, dict):
                        title = str(toc_info.get("title", toc_id))
                        if any(skip in title for skip in ("注释与链接", "干员模型")):
                            continue
                        level = int(toc_info.get("level", 1))
                        result.append(("  " * (level - 1)) + f"- {title}")
                result.append("")
        sections = operator_data.get("sections", {})
        if isinstance(sections, dict):
            for key, section in sections.items():
                if isinstance(section, dict):
                    line = str(section.get("content", ""))
                    if line:
                        result.append(f"## {self._SECTION_ICONS.get(key, '📋')} {section.get('title', key)}")
                        result.append(line)
                        result.append("")
        result.append(f"---\n📍 **页面链接**: {operator_data.get('url', '')}")
        return "\n".join(result)

    def matches_profession(self, title: str) -> bool:
        """判断页面标题是否带职业标识（干员主页面）。"""
        return any(prof in title for prof in PROFESSION_TAGS)
