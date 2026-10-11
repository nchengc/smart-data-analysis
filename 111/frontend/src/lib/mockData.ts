// Phase 1 本地 mock 数据契约与默认 seed

export type ChartType = 'bar' | 'line' | 'pie' | 'scatter'

export interface ChartSpec {
  type: ChartType
  title?: string
  x?: string
  y?: string | string[]
  group_by?: string
  agg?: 'sum' | 'avg' | 'count' | 'max' | 'min'
}

export type ChartData = Array<Record<string, string | number>>

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  createdAt: string
  chart?: ChartSpec
  data?: ChartData
  sql?: string
}

export interface Session {
  id: string
  title: string
  createdAt: string
  updatedAt: string
}

export function initialSessions(): Session[] {
  const now = new Date()
  const mk = (title: string, offsetMin: number): Session => ({
    id: `s_seed_${title}`,
    title,
    createdAt: new Date(now.getTime() - offsetMin * 60_000).toISOString(),
    updatedAt: new Date(now.getTime() - offsetMin * 60_000).toISOString(),
  })
  return [
    mk('欢迎示例 · 销售概览', 30),
    mk('品类 Top10', 18),
    mk('门店对比', 5),
  ]
}
