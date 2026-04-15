# Wiki Schema — WLJ-巴菲特知识库

## 页面类型

本知识库包含以下 6 种页面类型：

| 类型 | 目录 | 说明 |
|------|------|------|
| `concept` | wiki/concepts/ | 巴菲特核心投资概念（49个）|
| `company` | wiki/companies/ | 巴菲特投资过或分析过的公司（61个）|
| `person` | wiki/people/ | 巴菲特提及的关键人物（7个）|
| `letter-summary` | wiki/letters/ | 股东信/合伙人信摘要（98篇）|
| `interview-summary` | wiki/interviews/ | 访谈与演讲摘要（26篇）|
| `insight` | wiki/insights/ | 跨文档交叉分析（后续生成）|

## YAML Frontmatter 规范

所有页面**必须**包含以下 frontmatter：

```yaml
---
title: "页面标题"
type: letter-summary | interview-summary | concept | company | person | insight | index
date: YYYY-MM-DD
source: "原始文件相对路径（如 raw/letters/berkshire/1988 巴菲特致股东信.md）"
tags: [标签1, 标签2]
related: []
created: YYYY-MM-DD
updated: YYYY-MM-DD
---
```

## 双向链接规范

- 所有实体名称必须使用 `[[实体名]]` 格式关联
- 链接目标必须是 wiki/ 中已存在的页面
- 避免自链接（页面不链接自身）
- 常见实体：概念名、公司名、人物名、信件年份引用

## 摘要页结构（letter-summary / interview-summary）

```markdown
# 标题

## 核心要点
（3-5个最重要的观点，每点一行）

## 详细摘要
（原文20-30%长度的结构化摘要）

## 提到的概念
（使用 [[链接]] 格式）

## 提到的公司
（使用 [[链接]] 格式）

## 提到的人物
（使用 [[链接]] 格式）

## 原文金句
（最精彩的 3-5 句原话，带引号）
```

## 概念/公司/人物页结构

```markdown
# 标题

## 概念解析 / 公司简介 / 人物简介

## 核心要义 / 投资故事 / 主要贡献

## 实践应用 / 巴菲特评价精选

## 相关概念 / 相关公司 / 相关人物
（使用 [[链接]] 格式）
```

## 链接约定

- `[[护城河]]` → wiki/concepts/护城河.md
- `[[可口可乐]]` → wiki/companies/可口可乐.md
- `[[芒格]]` → wiki/people/芒格.md
- `[[1988 巴菲特致股东信]]` → wiki/letters/1988-巴菲特致股东信.md
