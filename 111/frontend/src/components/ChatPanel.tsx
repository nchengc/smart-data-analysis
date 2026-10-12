import { useEffect, useRef, useState } from 'react'
import { Button, Empty, Input, Space, Spin, Tag, Avatar } from 'antd'
import { SendOutlined, UserOutlined, RobotOutlined } from '@ant-design/icons'
import type { ChatMessage } from '../lib/mockData'
import MessageItem from './MessageItem'

interface Props {
  messages: ChatMessage[]
  pending: boolean
  streamingPhase?: string
  onAsk: (q: string) => void | Promise<void>
  disabled?: boolean
}

export default function ChatPanel({ messages, pending, streamingPhase, onAsk, disabled }: Props) {
  const [draft, setDraft] = useState('')
  const scrollRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: 'smooth',
    })
  }, [messages.length, pending])

  const submit = async () => {
    const text = draft.trim()
    if (!text || pending || disabled) return
    setDraft('')
    await onAsk(text)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div
        ref={scrollRef}
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: 24,
        }}
      >
        {messages.length === 0 ? (
          <div style={{ marginTop: 80, textAlign: 'center' }}>
            <Empty
              description={
                <span>
                  暂无消息。<br />
                  试试输入 <Tag color="blue">上月华东区销售额</Tag> / <Tag color="blue">各品类销量 Top10</Tag>
                </span>
              }
            />
          </div>
        ) : (
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            {messages.map((m) => (
              <MessageItem key={m.id} message={m} />
            ))}
            {pending && (
              <div style={{ display: 'flex', gap: 8, alignItems: 'center', paddingLeft: 4 }}>
                <Avatar icon={<RobotOutlined />} style={{ background: '#1677ff' }} />
                <Spin size="small" />{' '}
                <span style={{ color: '#999' }}>
                  {streamingPhase || '正在生成回答…'}
                </span>
              </div>
            )}
          </Space>
        )}
      </div>

      <div
        style={{
          background: '#fff',
          borderTop: '1px solid #f0f0f0',
          padding: 16,
        }}
      >
        <Space.Compact style={{ width: '100%' }}>
          <Input.TextArea
            placeholder={disabled ? '请先新建一个会话' : '用自然语言描述你的数据分析需求，例如：上月华东区销售额是多少？'}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            disabled={pending || disabled}
            autoSize={{ minRows: 1, maxRows: 4 }}
            onPressEnter={(e) => {
              if (!e.shiftKey) {
                e.preventDefault()
                void submit()
              }
            }}
          />
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={submit}
            disabled={!draft.trim() || pending || disabled}
            style={{ height: 'auto' }}
          >
            发送
          </Button>
        </Space.Compact>
        <div style={{ fontSize: 11, color: '#bbb', marginTop: 6 }}>
          Phase 3：流式调用后端 /api/chat/stream。Enter 发送，Shift+Enter 换行。
        </div>
      </div>
    </div>
  )
}
