// api/health.js — Vercel Serverless: 健康检查
import { readFileSync, existsSync } from 'fs'
import { join } from 'path'

export default async function handler(req, res) {
  try {
    const idxPath = join(process.cwd(), 'public', 'data', 'wiki-index.json')
    let pages = 0
    if (existsSync(idxPath)) {
      const data = JSON.parse(readFileSync(idxPath, 'utf-8'))
      pages = Array.isArray(data) ? data.length : 0
    }
    res.json({ ok: true, pages })
  } catch (e) {
    res.json({ ok: true, pages: 0 })
  }
}
