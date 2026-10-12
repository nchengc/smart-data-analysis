import ReactECharts from 'echarts-for-react'
import type { ChartSpec, ChartData } from '../lib/mockData'
import { buildEChartsOption, inferChart } from '../lib/chartAdapter'

interface Props {
  chart: ChartSpec
  data: ChartData
  height?: number
}

export default function EChartsView({ chart, data, height = 260 }: Props) {
  // 智能推断：如果 chart 不完整或列名不匹配，用 inferChart 兜底
  const inferred = inferChart(data, chart)
  const finalSpec: ChartSpec = { ...inferred, ...chart, title: chart.title ?? inferred.title }
  const option = buildEChartsOption(finalSpec, data)
  return (
    <ReactECharts
      option={option}
      style={{ height, width: '100%' }}
      notMerge
      lazyUpdate
      theme="light"
      opts={{ renderer: 'canvas' }}
    />
  )
}
