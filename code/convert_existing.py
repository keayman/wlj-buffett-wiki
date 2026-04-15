#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
convert_existing.py — 将 raw/ 中的概念/公司/人物 Markdown 批量转换为 wiki 格式。

功能：
  - 去掉 "> **Source**"、"> **Type**" 行和所有 "---" 分隔线
  - 添加 YAML frontmatter
  - 扫描正文，替换已知实体名为 [[双向链接]]
  - 支持 --dry-run 和 --category 参数

用法：
  python convert_existing.py                    # 转换全部
  python convert_existing.py --dry-run          # 预览模式
  python convert_existing.py --category concepts # 只转换概念
"""

import os
import re
import argparse
from datetime import date
from pathlib import Path

# ── 路径配置 ──────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent
RAW_DIR = BASE_DIR / "raw"
WIKI_DIR = BASE_DIR / "wiki"

CATEGORY_MAP = {
    "concepts": ("concept", "concepts"),
    "companies": ("company", "companies"),
    "people": ("person", "people"),
}

# ── 实体名称收集 ──────────────────────────────────────────────────────────────
def collect_entities():
    """收集所有已知实体名称，用于双向链接替换"""
    entities = {}  # name -> (category, type)
    
    for cat in ["concepts", "companies", "people"]:
        dir_path = RAW_DIR / cat
        if not dir_path.exists():
            continue
        for f in dir_path.glob("*.md"):
            name = f.stem
            entities[name] = cat
    
    return entities


# ── 清理原有头部 ──────────────────────────────────────────────────────────────
def strip_existing_header(text: str) -> str:
    """
    逐行处理，删除：
      - "> **Source**..." 行
      - "> **Type**..." 行
      - "---" 独立行（分隔线）
    """
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("> **Source**") or stripped.startswith("> **Type**"):
            continue
        if stripped == "---":
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


# ── 插入双向链接 ──────────────────────────────────────────────────────────────
def insert_wikilinks(text: str, entities: dict, self_name: str) -> str:
    """
    扫描正文，将已知实体名替换为 [[实体名]] 双向链接。
    
    规则：
    - 按名称长度降序匹配（避免短名称覆盖长名称）
    - 避免自链接
    - 跳过标题行（# 开头）和代码块（``` 内）
    - 不跟踪 frontmatter 状态（调用此函数时文本已不含 frontmatter）
    """
    # 按名称长度降序排列
    sorted_entities = sorted(entities.keys(), key=len, reverse=True)
    
    lines = text.split("\n")
    in_code_block = False
    result_lines = []
    
    for line in lines:
        # 检测代码块
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            result_lines.append(line)
            continue
        
        if in_code_block:
            result_lines.append(line)
            continue
        
        # 跳过标题行
        if re.match(r'^#{1,6}\s', line):
            result_lines.append(line)
            continue
        
        # 对每个实体进行替换
        for entity in sorted_entities:
            if entity == self_name:
                continue  # 避免自链接
            
            # 只替换尚未被 [[ ]] 包裹的实体名
            # 先检查是否已有 [[entity]] 形式，若有跳过
            if f'[[{entity}]]' in line:
                continue
            
            escaped = re.escape(entity)
            # 简单替换：找到实体名，且前后不是 [ 或 ]
            pattern = r'(?<!\[)' + escaped + r'(?!\])'
            replacement = f'[[{entity}]]'
            line = re.sub(pattern, replacement, line)
        
        result_lines.append(line)
    
    return "\n".join(result_lines)


# ── 生成 frontmatter ──────────────────────────────────────────────────────────
def generate_frontmatter(title: str, page_type: str, source_path: str, tags: list) -> str:
    today = date.today().isoformat()
    tags_str = ", ".join(f'"{t}"' for t in tags)
    return f"""---
title: "{title}"
type: {page_type}
date: {today}
source: "{source_path}"
tags: [{tags_str}]
related: []
created: {today}
updated: {today}
---
"""


# ── 处理单个文件 ──────────────────────────────────────────────────────────────
def convert_file(src_path: Path, dst_path: Path, page_type: str, 
                 entities: dict, dry_run: bool = False):
    text = src_path.read_text(encoding="utf-8")
    name = src_path.stem
    
    # 1. 去掉旧的 Source/Type 行和分隔线
    text = strip_existing_header(text)
    
    # 2. 处理正文：去掉首行的重复标题（如果和文件名一样）
    lines = text.strip().split("\n")
    # 去掉开头的空行
    while lines and not lines[0].strip():
        lines.pop(0)
    
    # 如果第一行是 # 标题，提取标题；否则保留
    if lines and lines[0].startswith("# "):
        title = lines[0][2:].strip()
        # 去掉第一行后的空行
        body_lines = lines[1:]
        while body_lines and not body_lines[0].strip():
            body_lines.pop(0)
        body = "\n".join(body_lines)
    else:
        title = name
        body = "\n".join(lines)
    
    # 3. 插入双向链接
    body = insert_wikilinks(body, entities, name)
    
    # 4. 生成 frontmatter
    source_path = f"raw/{page_type}s/{src_path.name}" if page_type != "person" else f"raw/people/{src_path.name}"
    
    # 确定 source 路径
    cat_to_raw = {"concept": "concepts", "company": "companies", "person": "people"}
    raw_sub = cat_to_raw.get(page_type, page_type + "s")
    source_rel = f"raw/{raw_sub}/{src_path.name}"
    
    tags = [page_type]
    if page_type == "concept":
        tags.append("投资概念")
    elif page_type == "company":
        tags.append("投资公司")
    elif page_type == "person":
        tags.append("关键人物")
    
    frontmatter = generate_frontmatter(title, page_type, source_rel, tags)
    
    # 5. 组合最终内容
    final = frontmatter + f"# {title}\n\n" + body.strip() + "\n"
    
    if dry_run:
        print(f"[DRY-RUN] {src_path.name} → {dst_path}")
        print(f"  标题: {title}")
        print(f"  类型: {page_type}")
        print(f"  字数: {len(final)}")
        return
    
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    dst_path.write_text(final, encoding="utf-8")
    print(f"OK {src_path.name} -> {dst_path.relative_to(BASE_DIR)}")


# ── 主函数 ────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="转换 raw/ 中的概念/公司/人物到 wiki 格式")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不写文件")
    parser.add_argument("--category", choices=["concepts", "companies", "people"],
                        help="只转换指定分类")
    args = parser.parse_args()
    
    # 收集所有实体
    entities = collect_entities()
    print(f"收集到 {len(entities)} 个实体名称")
    
    # 确定要处理的分类
    categories = [args.category] if args.category else list(CATEGORY_MAP.keys())
    
    total = 0
    for cat in categories:
        page_type, wiki_sub = CATEGORY_MAP[cat]
        src_dir = RAW_DIR / cat
        dst_dir = WIKI_DIR / wiki_sub
        
        if not src_dir.exists():
            print(f"警告：{src_dir} 不存在，跳过")
            continue
        
        files = sorted(src_dir.glob("*.md"))
        print(f"\n处理 {cat}（{len(files)} 个文件）...")
        
        for src_path in files:
            # 文件名转换：保留原始名称（中文友好）
            dst_path = dst_dir / src_path.name
            try:
                convert_file(src_path, dst_path, page_type, entities, args.dry_run)
                total += 1
            except Exception as e:
                print(f"  FAIL {src_path.name}: {e}")
    
    print(f"\n{'[预览]' if args.dry_run else '完成'} 处理了 {total} 个文件")


if __name__ == "__main__":
    main()
