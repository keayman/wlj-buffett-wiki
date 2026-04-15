// api/verify.js — Vercel Serverless: 密码验证
import crypto from 'crypto'

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' })
  }

  try {
    // 解析 body
    let password = ''
    if (typeof req.body === 'object' && req.body !== null) {
      password = req.body.password || ''
    } else if (typeof req.body === 'string') {
      try { password = JSON.parse(req.body).password || '' } catch { password = '' }
    }

    const expectedPassword = process.env.ACCESS_PASSWORD || process.env.ACCESS_PASSWORD || .REDACTED_FALLBACK.

    if (password === expectedPassword) {
      const salt = crypto.randomBytes(16).toString('hex')
      const token = crypto.createHash('sha256').update(password + salt).digest('hex')
      return res.json({ ok: true, token })
    }

    return res.json({ ok: false, debug: { received: password ? '***' : 'empty', envSet: !!process.env.ACCESS_PASSWORD } })
  } catch (e) {
    return res.status(500).json({ ok: false, error: 'server error' })
  }
}
