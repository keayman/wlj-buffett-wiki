// kb.js — 知识库加载与检索（Vercel Serverless 共享模块）
import { readFileSync, existsSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
// Vercel Serverless 中数据文件在项目根目录
const DATA_DIR = existsSync(join(process.cwd(), 'data'))
  ? join(process.cwd(), 'data')
  : join(__dirname, '..', 'public', 'data')
const PAGES_DIR = join(DATA_DIR, 'pages')

let wikiIndex = []
let graphData = null
let neighbors = {}
let indexByTitle = {}
let loaded = false

function loadKnowledgeBase() {
  if (loaded) return
  try {
    const idxPath = join(DATA_DIR, 'wiki-index.json')
    if (existsSync(idxPath)) {
      wikiIndex = JSON.parse(readFileSync(idxPath, 'utf-8'))
      wikiIndex.forEach(p => { indexByTitle[p.title] = p })
    }
    const graphPath = join(DATA_DIR, 'graph.json')
    if (existsSync(graphPath)) {
      graphData = JSON.parse(readFileSync(graphPath, 'utf-8'))
      neighbors = {}
      graphData.edges.forEach(e => {
        if (!neighbors[e.source]) neighbors[e.source] = []
        if (!neighbors[e.target]) neighbors[e.target] = []
        neighbors[e.source].push(e.target)
        neighbors[e.target].push(e.source)
      })
    }
    loaded = true
  } catch (e) {
    console.error('加载知识库失败:', e.message)
  }
}

function ngrams(text, n = 3) {
  const grams = new Set()
  const normalized = text.replace(/\r\n/g, '\n')
  for (let k = 2; k <= Math.min(4, normalized.length); k++) {
    for (let i = 0; i <= normalized.length - k; i++) {
      grams.add(normalized.slice(i, i + k))
    }
  }
  normalized.split(/\s+/).forEach(w => { if (w) grams.add(w) })
  return grams
}

function scoreEntry(entry, question, qNgrams) {
  let score = 0
  const title = entry.title || ''
  const summary = entry.summary || ''
  const links = entry.links || []
  const titleLower = title.toLowerCase()
  const qLower = question.toLowerCase()
  if (title && qLower.includes(titleLower)) score += 50
  if (title && titleLower.includes(qLower)) score += 40
  qNgrams.forEach(g => {
    if (titleLower.includes(g.toLowerCase())) score += 8
    if (summary.toLowerCase().includes(g.toLowerCase())) score += 3
  })
  links.forEach(l => {
    if (qLower.includes(l.toLowerCase()) || l.toLowerCase().includes(qLower.slice(0, 4))) {
      score += 6
    }
  })
  return score
}

function retrieve(question) {
  loadKnowledgeBase()
  const qNgrams = ngrams(question)
  const scored = wikiIndex
    .map(entry => ({ entry, score: scoreEntry(entry, question, qNgrams) }))
    .filter(x => x.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 4)
  const result = scored.map(x => x.entry)
  const resultTitles = new Set(result.map(e => e.title))
  if (graphData) {
    const candidates = []
    result.forEach(entry => {
      const nbrs = neighbors[entry.title] || []
      nbrs.forEach(nbr => {
        if (resultTitles.has(nbr)) return
        const nbrEntry = indexByTitle[nbr]
        if (!nbrEntry) return
        const nbrScore = scoreEntry(nbrEntry, question, qNgrams)
        if (nbrScore > 0) candidates.push({ entry: nbrEntry, score: nbrScore })
      })
    })
    candidates.sort((a, b) => b.score - a.score).slice(0, 2).forEach(c => {
      if (!resultTitles.has(c.entry.title)) {
        result.push(c.entry)
        resultTitles.add(c.entry.title)
      }
    })
  }
  return result
}

function loadPageContent(entry) {
  try {
    const cat = entry.category || 'concepts'
    const slug = entry.slug || entry.title
    const filePath = join(PAGES_DIR, cat, `${slug}.md`)
    if (existsSync(filePath)) {
      return readFileSync(filePath, 'utf-8').slice(0, 3000)
    }
    return entry.summary || entry.title
  } catch (e) {
    return entry.summary || entry.title
  }
}

function buildSystemPrompt(contextPages) {
  const context = contextPages
    .map(entry => {
      const content = loadPageContent(entry)
      return `### ${entry.title}\n${content}`
    })
    .join('\n\n---\n\n')
  return `你是沃伦·巴菲特。根据以下知识库内容，以巴菲特的第一人称风格回答问题。

要求：
1. 以第一人称（"我"）回答，模拟巴菲特的语气：直接、坦率、用简单例子说明复杂道理
2. 引用知识库中的具体案例、数据和原话
3. 偶尔用幽默感，就像巴菲特在股东大会上的讲话风格
4. 如果问题超出知识库范围，坦率说明但仍尝试给出有价值的见解
5. 回答结构清晰，适当分段

知识库内容：
---
${context}
---`
}

export { loadKnowledgeBase, retrieve, buildSystemPrompt, wikiIndex, graphData }
