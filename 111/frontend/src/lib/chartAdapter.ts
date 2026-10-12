// 智能 ECharts 适配器：根据列名 / 数据形状 / 行数自动选最佳 chart type
//
// 启发式：
// - 列名含 date/month/year/quarter/week/day/time → 时间序列 → line
// - 字符串分类列 + 1 个数值列 + 1-12 行 → 优先 bar（带 sort desc）
// - 字符串分类 + 1 个数值列 + 行数较多 → 折线 OR 排序后 top 15
// - 字符串分类 + 1 个数值列 + 行数 ≤ 6 → pie
// - 2 个数值列 → scatter
// - 1 行多数值列（横表） → bar（适合 KPI 对比）
// - 多数值列（>=2）+ 分类列 → multi-series bar/line

import type { ChartSpec, ChartData } from './mockData'

const TIME_KEYS = ['date', 'time', 'month', 'year', 'quarter', 'week', 'day', 'ym', 'y_m', 'yyyy', 'mm', 'dd']

function isTimeKey(k: string): boolean {
  const lower = k.toLowerCase()
  return TIME_KEYS.some((t) => lower.includes(t))
}

function isNumeric(v: unknown): boolean {
  return typeof v === 'number' && Number.isFinite(v)
}

function getColumnTypes(data: ChartData): Record<string, 'number' | 'string' | 'mixed'> {
  if (!data.length) return {}
  const cols = Object.keys(data[0])
  const types: Record<string, 'number' | 'string' | 'mixed'> = {}
  for (const c of cols) {
    let nNum = 0
    let nStr = 0
    for (const row of data) {
      const v = row[c]
      if (v == null) continue
      if (isNumeric(v)) nNum++
      else nStr++
    }
    if (nNum > 0 && nStr === 0) types[c] = 'number'
    else if (nStr > 0 && nNum === 0) types[c] = 'string'
    else types[c] = 'mixed'
  }
  return types
}

/** 智能推断最合适的 ChartSpec */
export function inferChart(data: ChartData, hint?: ChartSpec): ChartSpec {
  if (!data || data.length === 0) {
    return { type: 'table', title: hint?.title ?? '无数据' }
  }
  const cols = Object.keys(data[0])
  const types = getColumnTypes(data)
  const nRows = data.length

  // 找出各类型列
  const timeCols = cols.filter((c) => types[c] === 'string' && isTimeKey(c))
  const numericCols = cols.filter((c) => types[c] === 'number')
  const stringCols = cols.filter((c) => types[c] === 'string' && !isTimeKey(c))
  const firstCol = cols[0]
  const firstType = types[firstCol] ?? 'string'

  // 1) 时间列 + 至少 1 个数值列 → 折线图
  if (timeCols.length > 0 && numericCols.length > 0) {
    return {
      type: 'line',
      title: hint?.title ?? numericCols[0],
      x: hint?.x ?? timeCols[0],
      y: hint?.y ?? numericCols[0],
    }
  }

  // 2) 1 行多数值列（横表） → bar（适合 KPI 对比）
  if (nRows === 1 && numericCols.length >= 2) {
    return {
      type: 'bar',
      title: hint?.title ?? '对比',
      x: firstCol,
      y: numericCols,
    }
  }

  // 3) 字符串分类列 + 1 个数值列
  if (stringCols.length >= 1 && numericCols.length === 1 && firstType === 'string') {
    if (nRows <= 6) {
      // 少行用饼图更直观
      return {
        type: 'pie',
        title: hint?.title ?? numericCols[0],
        x: hint?.x ?? firstCol,
        y: hint?.y ?? numericCols[0],
      }
    }
    // 多行：bar（横轴分类，纵轴数值）
    return {
      type: 'bar',
      title: hint?.title ?? numericCols[0],
      x: hint?.x ?? firstCol,
      y: hint?.y ?? numericCols[0],
    }
  }

  // 4) 2 数值列 → 散点图
  if (numericCols.length === 2 && stringCols.length === 0) {
    return {
      type: 'scatter',
      title: hint?.title ?? `${numericCols[0]} vs ${numericCols[1]}`,
      x: hint?.x ?? numericCols[0],
      y: hint?.y ?? numericCols[1],
    }
  }

  // 5) 多数值列（>=2） + 1 分类列 → multi-series bar
  if (stringCols.length >= 1 && numericCols.length >= 2) {
    return {
      type: 'bar',
      title: hint?.title ?? stringCols[0],
      x: hint?.x ?? stringCols[0],
      y: hint?.y ?? numericCols,
    }
  }

  // 6) 默认：表格
  return {
    type: 'table',
    title: hint?.title ?? '数据',
    x: hint?.x ?? firstCol,
  }
}

// ---- ECharts option builder ----

interface EChartOption {
  tooltip?: any
  legend?: any
  grid?: any
  xAxis?: any
  yAxis?: any
  series?: any
  color?: string[]
}

