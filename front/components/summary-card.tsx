"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { BarChart } from "@/components/charts/bar-chart"

// Mock data for the chart
const chartData = [
  { name: "Неделя 1", total: 3 },
  { name: "Неделя 2", total: 5 },
  { name: "Неделя 3", total: 2 },
  { name: "Неделя 4", total: 7 },
  { name: "Неделя 5", total: 4 },
  { name: "Неделя 6", total: 6 },
]

export default function SummaryCard() {
  // In a real app, this would be calculated from actual meeting data
  const meetingsThisMonth = 12

  return (
    <Card className="col-span-3">
      <CardHeader>
        <CardTitle>Аналитика встреч</CardTitle>
        <CardDescription>У вас {meetingsThisMonth} встреч в этом месяце</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[200px]">
          <BarChart data={chartData} />
        </div>
      </CardContent>
    </Card>
  )
}
