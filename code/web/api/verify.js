// api/verify.js — Vercel Serverless: 密码验证
import crypto from 'crypto'

// Vercel Serverless 无状态，用密码 hash 作为 token（简化方案）
export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' })
  }

  const { password } = req.body || {}
  const expectedPassword = process.env.ACCESS_PASSWORD || process.env.ACCESS_PASSWORD || .REDACTED_FALLBACK.

  if (password === expectedPassword) {
    // 生成 token = hash(password + 随机盐)
    const salt = crypto.randomBytes(16).toString('hex')
    const token = crypto.createHash('sha256').update(password + salt).digest('hex')
    return res.json({ ok: true, token })
  }

  return res.json({ ok: false })
}
