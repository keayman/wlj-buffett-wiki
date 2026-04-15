// api/verify.js — Vercel Serverless: 密码验证
import crypto from 'crypto'

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' })
  }

  try {
    let password = ''
    if (typeof req.body === 'object' && req.body !== null) {
      password = String(req.body.password || '').trim()
    } else if (typeof req.body === 'string') {
      try { password = String(JSON.parse(req.body).password || '').trim() } catch { password = '' }
    }

    const expectedPassword = String(process.env.ACCESS_PASSWORD || process.env.ACCESS_PASSWORD || .REDACTED_FALLBACK.).trim()

    if (password === expectedPassword) {
      const salt = crypto.randomBytes(16).toString('hex')
      const token = crypto.createHash('sha256').update(password + salt).digest('hex')
      return res.json({ ok: true, token })
    }

    // Debug only in non-production
    if (process.env.NODE_ENV !== 'production') {
      return res.json({ ok: false, debug: { receivedLen: password.length, expectedLen: expectedPassword.length, receivedCharCodes: [...password].map(c => c.charCodeAt(0)), expectedCharCodes: [...expectedPassword].map(c => c.charCodeAt(0)) } })
    }

    return res.json({ ok: false })
  } catch (e) {
    return res.status(500).json({ ok: false, error: 'server error' })
  }
}
