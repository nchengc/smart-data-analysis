// Phase 3 API 层：把后端 /api/* 全部封装成 Promise/SSE

import type { ChartSpec, ChatMessage, Session } from './mockData'

const BASE = '/api'

async function jget<T>(path: string): Promise<T> {
  const resp = await fetch(BASE + path)
  if (!resp.ok) {
    const txt = await resp.text().catch(() => '')
    throw new Error(`GET ${path} 失败 ${resp.status}: ${txt}`)
  }
  return resp.json()
}

async function jpost<T>(path: string, body?: unknown): Promise<T> {
  const resp = await fetch(BASE + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : '{}',
  })
  if (!resp.ok) {
    const txt = await resp.text().catch(() => '')
    throw new Error(`POST ${path} 失败 ${resp.status}: ${txt}`)
  }
  return resp.json()
}

async function jpatch<T>(path: string, body: unknown): Promise<T> {
  const resp = await fetch(BASE + path, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!resp.ok) throw new Error(`PATCH ${path} 失败 ${resp.status}`)
  return resp.json()
}

async function jdel<T = unknown>(path: string): Promise<T> {
  const resp = await fetch(BASE + path, { method: 'DELETE' })
  if (!resp.ok) throw new Error(`DELETE ${path} 失败 ${resp.status}`)
  return resp.json()
}

// ---------- Sessions ----------
export const listSessions = (): Promise<Session[]> => jget('/sessions')
export const createSession = (title?: string): Promise<Session> =>
  jpost('/sessions', { title: title ?? '新会话' })
export const renameSession = (id: string, title: string): Promise<Session> =>
  jpatch(`/sessions/${id}`, { title })
export const deleteSession = (id: string): Promise<{ deleted: boolean }> =>
  jdel(`/sessions/${id}`)
export const listMessages = (id: string, limit = 50): Promise<ChatMessage[]> =>
  jget(`/sessions/${id}/messages?limit=${limit}`)

// ---------- Schema ----------
export interface SchemaInfo {
  tables: string[]
  schema_text: string
  row_counts: Record<string, number>
}
export const getSchema = (): Promise<SchemaInfo> => jget('/schema')

// ---------- Chat (SSE) ----------
export type StreamEvent =
  | { type: 'phase'; payload: string }
  | { type: 'sql'; payload: string }
  | { type: 'data'; payload: { rows: any[]; row_count: number } }
  | { type: 'chart'; payload: ChartSpec }
  | { type: 'summary'; payload: { summary: string } }
  | { type: 'error'; payload: string }
  | { type: 'done'; payload: { elapsed_ms: number; rounds: number } | null }

export interface StreamHandlers {
  onPhase?: (msg: string) => void
  onSql?: (sql: string) => void
  onData?: (rows: any[], row_count: number) => void
  onChart?: (chart: ChartSpec) => void
  onSummary?: (summary: string) => void
  onError?: (msg: string) => void
  onDone?: (meta: { elapsed_ms: number; rounds: number } | null) => void
  onAbort?: () => void
}

/** POST + 流式读取 SSE */
export async function streamChat(
  sessionId: string,
  question: string,
  handlers: StreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const resp = await fetch(BASE + '/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, question }),
    signal,
  })
  if (!resp.ok || !resp.body) {
    throw new Error(`SSE 失败：${resp.status}`)
  }
  const reader = resp.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    // 解析 SSE 帧 (event: ... \n data: ... \n\n)
    let sep: number
    while ((sep = buffer.indexOf('\n\n')) >= 0) {
      const frame = buffer.slice(0, sep)
      buffer = buffer.slice(sep + 2)
      const evLine = frame.split('\n').find((l) => l.startsWith('event:'))
      const dataLine = frame.split('\n').find((l) => l.startsWith('data:'))
      if (!dataLine) continue
      const dataStr = dataLine.replace(/^data:\s*/, '')
      let payload: StreamEvent | null = null
      try {
        payload = JSON.parse(dataStr)
      } catch {
        continue
      }
      if (!payload) continue
      switch (payload.type) {
        case 'phase':
          handlers.onPhase?.(payload.payload as string)
          break
        case 'sql':
          handlers.onSql?.(payload.payload as string)
          break
        case 'data':
          handlers.onData?.(payload.payload.rows, payload.payload.row_count)
          break
        case 'chart':
          handlers.onChart?.(payload.payload)
          break
        case 'summary':
          handlers.onSummary?.((payload.payload as { summary: string }).summary)
          break
        case 'error':
          handlers.onError?.(payload.payload as string)
          break
        case 'done':
          handlers.onDone?.(payload.payload)
          return
      }
    }
  }
  // 浏览器断流但没收到 done
  handlers.onDone?.(null)
}