const PALETTE = [
  '#1677ff', '#52c41a', '#fa8c16', '#eb2f96', '#722ed1',
  '#13c2c2', '#f5222d', '#a0d911', '#2f54eb', '#fa541c',
]

function buildOption(chart: ChartSpec, data: ChartData): EChartOption {
  // chart.x 是 string | string[]；这里我们只取第一个字符串作为 X 轴
  const xFirst = Array.isArray(chart.x) ? chart.x[0] : chart.x
  const cols = data.length > 0 ? Object.keys(data[0]) : []
  const fallback = inferChart(data, chart)
  const fX = Array.isArray(fallback.x) ? fallback.x[0] : fallback.x

  if (chart.type === 'pie') {
    const x = xFirst ?? fX ?? cols[0]
    const yRaw = Array.isArray(chart.y) ? chart.y[0] : chart.y
    const yFb = Array.isArray(fallback.y) ? fallback.y[0] : fallback.y
    const y = yRaw ?? yFb ?? cols[1] ?? cols[0]
    return {
      color: PALETTE,
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
      legend: { type: 'scroll', bottom: 0 },
      series: [
        {
          name: chart.title ?? y,
          type: 'pie',
          radius: ['35%', '65%'],
          center: ['50%', '45%'],
          label: { formatter: '{b}\n{d}%' },
          data: data.map((d) => ({ name: String(d[x] ?? ''), value: Number(d[y] ?? 0) })),
        },
      ],
    }
  }

  if (chart.type === 'line') {
    const x = xFirst ?? fX ?? cols[0]
    const yRaw = Array.isArray(chart.y) ? chart.y[0] : chart.y
    const yFb = Array.isArray(fallback.y) ? fallback.y[0] : fallback.y
    const yKey = yRaw ?? yFb ?? cols[1] ?? cols[0]
    const series = (Array.isArray(yKey) ? yKey : [yKey]).map((k) => ({
      name: k,
      type: 'line',
      smooth: true,
      symbolSize: 6,
      lineStyle: { width: 2 },
      data: data.map((d) => Number(d[k] ?? 0)),
    }))
    return {
      color: PALETTE,
      tooltip: { trigger: 'axis' },
      legend: { bottom: 0 },
      grid: { left: 50, right: 20, top: 20, bottom: 50, containLabel: true },
      xAxis: { type: 'category', data: data.map((d) => String(d[x] ?? '')) },
      yAxis: { type: 'value' },
      series,
    }
  }

  if (chart.type === 'scatter') {
    const x = xFirst ?? fX ?? cols[0]
    const yRaw = Array.isArray(chart.y) ? chart.y[0] : chart.y
    const yFb = Array.isArray(fallback.y) ? fallback.y[0] : fallback.y
    const y = yRaw ?? yFb ?? cols[1] ?? cols[0]
    return {
      color: PALETTE,
      tooltip: { trigger: 'item', formatter: (p: any) => `${x}=${p.value[0]}, ${y}=${p.value[1]}` },
      grid: { left: 50, right: 20, top: 20, bottom: 40, containLabel: true },
      xAxis: { type: 'value', name: x, nameLocation: 'middle', nameGap: 30 },
      yAxis: { type: 'value', name: y, nameLocation: 'middle', nameGap: 40 },
      series: [
        {
          type: 'scatter',
          data: data.map((d) => [Number(d[x] ?? 0), Number(d[y] ?? 0)]),
          symbolSize: 10,
        },
      ],
    }
  }

  // bar (default)
  const x = xFirst ?? fX ?? cols[0]
  const yRaw = Array.isArray(chart.y) ? chart.y[0] : chart.y
  const yFb = Array.isArray(fallback.y) ? fallback.y[0] : fallback.y
  const y = yRaw ?? yFb ?? cols[1] ?? cols[0]
  const yKeys = Array.isArray(y) ? y : [y]
  const series = yKeys.map((k) => ({
    name: k,
    type: 'bar',
    barMaxWidth: 40,
    data: data.map((d) => Number(d[k] ?? 0)),
    label: { show: data.length <= 12, position: 'top', formatter: (p: any) => formatVal(p.value) },
  }))
  return {
    color: PALETTE,
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: yKeys.length > 1 ? { bottom: 0 } : undefined,
    grid: { left: 60, right: 20, top: 20, bottom: 50, containLabel: true },
    xAxis: { type: 'category', data: data.map((d) => String(d[x] ?? '')) },
    yAxis: { type: 'value' },
    series,
  }
}

function formatVal(v: number): string {
  if (v >= 1e8) return (v / 1e8).toFixed(1) + '亿'
  if (v >= 1e4) return (v / 1e4).toFixed(1) + '万'
  return String(v)
}

export function buildEChartsOption(chart: ChartSpec, data: ChartData): EChartOption {
  return buildOption(chart, data)
}
