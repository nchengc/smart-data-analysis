// Phase 1 本地 mock 问答：根据关键词返回不同的图表/数据

import type { ChatMessage, ChartData, ChartSpec } from './mockData'

function rand(min: number, max: number) {
  return Math.floor(Math.random() * (max - min + 1)) + min
}

const REGIONS = ['华东区', '华南区', '华北区', '西南区', '西北区']
const CATEGORIES = ['家电', '服饰', '美妆', '食品', '数码', '母婴', '运动', '图书']

function salesByRegion(): { chart: ChartSpec; data: ChartData; summary: string } {
  const data = REGIONS.map((r) => ({ region: r, sales: rand(800_000, 2_400_000) }))
  const top = data.reduce((a, b) => (a.sales > b.sales ? a : b))
  return {
    chart: { type: 'bar', title: '各区销售对比', x: 'region', y: 'sales' },
    data,
    summary: `${top.region}以 ${top.sales.toLocaleString()} 元领跑，其余大区依次为 …`,
  }
}

function categoryTop(): { chart: ChartSpec; data: ChartData; summary: string } {
  const data = CATEGORIES.map((c) => ({ category: c, qty: rand(120, 980) }))
    .sort((a, b) => b.qty - a.qty)
  return {
    chart: { type: 'bar', title: '品类销量 Top', x: 'category', y: 'qty' },
    data,
    summary: `销量最高的品类是 ${data[0].category}（${data[0].qty} 件）。`,
  }
}

function trendMonths(): { chart: ChartSpec; data: ChartData; summary: string } {
  const months = ['1月', '2月', '3月', '4月', '5月', '6月']
  const data = months.map((m) => ({ month: m, sales: rand(300_000, 1_200_000), orders: rand(800, 3500) }))
  return {
    chart: { type: 'line', title: '近 6 个月销售趋势', x: 'month', y: ['sales', 'orders'] },
    data,
    summary: `近 6 个月销售呈波动上升态势，最高峰出现在 ${data.reduce((a,b)=>a.sales>b.sales?a:b).month}。`,
  }
}

function stores(): { chart: ChartSpec; data: ChartData; summary: string } {
  const names = ['北京旗舰店', '上海徐汇店', '深圳南山店', '广州天河店', '杭州西湖店']
  const data = names.map((n) => ({ store: n, gmv: rand(400_000, 1_500_000) }))
  return {
    chart: { type: 'pie', title: '门店 GMV 占比', x: 'store', y: 'gmv' },
    data,
    summary: `门店 GMV 占比中，${data[0].store} 贡献最大。`,
  }
}

function fallback(q: string): { chart: ChartSpec; data: ChartData; summary: string } {
  return {
    chart: { type: 'bar', title: '示例数据（mock）', x: 'k', y: 'v' },
    data: Array.from({ length: 5 }).map((_, i) => ({ k: `指标${i + 1}`, v: rand(50, 500) })),
    summary: `本次回答为 Phase 1 mock，关键词「${q.slice(0, 12)}」未匹配到具体模板。`,
  }
}

function route(q: string): { chart: ChartSpec; data: ChartData; summary: string } {
  const lower = q.toLowerCase()
  if (/(区|地区|地域|region)/.test(lower)) return salesByRegion()
  if (/(品类|类目|分类|category)/.test(lower)) return categoryTop()
  if (/(月|趋势|走势|trend)/.test(lower)) return trendMonths()
  if (/(店|门店|store)/.test(lower)) return stores()
  return fallback(q)
}

export async function mockAsk(
  question: string,
  _history: ChatMessage[],
): Promise<ChatMessage> {
  // 模拟 0.6-1.2 秒网络延迟
  await new Promise((r) => setTimeout(r, 600 + Math.random() * 600))
  const { chart, data, summary } = route(question)
  const fakeSql = `-- mock SQL for: ${question}\nSELECT region, SUM(sales) FROM mock_orders GROUP BY region;`
  return {
    id: `m_${Date.now()}_a`,
    role: 'assistant',
    content: summary,
    createdAt: new Date().toISOString(),
    chart,
    data,
    sql: fakeSql,
  }
}
