import { Avatar, Space, Tag } from 'antd'
import { UserOutlined, RobotOutlined } from '@ant-design/icons'
import type { ChatMessage } from '../lib/mockData'
import EChartsView from './EChartsView'

export default function MessageItem({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user'

  return (
    <div style={{ display: 'flex', gap: 12, flexDirection: isUser ? 'row-reverse' : 'row' }}>
      <Avatar
        icon={isUser ? <UserOutlined /> : <RobotOutlined />}
        style={{ background: isUser ? '#87d068' : '#1677ff', flexShrink: 0 }}
      />
      <div style={{ maxWidth: '80%' }}>
        <Space direction="vertical" size={6} style={{ width: '100%' }}>
          <div
            style={{
              background: isUser ? '#f6ffed' : '#fff',
              border: '1px solid #f0f0f0',
              borderRadius: 8,
              padding: '10px 14px',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
            }}
          >
            {message.content}
          </div>
          {!isUser && message.chart && message.data && (
            <div
              style={{
                background: '#fff',
                border: '1px solid #f0f0f0',
                borderRadius: 8,
                padding: 12,
              }}
            >
              <div style={{ marginBottom: 8, display: 'flex', gap: 6, alignItems: 'center' }}>
                <Tag color="blue">{message.chart.type}</Tag>
                <span style={{ fontSize: 12, color: '#999' }}>
                  行数：{message.data.length}
                </span>
              </div>
              <EChartsView chart={message.chart} data={message.data} height={220} />
            </div>
          )}
        </Space>
      </div>
    </div>
  )
}
