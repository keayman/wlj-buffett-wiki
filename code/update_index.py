#!/usr/bin/env python3
"""
update_index.py — 扫描 wiki/ 所有页面，重新生成 index.md（按分类组织的表格目录）。
"""

import re
import yaml
from pathlib import Path
from datetime import date

BASE_DIR = Path(__file__).parent.parent
WIKI_DIR = BASE_DIR / "wiki"
INDEX_PATH = WIKI_DIR / "index.md"

CATEGORY_DISPLAY = {
    "concept": ("💡 核心概念", "concepts"),
    "company": ("🏢 投资公司", "companies"),
    "person": ("👤 关键人物", "people"),
    "interview-summary": ("🎤 访谈与演讲", "interviews"),
    "letter-summary": ("✉️ 股东信 / 合伙人信", "letters"),
    "insight": ("🔍 交叉分析", "insights"),
}

ORDER = ["concept", "company", "person", "interview-summary", "letter-summary", "insight"]


def parse_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    
    try:
        fm = yaml.safe_load(parts[1])
        return fm or {}
    except Exception:
        return {}


def collect_pages():
    pages = {t: [] for t in ORDER}
    
    for md_file in WIKI_DIR.rglob("*.md"):
        if md_file.name in ("SCHEMA.md", "README.md", "index.md", "log.md"):
            continue
        
        fm = parse_frontmatter(md_file)
        if not fm:
            continue
        
        page_type = fm.get("type", "unknown")
        if page_type not in pages:
            continue
        
        # 相对路径（供链接使用）
        rel_path = md_file.relative_to(WIKI_DIR)
        
        pages[page_type].append({
            "title": fm.get("title", md_file.stem),
            "date": fm.get("date", ""),
            "tags": fm.get("tags", []),
            "path": rel_path,
            "filename": md_file.stem,
        })
    
    # 排序
    for t in pages:
        pages[t].sort(key=lambda x: (str(x.get("date", "")), x["title"]))
    
    return pages


def generate_index(pages: dict) -> str:
    today = date.today().isoformat()
    lines = [
        "---",
        'title: "知识库全索引"',
        "type: index",
        f"updated: {today}",
        "---",
        "",
        "# 知识库全索引",
        "",
        f"> 自动生成于 {today}，共 {sum(len(v) for v in pages.values())} 个页面",
        "",
    ]
    
    # 统计摘要
    lines.append("## 内容统计")
    lines.append("")
    lines.append("| 分类 | 页面数 |")
    lines.append("|------|--------|")
    for t in ORDER:
        if not pages.get(t):
            continue
        display, _ = CATEGORY_DISPLAY.get(t, (t, t))
        lines.append(f"| {display} | {len(pages[t])} |")
    lines.append("")
    
    # 分类目录
    for t in ORDER:
        if not pages.get(t):
            continue
        display, _ = CATEGORY_DISPLAY.get(t, (t, t))
        lines.append(f"## {display}")
        lines.append("")
        lines.append("| 标题 | 日期 | 标签 |")
        lines.append("|------|------|------|")
        
        for p in pages[t]:
            title = p["title"]
            date_str = p.get("date", "")
            tags = ", ".join(str(tag) for tag in p.get("tags", []))
            link_path = str(p["path"]).replace("\\", "/")
            lines.append(f"| [[{p['filename']}\\|{title}]] | {date_str} | {tags} |")
        
        lines.append("")
    
    return "\n".join(lines)


def main():
    print("扫描 wiki/ 页面...")
    pages = collect_pages()
    
    total = sum(len(v) for v in pages.values())
    for t in ORDER:
        count = len(pages.get(t, []))
        if count:
            display, _ = CATEGORY_DISPLAY.get(t, (t, t))
            print(f"  {display}: {count} 个")
    print(f"  总计: {total} 个")
    
    index_content = generate_index(pages)
    INDEX_PATH.write_text(index_content, encoding="utf-8")
    print(f"\n✓ 已生成 {INDEX_PATH.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()
