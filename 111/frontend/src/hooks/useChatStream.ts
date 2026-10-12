// useChatStream：订阅 SSE 流式问答事件

import { useCallback, useRef, useState } from 'react'
import { streamChat, type StreamHandlers } from '../lib/api'
import type { ChatMessage, ChartSpec } from '../lib/mockData'

export interface UseChatStreamState {
  pending: boolean
  error: string | null
}

export function useChatStream(opts: {
  onEvent: (kind: 'sql' | 'data' | 'chart' | 'summary' | 'phase' | 'error', payload: any) => void
  onDone: (summary: string, sql: string, chart?: ChartSpec, data?: any[]) => void
  onError: (msg: string) => void
}) {
  const [state, setState] = useState<UseChatStreamState>({ pending: false, error: null })
  const abortRef = useRef<AbortController | null>(null)

  const start = useCallback(
    async (sessionId: string, question: string) => {
      if (!sessionId) return
      // 取消上一次
      abortRef.current?.abort()
      const ctrl = new AbortController()
      abortRef.current = ctrl
      setState({ pending: true, error: null })

      let collectedSql = ''
      let collectedChart: ChartSpec | undefined
      let collectedData: any[] | undefined
      let collectedSummary = ''

      const handlers: StreamHandlers = {
        onPhase: (msg) => opts.onEvent('phase', msg),
        onSql: (sql) => {
          collectedSql = sql
          opts.onEvent('sql', sql)
        },
        onData: (rows, _count) => {
          collectedData = rows
          opts.onEvent('data', rows)
        },
        onChart: (chart) => {
          collectedChart = chart
          opts.onEvent('chart', chart)
        },
        onSummary: (summary) => {
          collectedSummary = summary
          opts.onEvent('summary', summary)
        },
        onError: (msg) => {
          opts.onError(msg)
          setState({ pending: true, error: msg })  // keep pending so we can fallback
        },
        onDone: (meta) => {
          setState({ pending: false, error: null })
          opts.onDone(collectedSummary, collectedSql, collectedChart, collectedData)
        },
      }

      try {
        await streamChat(sessionId, question, handlers, ctrl.signal)
      } catch (e: any) {
        if (e?.name === 'AbortError') {
          setState({ pending: false, error: null })
          return
        }
        setState({ pending: false, error: String(e?.message ?? e) })
        opts.onError(String(e?.message ?? e))
      }
    },
    [opts],
  )

  const stop = useCallback(() => {
    abortRef.current?.abort()
  }, [])

  return { state, start, stop }
}
