import { useEffect, useMemo, useState } from 'react'
import { Layout, Button, Space, Tag, Typography, message } from 'antd'
import { LogoutOutlined, ReloadOutlined, RocketOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import SessionSidebar from '../components/SessionSidebar'
import ChatPanel from '../components/ChatPanel'
import ChartPanel from '../components/ChartPanel'
import { AUTH_KEY } from '../App'
import { initialSessions, type ChatMessage, type Session } from '../lib/mockData'
import { mockAsk } from '../lib/mockChat'

const { Header, Sider, Content } = Layout
const { Title } = Typography

const SESSIONS_KEY = 'sda_sessions_v1'
const MSGS_KEY = 'sda_messages_v1'

function loadOrSeedSessions(): Session[] {
  const raw = localStorage.getItem(SESSIONS_KEY)
  if (raw) {
    try {
      return JSON.parse(raw)
    } catch {
      /* fallthrough */
    }
  }
  const seeded = initialSessions()
  localStorage.setItem(SESSIONS_KEY, JSON.stringify(seeded))
  return seeded
}

function loadMsgs(): Record<string, ChatMessage[]> {
  const raw = localStorage.getItem(MSGS_KEY)
  if (!raw) return {}
  try {
    return JSON.parse(raw)
  } catch {
    return {}
  }
}

function persistSessions(arr: Session[]) {
  localStorage.setItem(SESSIONS_KEY, JSON.stringify(arr))
}

function persistMsgs(map: Record<string, ChatMessage[]>) {
  localStorage.setItem(MSGS_KEY, JSON.stringify(map))
}

export default function Workspace() {
  const nav = useNavigate()
  const [sessions, setSessions] = useState<Session[]>(loadOrSeedSessions)
  const [activeId, setActiveId] = useState<string>(sessions[0]?.id ?? '')
  const [msgs, setMsgs] = useState<Record<string, ChatMessage[]>>(loadMsgs)
  const [pending, setPending] = useState(false)

  useEffect(() => {
    persistSessions(sessions)
  }, [sessions])

  useEffect(() => {
    persistMsgs(msgs)
  }, [msgs])

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

  const handleNew = () => {
    const id = `s_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`
    const s: Session = {
      id,
      title: '新会话',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    }
    setSessions((prev) => [s, ...prev])
    setActiveId(id)
    setMsgs((prev) => ({ ...prev, [id]: [] }))
    message.success('已新建会话')
  }

  const handleRename = (id: string, title: string) => {
    setSessions((prev) =>
      prev.map((s) => (s.id === id ? { ...s, title, updatedAt: new Date().toISOString() } : s)),
    )
  }

  const handleDelete = (id: string) => {
    setSessions((prev) => prev.filter((s) => s.id !== id))
    setMsgs((prev) => {
      const next = { ...prev }
      delete next[id]
      return next
    })
    if (activeId === id) {
      const next = sessions.filter((s) => s.id !== id)[0]
      setActiveId(next?.id ?? '')
    }
    message.success('已删除会话')
  }

  const handleAsk = async (question: string) => {
    if (!activeId) {
      message.warning('请先新建或选择一个会话')
      return
    }
    const userMsg: ChatMessage = {
      id: `m_${Date.now()}_u`,
      role: 'user',
      content: question,
      createdAt: new Date().toISOString(),
    }
    setMsgs((prev) => ({
      ...prev,
      [activeId]: [...(prev[activeId] ?? []), userMsg],
    }))
    // 更新会话标题
    setSessions((prev) =>
      prev.map((s) =>
        s.id === activeId
          ? {
              ...s,
              title:
                s.title === '新会话'
                  ? question.slice(0, 18) + (question.length > 18 ? '…' : '')
                  : s.title,
              updatedAt: new Date().toISOString(),
            }
          : s,
      ),
    )
    setPending(true)
    try {
      const assistantMsg = await mockAsk(question, msgs[activeId] ?? [])
      setMsgs((prev) => ({
        ...prev,
        [activeId]: [...(prev[activeId] ?? []), assistantMsg],
      }))
    } finally {
      setPending(false)
    }
  }

  const handleLogout = () => {
    localStorage.removeItem(AUTH_KEY)
    message.info('已退出登录')
    nav('/login', { replace: true })
  }

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
          Phase 1 · 三栏 + Mock
        </Tag>
        <div style={{ flex: 1 }} />
        <Space>
          <span style={{ color: '#fff', fontSize: 13 }}>
            {activeSession?.title ?? '当前会话：—'}
          </span>
          <Button
            size="small"
            icon={<ReloadOutlined />}
            onClick={() => {
              localStorage.removeItem(SESSIONS_KEY)
              localStorage.removeItem(MSGS_KEY)
              window.location.reload()
            }}
          >
            重置数据
          </Button>
          <Button size="small" icon={<LogoutOutlined />} onClick={handleLogout}>
            退出
          </Button>
        </Space>
      </Header>

      <Layout>
        <Sider width={260} style={{ background: '#fff' }}>
          <SessionSidebar
            sessions={sessions}
            activeId={activeId}
            onSelect={setActiveId}
            onNew={handleNew}
            onRename={handleRename}
            onDelete={handleDelete}
          />
        </Sider>

        <Content style={{ background: '#f5f7fa' }}>
          <ChatPanel
            messages={msgs[activeId] ?? []}
            pending={pending}
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
