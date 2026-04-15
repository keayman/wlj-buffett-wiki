<template>
  <div>
    <!-- 密码验证 -->
    <div v-if="!authed" class="chat-password-overlay">
      <div class="chat-password-card">
        <div class="chat-password-icon">🔐</div>
        <div class="chat-password-title">访问密码</div>
        <input
          v-model="pw"
          type="password"
          class="chat-pw-input"
          placeholder="请输入密码"
          @keydown.enter="checkPw"
        />
        <div v-if="pwError" class="chat-pw-error">{{ pwError }}</div>
        <button class="btn btn-blue" style="width:100%" @click="checkPw">确认进入</button>
      </div>
    </div>

    <!-- 对话界面 -->
    <template v-else>
      <div class="hero">
        <h1 class="hero-title">🧑‍💼 AI 巴菲特</h1>
        <div class="hero-subtitle">基于知识库的巴菲特投资风格对话 · 知识来源于历年股东信与访谈</div>
      </div>

      <div class="chat-layout">
        <!-- 消息列表 -->
        <div class="chat-messages" ref="chatBox">
          <!-- 空态 -->
          <div v-if="!messages.length" class="chat-empty">
            <div class="chat-empty-icon">🎩</div>
            <div class="chat-empty-title">问我关于投资、人生和商业的问题</div>
            <div style="font-size:13px;color:var(--text-tertiary)">我会以巴菲特的视角和知识库为基础回答</div>
            <div class="chat-examples">
              <div v-for="e in examples" :key="e" class="chat-example" @click="sendExample(e)">{{ e }}</div>
            </div>
          </div>

          <!-- 消息 -->
          <div
            v-for="(msg, i) in messages"
            :key="i"
            class="chat-msg"
            :class="msg.role === 'user' ? 'chat-msg-user' : 'chat-msg-ai'"
          >
            <div class="chat-avatar">{{ msg.role === 'user' ? '👤' : '🎩' }}</div>
            <div>
              <div
                class="chat-bubble"
                :class="msg.role === 'user' ? 'chat-bubble-user' : 'chat-bubble-ai'"
              >
                <template v-if="msg.role === 'assistant'">
                  <div class="prose" v-html="renderMd(msg.content)"></div>
                </template>
                <template v-else>{{ msg.content }}</template>
              </div>
              <!-- 来源标签 -->
              <div v-if="msg.sources?.length" class="chat-sources">
                <span v-for="s in msg.sources" :key="s" class="chat-source-tag">📄 {{ s }}</span>
              </div>
            </div>
          </div>

          <!-- 思考中 -->
          <div v-if="thinking" class="chat-msg chat-msg-ai">
            <div class="chat-avatar">🎩</div>
            <div class="chat-bubble chat-bubble-ai" style="color:var(--text-tertiary);font-style:italic">
              思考中...
            </div>
          </div>
        </div>

        <!-- 输入区 -->
        <div class="chat-input-area">
          <textarea
            v-model="input"
            class="chat-input"
            rows="1"
            placeholder="向巴菲特提问..."
            @keydown.enter.prevent="sendMsg"
            @input="autoResize"
            ref="inputEl"
          ></textarea>
          <button
            class="btn btn-blue"
            :disabled="!input.trim() || thinking"
            @click="sendMsg"
          >发送</button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import MarkdownIt from 'markdown-it'

const md = new MarkdownIt({ html: false, linkify: true, typographer: true })

// 状态
const authed = ref(false)
const pw = ref('')
const pwError = ref('')
const input = ref('')
const messages = ref([])
const thinking = ref(false)
const chatBox = ref(null)
const inputEl = ref(null)
const sessionToken = ref('')  // session token，替代明文密码

// 历史记录（给 API 用）
const history = ref([])

const examples = [
  '护城河是什么意思？',
  '你如何评估一家企业的内在价值？',
  '对年轻人最重要的投资建议是什么？',
  '为什么长期持有比频繁交易更好？',
  '如何看待市场波动？',
]

function renderMd(text) {
  return md.render(text || '')
}

async function checkPw() {
  if (!pw.value.trim()) { pwError.value = '请输入密码'; return }
  
  try {
    const res = await fetch('/api/verify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password: pw.value }),
    })
    if (res.ok) {
      const data = await res.json()
      if (data.ok) {
        authed.value = true
        pwError.value = ''
        sessionToken.value = data.token  // 保存 session token
        pw.value = ''  // 清除明文密码
      } else {
        pwError.value = '密码错误，请重试'
      }
    } else {
      pwError.value = '验证失败，请稍后再试'
    }
  } catch (e) {
    pwError.value = '网络错误，请检查服务是否启动'
  }
}

function sendExample(e) {
  input.value = e
  sendMsg()
}

async function sendMsg() {
  const text = input.value.trim()
  if (!text || thinking.value) return
  
  input.value = ''
  
  // 用户消息
  messages.value.push({ role: 'user', content: text })
  history.value.push({ role: 'user', content: text })
  
  // AI 消息占位
  const aiIdx = messages.value.length
  messages.value.push({ role: 'assistant', content: '', sources: [] })
  thinking.value = true
  
  scrollToBottom()
  
  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Session-Token': sessionToken.value,  // 用 session token 代替明文密码
      },
      body: JSON.stringify({
        question: text,
        history: history.value.slice(-10),
      }),
    })
    
    if (!res.ok) {
      if (res.status === 401) {
        // session 过期，重新要求密码
        authed.value = false
        sessionToken.value = ''
        messages.value[aiIdx] = { ...messages.value[aiIdx], content: '会话已过期，请重新输入密码。' }
      }
      throw new Error(`HTTP ${res.status}`)
    }
    
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let fullText = ''
    
    thinking.value = false
    
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      
      const chunk = decoder.decode(value)
      const lines = chunk.split('\n')
      
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        try {
          const data = JSON.parse(line.slice(6))
          if (data.text) {
            fullText += data.text
            messages.value[aiIdx] = { ...messages.value[aiIdx], content: fullText }
            scrollToBottom()
          }
          if (data.done) {
            messages.value[aiIdx] = { ...messages.value[aiIdx], sources: data.sources || [] }
          }
        } catch (e) {}
      }
    }
    
    // 记录到历史
    history.value.push({ role: 'assistant', content: fullText })
    
  } catch (e) {
    thinking.value = false
    messages.value[aiIdx] = { ...messages.value[aiIdx], content: `抱歉，发生了错误：${e.message}` }
  }
  
  scrollToBottom()
}

function scrollToBottom() {
  nextTick(() => {
    if (chatBox.value) {
      chatBox.value.scrollTop = chatBox.value.scrollHeight
    }
  })
}

function autoResize(e) {
  const el = e.target
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 120) + 'px'
}
</script>
