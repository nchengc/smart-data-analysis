import { Empty, Card, Tabs, Tag, Alert } from 'antd'
import type { ChatMessage } from '../lib/mockData'
import EChartsView from './EChartsView'

interface Props {
  message: ChatMessage | null
}

export default function ChartPanel({ message }: Props) {
  if (!message) {
    return (
      <div style={{ padding: 24, height: '100%' }}>
        <Card title="📊 可视化图表" bordered={false}>
          <Empty description="还没有数据。先在中间问答区问一个问题试试。" />
        </Card>
      </div>
    )
  }

  const { chart, data, sql } = message

  return (
    <div style={{ padding: 12, height: '100%', overflowY: 'auto' }}>
      <Card
        title={
          <span>
            📊 {chart?.title ?? '可视化'}
            {chart && <Tag color="blue" style={{ marginLeft: 8 }}>{chart.type}</Tag>}
          </span>
        }
        bordered={false}
        bodyStyle={{ padding: 12 }}
        size="small"
      >
        {data && chart ? (
          <EChartsView chart={chart} data={data} height={280} />
        ) : (
          <Empty description="本次回答未返回图表" />
        )}
      </Card>

      <Tabs
        size="small"
        style={{ marginTop: 12 }}
        items={[
          {
            key: 'data',
            label: '数据',
            children: (
              <Card size="small" bordered={false}>
                {data && data.length > 0 ? (
                  <pre style={{ fontSize: 12, maxHeight: 220, overflow: 'auto', margin: 0 }}>
                    {JSON.stringify(data, null, 2)}
                  </pre>
                ) : (
                  <Empty description="无数据" />
                )}
              </Card>
            ),
          },
          {
            key: 'sql',
            label: 'SQL',
            children: (
              <Card size="small" bordered={false}>
                {sql ? (
                  <pre
                    style={{
                      fontSize: 12,
                      maxHeight: 220,
                      overflow: 'auto',
                      margin: 0,
                      background: '#fafafa',
                      padding: 8,
                    }}
                  >
                    {sql}
                  </pre>
                ) : (
                  <Empty description="无 SQL" />
                )}
              </Card>
            ),
          },
          {
            key: 'tip',
            label: '说明',
            children: (
              <Alert
                type="info"
                showIcon
                message="Phase 1 Mock 模式"
                description="此图表与数据由前端 mock 随机生成，与后端无关。Phase 3 联调后会替换为真实接口调用结果。"
                style={{ fontSize: 12 }}
              />
            ),
          },
        ]}
      />
    </div>
  )
}
