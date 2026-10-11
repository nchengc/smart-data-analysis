import ReactECharts from 'echarts-for-react'
import type { ChartSpec, ChartData } from '../lib/mockData'

interface Props {
  chart: ChartSpec
  data: ChartData
  height?: number
}

function buildOption(chart: ChartSpec, data: ChartData) {
  if (chart.type === 'pie') {
    const x = chart.x ?? 'name'
    const y = chart.y ?? 'value'
    return {
      tooltip: { trigger: 'item' },
      legend: { type: 'scroll', bottom: 0 },
      series: [
        {
          name: chart.title ?? '',
          type: 'pie',
          radius: ['35%', '65%'],
          data: data.map((d) => ({ name: String(d[x] ?? ''), value: Number(d[y] ?? 0) })),
        },
      ],
    }
  }

  if (chart.type === 'line') {
    const x = chart.x ?? 'x'
    const yKey = chart.y ?? 'y'
    const series = (Array.isArray(yKey) ? yKey : [yKey]).map((k) => ({
      name: k,
      type: 'line',
      smooth: true,
      data: data.map((d) => Number(d[k] ?? 0)),
    }))
    return {
      tooltip: { trigger: 'axis' },
      legend: { bottom: 0 },
      xAxis: { type: 'category', data: data.map((d) => String(d[x] ?? '')) },
      yAxis: { type: 'value' },
      grid: { left: 40, right: 20, top: 20, bottom: 40 },
      series,
    }
  }

  if (chart.type === 'scatter') {
    const x = chart.x ?? 'x'
    const y = chart.y ?? 'y'
    return {
      tooltip: { trigger: 'item' },
      xAxis: { type: 'value' },
      yAxis: { type: 'value' },
      grid: { left: 40, right: 20, top: 20, bottom: 40 },
      series: [
        {
          type: 'scatter',
          data: data.map((d) => [Number(d[x] ?? 0), Number(d[y] ?? 0)]),
        },
      ],
    }
  }

  // bar (default)
  const x = chart.x ?? 'x'
  const y = chart.y ?? 'y'
  const series = (Array.isArray(y) ? y : [y]).map((k) => ({
    name: k,
    type: 'bar',
    data: data.map((d) => Number(d[k] ?? 0)),
  }))
  return {
    tooltip: { trigger: 'axis' },
    legend: { bottom: 0 },
    xAxis: { type: 'category', data: data.map((d) => String(d[x] ?? '')) },
    yAxis: { type: 'value' },
    grid: { left: 40, right: 20, top: 20, bottom: 40 },
    series,
  }
}

export default function EChartsView({ chart, data, height = 260 }: Props) {
  return (
    <ReactECharts
      option={buildOption(chart, data)}
      style={{ height, width: '100%' }}
      notMerge
      lazyUpdate
      theme="light"
    />
  )
}
