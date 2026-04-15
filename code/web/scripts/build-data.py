#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build-data.py — 扫描 wiki/ 生成前端所需的 JSON 数据文件。

输出：
  public/data/wiki-index.json     — 所有页面元数据
  public/data/graph.json          — 知识图谱（节点+边）
  public/data/search-index.json   — 搜索索引
  public/data/pages/*/            — wiki 页面 Markdown 副本
  public/data/raw/                — 原文副本
"""

import os
import re
import json
import shutil
from pathlib import Path
from datetime import date

# ── 路径配置 ──────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
WEB_DIR = SCRIPT_DIR.parent
BASE_DIR = WEB_DIR.parent.parent   # buffet1/

WIKI_DIR = BASE_DIR / "wiki"
RAW_DIR  = BASE_DIR / "raw"
DATA_DIR = WEB_DIR / "public" / "data"
PAGES_DIR = DATA_DIR / "pages"
RAW_OUT_DIR = DATA_DIR / "raw"

# ── 分类映射 ──────────────────────────────────────────────────────────────────
CATEGORY_DIRS = {
    "concepts":   ("concept",              WIKI_DIR / "concepts"),
    "companies":  ("company",              WIKI_DIR / "companies"),
    "people":     ("person",               WIKI_DIR / "people"),
    "interviews": ("interview-summary",    WIKI_DIR / "interviews"),
    "letters":    ("letter-summary",       WIKI_DIR / "letters"),
    "insights":   ("insight",              WIKI_DIR / "insights"),
}

# ── 解析 frontmatter ──────────────────────────────────────────────────────────
def parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    
    fm = {}
    for line in parts[1].strip().split("\n"):
        m = re.match(r'^(\w+):\s*(.+)$', line)
        if m:
            key = m.group(1)
            val = m.group(2).strip().strip('"').strip("'")
            # 处理列表（tags, related）
            if val.startswith('[') and val.endswith(']'):
                inner = val[1:-1]
                items = [x.strip().strip('"').strip("'") for x in inner.split(',') if x.strip()]
                fm[key] = items
            else:
                fm[key] = val
    
    body = parts[2].strip()
    return fm, body


# ── 提取摘要 ──────────────────────────────────────────────────────────────────
def extract_summary(body: str, max_len: int = 200) -> str:
    """从正文提取摘要（去掉标题行，取第一段）"""
    lines = body.split("\n")
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith("-"):
            # 去掉 [[链接]] 格式
            clean = re.sub(r'\[\[([^\]|]+?)(?:\|[^\]]+?)?\]\]', r'\1', stripped)
            if len(clean) > 30:
                return clean[:max_len] + ("..." if len(clean) > max_len else "")
    return ""


# ── 提取双向链接 ──────────────────────────────────────────────────────────────
def extract_links(text: str) -> list:
    """提取文中所有 [[实体名]] 双向链接"""
    matches = re.findall(r'\[\[([^\]|]+?)(?:\|[^\]]+?)?\]\]', text)
    return list(dict.fromkeys(matches))  # 去重保序


# ── 建立 wiki-index.json ──────────────────────────────────────────────────────
def build_wiki_index() -> list:
    pages = []
    
    for cat, (page_type, wiki_subdir) in CATEGORY_DIRS.items():
        if not wiki_subdir.exists():
            continue
        
        for md_file in sorted(wiki_subdir.glob("*.md")):
            text = md_file.read_text(encoding="utf-8")
            fm, body = parse_frontmatter(text)
            
            if not fm:
                continue
            
            title = fm.get("title", md_file.stem)
            slug = md_file.stem
            links = extract_links(body)
            summary = fm.get("summary", extract_summary(body))
            
            pages.append({
                "title": title,
                "slug": slug,
                "type": fm.get("type", page_type),
                "category": cat,
                "date": fm.get("date", ""),
                "source": fm.get("source", ""),
                "tags": fm.get("tags", []),
                "summary": summary,
                "links": links,
                "path": f"{cat}/{slug}",
            })
    
    print(f"  wiki-index: {len(pages)} 个页面")
    return pages


# ── 建立 graph.json ───────────────────────────────────────────────────────────
def build_graph(index: list) -> dict:
    """从双向链接生成图谱节点和边"""
    # 建立 title → category/type 映射
    title_map = {p["title"]: p for p in index}
    
    nodes = []
    nodes_set = set()
    edges = []
    edges_set = set()
    
    # 添加所有已知页面为节点
    for p in index:
        if p["title"] not in nodes_set:
            nodes.append({"id": p["title"], "type": p["type"], "category": p["category"]})
            nodes_set.add(p["title"])
    
    # 从链接生成边
    for p in index:
        src = p["title"]
        for link in p.get("links", []):
            tgt = link
            # 如果目标节点不存在，添加为 unknown 节点
            if tgt not in nodes_set:
                nodes.append({"id": tgt, "type": "unknown", "category": "unknown"})
                nodes_set.add(tgt)
            
            # 避免重复边（无向）
            edge_key = tuple(sorted([src, tgt]))
            if edge_key not in edges_set:
                edges.append({"source": src, "target": tgt})
                edges_set.add(edge_key)
    
    print(f"  graph: {len(nodes)} 节点，{len(edges)} 边")
    return {"nodes": nodes, "edges": edges}


# ── 建立 search-index.json ────────────────────────────────────────────────────
def build_search_index(index: list) -> list:
    """精简版搜索索引（标题+摘要+标签）"""
    return [
        {
            "title": p["title"],
            "slug": p["slug"],
            "category": p["category"],
            "type": p["type"],
            "summary": p.get("summary", ""),
            "tags": p.get("tags", []),
            "path": p["path"],
        }
        for p in index
    ]


# ── 复制 wiki 页面到 pages/ ──────────────────────────────────────────────────
def copy_pages():
    count = 0
    for cat, (_, wiki_subdir) in CATEGORY_DIRS.items():
        if not wiki_subdir.exists():
            continue
        out_dir = PAGES_DIR / cat
        out_dir.mkdir(parents=True, exist_ok=True)
        
        for md_file in wiki_subdir.glob("*.md"):
            dst = out_dir / md_file.name
            shutil.copy2(md_file, dst)
            count += 1
    
    print(f"  复制了 {count} 个 wiki 页面")


# ── 复制原文到 raw/ ───────────────────────────────────────────────────────────
def copy_raw():
    count = 0
    for sub in ["letters", "interviews"]:
        src_dir = RAW_DIR / sub
        if not src_dir.exists():
            continue
        dst_dir = RAW_OUT_DIR / sub
        
        if sub == "letters":
            # 信件有子目录
            for subsub in ["berkshire", "partnership", "special"]:
                src_sub = src_dir / subsub
                if not src_sub.exists():
                    continue
                dst_sub = dst_dir / subsub
                dst_sub.mkdir(parents=True, exist_ok=True)
                for f in src_sub.glob("*.md"):
                    shutil.copy2(f, dst_sub / f.name)
                    count += 1
        else:
            dst_dir.mkdir(parents=True, exist_ok=True)
            for f in src_dir.glob("*.md"):
                shutil.copy2(f, dst_dir / f.name)
                count += 1
    
    print(f"  复制了 {count} 个原文文件")


# ── 主函数 ────────────────────────────────────────────────────────────────────
def main():
    print("构建前端数据...")
    print(f"  wiki/ 目录: {WIKI_DIR}")
    print(f"  输出目录: {DATA_DIR}")
    
    # 创建输出目录
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PAGES_DIR.mkdir(parents=True, exist_ok=True)
    RAW_OUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 生成 wiki-index
    index = build_wiki_index()
    (DATA_DIR / "wiki-index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    
    # 生成 graph
    graph = build_graph(index)
    (DATA_DIR / "graph.json").write_text(
        json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    
    # 生成 search-index
    search_idx = build_search_index(index)
    (DATA_DIR / "search-index.json").write_text(
        json.dumps(search_idx, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    
    # 复制页面
    copy_pages()
    
    # 复制原文
    copy_raw()
    
    print(f"\n构建完成！")
    print(f"  wiki-index.json: {len(index)} 条")
    print(f"  graph.json: {len(graph['nodes'])} 节点 / {len(graph['edges'])} 边")
    print(f"  search-index.json: {len(search_idx)} 条")


if __name__ == "__main__":
    main()
