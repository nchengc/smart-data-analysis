import { Button, Input, List, Space, Popconfirm, message } from 'antd'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  CheckOutlined,
  CloseOutlined,
  MessageOutlined,
} from '@ant-design/icons'
import { useState } from 'react'
import type { Session } from '../lib/mockData'

interface Props {
  sessions: Session[]
  activeId: string
  onSelect: (id: string) => void
  onNew: () => void
  onRename: (id: string, title: string) => void
  onDelete: (id: string) => void
}

export default function SessionSidebar({
  sessions,
  activeId,
  onSelect,
  onNew,
  onRename,
  onDelete,
}: Props) {
  const [editingId, setEditingId] = useState<string | null>(null)
  const [draft, setDraft] = useState('')

  const startEdit = (s: Session) => {
    setEditingId(s.id)
    setDraft(s.title)
  }
  const commitEdit = (s: Session) => {
    const t = draft.trim()
    if (!t) {
      message.warning('标题不能为空')
      return
    }
    onRename(s.id, t)
    setEditingId(null)
  }
  const cancelEdit = () => setEditingId(null)

  return (
    <div style={{ padding: 12, display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Button type="primary" icon={<PlusOutlined />} block onClick={onNew}>
        新建会话
      </Button>

      <div style={{ margin: '12px 0 4px', fontSize: 12, color: '#999' }}>
        会话列表（{sessions.length}）
      </div>

      <div style={{ overflowY: 'auto', flex: 1 }}>
        <List
          dataSource={sessions}
          renderItem={(s) => {
            const active = s.id === activeId
            const editing = editingId === s.id
            return (
              <List.Item
                key={s.id}
                style={{
                  padding: '8px 10px',
                  borderRadius: 6,
                  cursor: editing ? 'default' : 'pointer',
                  background: active ? '#e6f4ff' : 'transparent',
                  border: active ? '1px solid #91caff' : '1px solid transparent',
                  marginBottom: 4,
                }}
                onClick={() => !editing && onSelect(s.id)}
                actions={
                  editing
                    ? [
                        <CheckOutlined
                          key="ok"
                          onClick={(e) => {
                            e.stopPropagation()
                            commitEdit(s)
                          }}
                        />,
                        <CloseOutlined
                          key="cancel"
                          onClick={(e) => {
                            e.stopPropagation()
                            cancelEdit()
                          }}
                        />,
                      ]
                    : [
                        <EditOutlined
                          key="edit"
                          onClick={(e) => {
                            e.stopPropagation()
                            startEdit(s)
                          }}
                        />,
                        <Popconfirm
                          key="del"
                          title="删除该会话？"
                          onConfirm={(e) => {
                            e?.stopPropagation()
                            onDelete(s.id)
                          }}
                          onCancel={(e) => e?.stopPropagation()}
                          okText="删除"
                          cancelText="取消"
                        >
                          <DeleteOutlined
                            onClick={(e) => {
                              e.stopPropagation()
                            }}
                          />
                        </Popconfirm>,
                      ]
                }
              >
                <Space>
                  <MessageOutlined style={{ color: active ? '#1677ff' : '#999' }} />
                  {editing ? (
                    <Input
                      autoFocus
                      size="small"
                      value={draft}
                      onChange={(e) => setDraft(e.target.value)}
                      onClick={(e) => e.stopPropagation()}
                      onPressEnter={() => commitEdit(s)}
                      style={{ width: 150 }}
                    />
                  ) : (
                    <span style={{ fontSize: 13 }}>{s.title || '未命名会话'}</span>
                  )}
                </Space>
              </List.Item>
            )
          }}
        />
      </div>
      <div style={{ fontSize: 11, color: '#bbb', padding: '8px 4px 0' }}>
        Phase 1：所有数据保存在浏览器 localStorage
      </div>
    </div>
  )
}
