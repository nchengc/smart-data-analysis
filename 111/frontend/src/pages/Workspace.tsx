import { useCallback, useEffect, useMemo, useState } from 'react'
import { Layout, Button, Space, Tag, Typography, message, Spin } from 'antd'
import {
  LogoutOutlined,
  ReloadOutlined,
  RocketOutlined,
  ApiOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import SessionSidebar from '../components/SessionSidebar'
import ChatPanel from '../components/ChatPanel'
import ChartPanel from '../components/ChartPanel'
import { AUTH_KEY } from '../App'
import {
  createSession as apiCreateSession,
  deleteSession as apiDeleteSession,
  listMessages as apiListMessages,
  listSessions as apiListSessions,
  renameSession as apiRenameSession,
} from '../lib/api'
import { useChatStream } from '../hooks/useChatStream'
import { mockAsk } from '../lib/mockChat'
import type { ChartSpec, ChatMessage, Session } from '../lib/mockData'

const { Header, Sider, Content } = Layout
const { Title, Text } = Typography

const MSGS_KEY_PREFIX = 'sda_messages_v1:'

function loadMsgsCache(sid: string): ChatMessage[] {
  try {
    const raw = localStorage.getItem(MSGS_KEY_PREFIX + sid)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}
function saveMsgsCache(sid: string, msgs: ChatMessage[]) {
  localStorage.setItem(MSGS_KEY_PREFIX + sid, JSON.stringify(msgs))
}
function rmMsgsCache(sid: string) {
  localStorage.removeItem(MSGS_KEY_PREFIX + sid)
}

export default function Workspace() {
  const nav = useNavigate()
  const [sessions, setSessions] = useState<Session[]>([])
  const [activeId, setActiveId] = useState<string>('')
  const [msgs, setMsgs] = useState<Record<string, ChatMessage[]>>({})
  const [loading, setLoading] = useState(false)
  const [streamingPhase, setStreamingPhase] = useState<string>('')

  // 首次加载会话列表
  useEffect(() => {
    let mounted = true
    void (async () => {
      setLoading(true)
      try {
        const list = await apiListSessions()
        if (!mounted) return
        setSessions(list)
        if (list.length > 0) {
          setActiveId(list[0].id)
        }
      } catch (e: any) {
        message.error(`加载会话失败：${e.message ?? e}`)
      } finally {
        if (mounted) setLoading(false)
      }
    })()
    return () => {
      mounted = false
    }
  }, [])

  // 切换会话时拉取该会话消息
  useEffect(() => {
    if (!activeId) {
      setMsgs({})
      return
    }
    const cached = loadMsgsCache(activeId)
    if (cached.length) {
      setMsgs((m) => ({ ...m, [activeId]: cached }))
    }
    void (async () => {
      try {
        const list = await apiListMessages(activeId)
        const normalized: ChatMessage[] = list.map((m: any) => ({
          id: `m_${m.id}`,
          role: m.role as 'user' | 'assistant',
          content: m.content,
          createdAt: m.created_at,
          chart: m.chart,
          data: m.data,
          sql: m.sql ?? undefined,
        }))
        setMsgs((prev) => ({ ...prev, [activeId]: normalized }))
        saveMsgsCache(activeId, normalized)
      } catch (e) {
        // 取不到就保持本地缓存
      }
    })()
  }, [activeId])

  // 持久化当前会话消息
  useEffect(() => {
    if (activeId && msgs[activeId]) saveMsgsCache(activeId, msgs[activeId])
  }, [msgs, activeId])

  const activeSession = useMemo(
    () => sessions.find((s) => s.id === activeId) ?? null,
    [sessions, activeId],
  )

  const lastAssistant = useMemo(() => {
    const list = msgs[activeId] ?? []
    for (let i = list.length - 1; i >= 0; i--) {
      if (list[i].role === 'assistant') return list[i]
    }
    return null
  }, [msgs, activeId])

  // ----- chat 流式 -----
  const chat = useChatStream({
    onEvent: (kind, _payload) => {
      if (kind === 'phase') setStreamingPhase(String(_payload ?? ''))
      else if (kind === 'sql' || kind === 'data' || kind === 'chart' || kind === 'summary' || kind === 'error') {
        // 这些由 setActive assistant message 处理，这里只需清理 phase
      }
    },
    onError: (msg) => {
      setStreamingPhase(`⚠️ ${msg}`)
    },
    onDone: (summary, sql, chart, data) => {
      setStreamingPhase('')
      // 找到刚才插入的 assistant placeholder，更新内容
      setMsgs((prev) => {
        const list = prev[activeId] ?? []
        const next = [...list]
        // 最后一条 assistant 一定是 placeholder
        for (let i = next.length - 1; i >= 0; i--) {
          if (next[i].role === 'assistant') {
            next[i] = {
              ...next[i],
              content: summary || '（无总结）',
              sql,
              chart,
              data,
            }
            break
          }
        }
        return { ...prev, [activeId]: next }
      })
    },
  })

  const handleAsk = useCallback(
    async (question: string) => {
      if (!activeId) {
        message.warning('请先新建或选择一个会话')
        return
      }
      const userMsg: ChatMessage = {
        id: `m_u_${Date.now()}`,
        role: 'user',
        content: question,
        createdAt: new Date().toISOString(),
      }
      const placeholder: ChatMessage = {
        id: `m_a_${Date.now()}`,
        role: 'assistant',
        content: '…',
        createdAt: new Date().toISOString(),
      }
      setMsgs((prev) => ({
        ...prev,
        [activeId]: [...(prev[activeId] ?? []), userMsg, placeholder],
      }))
      setStreamingPhase('正在连接后端…')
      try {
        await chat.start(activeId, question)
      } catch (e: any) {
        // 不会到这里：useChatStream 内部已 catch
        message.error(String(e?.message ?? e))
      }
    },
    [activeId, chat],
  )

  // ----- 会话 CRUD -----
  const handleNew = useCallback(async () => {
    try {
      const s = await apiCreateSession('新会话')
      setSessions((prev) => [s, ...prev])
      setActiveId(s.id)
      setMsgs((prev) => ({ ...prev, [s.id]: [] }))
    } catch (e: any) {
      message.error(`新建失败：${e.message ?? e}`)
    }
  }, [])

  const handleRename = useCallback(async (id: string, title: string) => {
    try {
      const updated = await apiRenameSession(id, title)
      setSessions((prev) => prev.map((s) => (s.id === id ? updated : s)))
    } catch (e: any) {
      message.error(`重命名失败：${e.message ?? e}`)
    }
  }, [])

  const handleDelete = useCallback(
    async (id: string) => {
      try {
        await apiDeleteSession(id)
      } catch (e: any) {
        message.warning(`后端删除失败：${e.message ?? e}`)
      }
      setSessions((prev) => prev.filter((s) => s.id !== id))
      setMsgs((prev) => {
        const next = { ...prev }
        delete next[id]
        return next
      })
      rmMsgsCache(id)
      if (activeId === id) {
        const next = sessions.find((s) => s.id !== id)
        setActiveId(next?.id ?? '')
      }
    },
    [activeId, sessions],
  )

  const handleLogout = useCallback(() => {
    localStorage.removeItem(AUTH_KEY)
    message.info('已退出登录')
    nav('/login', { replace: true })
  }, [nav])

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header
        style={{
          background: '#001529',
          padding: '0 24px',
          display: 'flex',
          alignItems: 'center',
          gap: 12,
        }}
      >
        <RocketOutlined style={{ color: '#fff', fontSize: 20 }} />
        <Title level={5} style={{ color: '#fff', margin: 0 }}>
          智能数据分析系统
        </Title>
        <Tag color="processing" style={{ marginLeft: 12 }}>
          Phase 3 · 联调
        </Tag>
        {chat.state.pending && (
          <Tag color="warning" icon={<ApiOutlined spin />}>
            {streamingPhase || '正在调用后端…'}
          </Tag>
        )}
        {chat.state.error && !chat.state.pending && (
          <Tag color="error">后端异常</Tag>
        )}
        <div style={{ flex: 1 }} />
        <Space>
          <Text style={{ color: '#fff', fontSize: 13 }}>
            {activeSession?.title ?? '当前会话：—'}
          </Text>
          <Button
            size="small"
            icon={<ReloadOutlined />}
            onClick={() => window.location.reload()}
            title="刷新页面"
          >
            刷新
          </Button>
          <Button size="small" icon={<LogoutOutlined />} onClick={handleLogout}>
            退出
          </Button>
        </Space>
      </Header>

      <Layout>
        <Sider width={260} style={{ background: '#fff' }}>
          {loading && sessions.length === 0 ? (
            <div style={{ padding: 24, textAlign: 'center' }}>
              <Spin /> <Text>加载会话…</Text>
            </div>
          ) : (
            <SessionSidebar
              sessions={sessions}
              activeId={activeId}
              onSelect={setActiveId}
              onNew={handleNew}
              onRename={handleRename}
              onDelete={handleDelete}
            />
          )}
        </Sider>

        <Content style={{ background: '#f5f7fa' }}>
          <ChatPanel
            messages={msgs[activeId] ?? []}
            pending={chat.state.pending}
            streamingPhase={streamingPhase}
            onAsk={handleAsk}
            disabled={!activeId}
          />
        </Content>

        <Sider width={380} style={{ background: '#fff', borderLeft: '1px solid #f0f0f0' }}>
          <ChartPanel message={lastAssistant} />
        </Sider>
      </Layout>
    </Layout>
  )
}
