import { Form, Input, Button, Card, Typography, Space, message } from 'antd'
import { LockOutlined, UserOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { AUTH_KEY } from '../App'

const { Title, Paragraph } = Typography

const DEMO_USER = 'demo'
const DEMO_PASS = 'demo'

export default function Login() {
  const nav = useNavigate()

  const onFinish = (v: { username: string; password: string }) => {
    if (v.username === DEMO_USER && v.password === DEMO_PASS) {
      localStorage.setItem(AUTH_KEY, '1')
      message.success('登录成功')
      nav('/workspace', { replace: true })
    } else {
      message.error('账号或密码错误（demo 阶段请用 demo / demo）')
    }
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        background: 'linear-gradient(135deg,#001529,#1f3a5f)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
      }}
    >
      <Card style={{ width: 380, borderRadius: 12 }} bodyStyle={{ padding: 32 }}>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div style={{ textAlign: 'center' }}>
            <Title level={3} style={{ marginBottom: 4 }}>
              智能数据分析系统
            </Title>
            <Paragraph type="secondary" style={{ margin: 0 }}>
              Phase 1 · Demo 登录（账号 <b>demo</b> / 密码 <b>demo</b>）
            </Paragraph>
          </div>

          <Form layout="vertical" onFinish={onFinish} initialValues={{ username: 'demo', password: 'demo' }}>
            <Form.Item
              name="username"
              label="账号"
              rules={[{ required: true, message: '请输入账号' }]}
            >
              <Input prefix={<UserOutlined />} placeholder="demo" autoFocus />
            </Form.Item>
            <Form.Item
              name="password"
              label="密码"
              rules={[{ required: true, message: '请输入密码' }]}
            >
              <Input.Password prefix={<LockOutlined />} placeholder="demo" />
            </Form.Item>
            <Form.Item style={{ marginBottom: 0 }}>
              <Button type="primary" htmlType="submit" block size="large">
                登录
              </Button>
            </Form.Item>
          </Form>
        </Space>
      </Card>
    </div>
  )
}
