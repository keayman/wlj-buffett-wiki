#!/usr/bin/env python3
"""
fix_headings2.py — 第二轮修复：基于已知标题列表精确匹配，在标题前后加空行。

已知的常见标题（来自原始数据分析）：
  概念类：概念解析、定义与起源、核心要义、实践应用、常见误区、相关概念、思想演变、典型案例公司
  公司类：公司简介、投资故事、巴菲特评价精选、投资启示、相关公司、相关概念
  人物类：人物简介、主要贡献、投资哲学、巴菲特评价、相关人物
  通用：原文金句、核心要点、详细摘要、提到的概念、提到的公司、提到的人物
"""

import re
import sys
from pathlib import Path
import argparse

BASE_DIR = Path(__file__).parent.parent
WIKI_DIR = BASE_DIR / "wiki"

# 已知标题列表（精确匹配整行）
KNOWN_HEADINGS = [
    "概念解析", "定义与起源", "核心要义", "实践应用", "常见误区",
    "相关概念", "思想演变", "典型案例公司", "萌芽期", "成熟期", "巩固期",
    "公司简介", "投资故事", "巴菲特评价精选", "投资启示", "相关公司",
    "人物简介", "主要贡献", "投资哲学", "巴菲特评价", "相关人物",
    "原文金句", "核心要点", "详细摘要", "提到的概念", "提到的公司", "提到的人物",
    "背景与意义", "主要内容", "历史背景", "误区分析",
]

# 将已知标题转为集合（用于快速查找）
HEADING_SET = set(KNOWN_HEADINGS)


def fix_headings2(text: str) -> str:
    lines = text.split("\n")
    result = []
    in_frontmatter = False
    frontmatter_done = False
    in_code = False
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # YAML frontmatter
        if i == 0 and stripped == "---":
            in_frontmatter = True
            result.append(line)
            continue
        
        if in_frontmatter:
            result.append(line)
            if stripped == "---" and i > 0:
                in_frontmatter = False
                frontmatter_done = True
            continue
        
        # 代码块
        if stripped.startswith("```"):
            in_code = not in_code
            result.append(line)
            continue
        
        if in_code:
            result.append(line)
            continue
        
        # 检查是否是已知标题（且没有 ## 前缀）
        if (frontmatter_done 
                and stripped in HEADING_SET
                and not line.startswith("#")):
            
            # 确保前面有空行
            if result and result[-1].strip():
                result.append("")
            
            result.append(f"## {stripped}")
            
            # 确保后面有空行（向前看）
            if i + 1 < len(lines) and lines[i + 1].strip():
                result.append("")
        else:
            result.append(line)
    
    return "\n".join(result)


def process_file(path: Path, dry_run: bool = False) -> bool:
    text = path.read_text(encoding="utf-8")
    fixed = fix_headings2(text)
    
    if fixed == text:
        return False
    
    if dry_run:
        print(f"  {path.name}: 有修改")
    else:
        path.write_text(fixed, encoding="utf-8")
    
    return True


def main():
    parser = argparse.ArgumentParser(description="修复 wiki 中缺失的 ## 标题标记（第二轮，已知标题列表）")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--dir", help="指定子目录", default=None)
    args = parser.parse_args()
    
    target_dir = (WIKI_DIR / args.dir) if args.dir else WIKI_DIR
    files = list(target_dir.rglob("*.md"))
    changed = 0
    
    for f in sorted(files):
        if f.name in ("SCHEMA.md", "README.md", "index.md", "log.md"):
            continue
        if process_file(f, args.dry_run):
            changed += 1
            if not args.dry_run:
                print(f"✓ {f.relative_to(BASE_DIR)}")
    
    print(f"\n{'[预览]' if args.dry_run else '完成'} 修改了 {changed}/{len(files)} 个文件")


if __name__ == "__main__":
    main()
