import { useEffect, useState } from 'react'
import { Button, Card, Layout, Space, Tag, Typography } from 'antd'
import {
  ApiOutlined,
  CheckCircleTwoTone,
  RocketOutlined,
} from '@ant-design/icons'

const { Header, Content } = Layout
const { Title, Paragraph, Text } = Typography

interface HealthData {
  status: string
  version: string
  phase: string
}

function App() {
  const [health, setHealth] = useState<HealthData | null>(null)
  const [error, setError] = useState<string | null>(null)

  const checkHealth = async () => {
    setError(null)
    try {
      const resp = await fetch('/api/health')
      const data = await resp.json()
      setHealth(data)
    } catch (e) {
      setError(String(e))
    }
  }

  useEffect(() => {
    void checkHealth()
  }, [])

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header
        style={{
          background: '#001529',
          display: 'flex',
          alignItems: 'center',
          gap: 12,
        }}
      >
        <RocketOutlined style={{ color: '#fff', fontSize: 22 }} />
        <Title level={4} style={{ color: '#fff', margin: 0 }}>
          智能数据分析系统
        </Title>
        <Tag color="processing" style={{ marginLeft: 'auto' }}>
          Phase 0 · 骨架
        </Tag>
      </Header>

      <Content style={{ padding: 32 }}>
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <Card title="✅ 前后端联通自检">
            <Paragraph>
              浏览器通过 Vite 代理 <Text code>/api/health</Text> 调用 FastAPI 后端。
            </Paragraph>
            {health && (
              <Paragraph>
                <CheckCircleTwoTone twoToneColor="#52c41a" /> 后端响应：
                <Text code>{JSON.stringify(health)}</Text>
              </Paragraph>
            )}
            {error && (
              <Paragraph type="danger">❌ 请求失败：{error}</Paragraph>
            )}
            <Button type="primary" icon={<ApiOutlined />} onClick={checkHealth}>
              重新检测
            </Button>
          </Card>

          <Card title="📌 Phase 0 验收清单">
            <ul>
              <li>✅ 后端 FastAPI 启动（uvicorn 监听 8000）</li>
              <li>
                ✅ 前端 Vite 启动（监听 5173，已配置代理
                <Text code>/api → 8000</Text>）
              </li>
              <li>✅ AntD 中文 Locale 全局生效</li>
              <li>✅ 这个页面能看到后端 health 响应</li>
            </ul>
          </Card>

          <Card title="🛣 接下来的 Phase">
            <ul>
              <li>
                <strong>Phase 1</strong>：完整前端 UI（三栏 + 登录页 + Mock 数据）
              </li>
              <li>
                <strong>Phase 2</strong>：后端业务接口（LLM / SQLite / Agent / SSE）
              </li>
              <li>
                <strong>Phase 3</strong>：前后端联调（ECharts + 上下文记忆）
              </li>
            </ul>
          </Card>
        </Space>
      </Content>
    </Layout>
  )
}

export default App
