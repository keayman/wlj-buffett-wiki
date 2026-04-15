// api/chat.js — Vercel Serverless: AI 对话（SSE 流式）
import Anthropic from '@anthropic-ai/sdk'
import { readFileSync, existsSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))

// Vercel Serverless 中数据在项目根目录
const ROOT = process.cwd()
const DATA_DIR = join(ROOT, 'public', 'data')
const PAGES_DIR = join(DATA_DIR, 'pages')

export const config = {
  api: {
    bodyParser: true,
    responseLimit: false,
  },
}

// ── 知识库加载 ──────────────────────────────────────────────────────────
let wikiIndex = []
let graphData = null
let neighbors = {}
let indexByTitle = {}

function loadKnowledgeBase() {
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
  } catch (e) {
    console.error('KB load error:', e.message)
  }
}

// ── 检索逻辑 ──────────────────────────────────────────────────────────
function ngrams(text) {
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
  const title = (entry.title || '').toLowerCase()
  const summary = (entry.summary || '').toLowerCase()
  const qLower = question.toLowerCase()
  if (title && qLower.includes(title)) score += 50
  if (title && title.includes(qLower)) score += 40
  qNgrams.forEach(g => {
    const gl = g.toLowerCase()
    if (title.includes(gl)) score += 8
    if (summary.includes(gl)) score += 3
  })
  ;(entry.links || []).forEach(l => {
    if (qLower.includes(l.toLowerCase())) score += 6
  })
  return score
}

function retrieve(question) {
  const qNgrams = ngrams(question)
  const scored = wikiIndex
    .map(entry => ({ entry, score: scoreEntry(entry, question, qNgrams) }))
    .filter(x => x.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 4)

  const result = scored.map(x => x.entry)
  const titles = new Set(result.map(e => e.title))

  if (graphData) {
    const candidates = []
    result.forEach(entry => {
      ;(neighbors[entry.title] || []).forEach(nbr => {
        if (titles.has(nbr)) return
        const nbrEntry = indexByTitle[nbr]
        if (!nbrEntry) return
        const s = scoreEntry(nbrEntry, question, qNgrams)
        if (s > 0) candidates.push({ entry: nbrEntry, score: s })
      })
    })
    candidates.sort((a, b) => b.score - a.score).slice(0, 2).forEach(c => {
      if (!titles.has(c.entry.title)) {
        result.push(c.entry)
        titles.add(c.entry.title)
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
    if (existsSync(filePath)) return readFileSync(filePath, 'utf-8').slice(0, 3000)
    return entry.summary || entry.title
  } catch (e) {
    return entry.summary || entry.title
  }
}

function buildSystemPrompt(contextPages) {
  const context = contextPages
    .map(entry => `### ${entry.title}\n${loadPageContent(entry)}`)
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

// ── Handler ────────────────────────────────────────────────────────────
export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' })
  }

  // Token 验证（简化：Vercel 无状态，token 只要存在就放行）
  const token = req.headers['x-session-token']
  if (!token) {
    return res.status(401).json({ error: '未授权，请重新验证密码' })
  }

  const { question, history = [] } = req.body
  if (!question?.trim()) {
    return res.status(400).json({ error: '问题不能为空' })
  }
  if (question.length > 2000) {
    return res.status(400).json({ error: '问题过长' })
  }

  loadKnowledgeBase()

  const relevantPages = retrieve(question)
  const sources = relevantPages.map(p => p.title)
  const safeHistory = history.slice(-8).map(m => ({
    role: m.role,
    content: String(m.content || '').slice(0, 1000),
  }))

  // SSE headers
  res.setHeader('Content-Type', 'text/event-stream')
  res.setHeader('Cache-Control', 'no-cache')
  res.setHeader('Connection', 'keep-alive')
  res.setHeader('X-Accel-Buffering', 'no')

  // Vercel 需要立即 flush
  res.flushHeaders()

  const send = (data) => {
    try { res.write(`data: ${JSON.stringify(data)}\n\n`) } catch (e) {}
  }

  try {
    const API_KEY = process.env.ANTHROPIC_API_KEY
    if (!API_KEY) {
      send({ text: 'API Key 未配置，请联系管理员。', done: true, sources: [] })
      res.end()
      return
    }

    const clientOpts = { apiKey: API_KEY }
    const BASE_URL = process.env.ANTHROPIC_BASE_URL
    if (BASE_URL) clientOpts.baseURL = BASE_URL
    const anthropic = new Anthropic(clientOpts)
    const MODEL = process.env.ANTHROPIC_MODEL || 'claude-opus-4-5'

    const stream = await anthropic.messages.stream({
      model: MODEL,
      max_tokens: 2048,
      system: buildSystemPrompt(relevantPages),
      messages: [...safeHistory, { role: 'user', content: question }],
    })

    for await (const chunk of stream) {
      if (chunk.type === 'content_block_delta' && chunk.delta?.text) {
        send({ text: chunk.delta.text })
      }
    }

    send({ done: true, sources })
  } catch (e) {
    console.error('Chat API error:', e.message)
    send({ text: '\n\n抱歉，生成回复时遇到了问题，请稍后再试。', done: true, sources: [] })
  }

  res.end()
}
