"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { BarChart } from "@/components/charts/bar-chart"

// Mock data for the chart
const chartData = [
  { name: "Week 1", total: 3 },
  { name: "Week 2", total: 5 },
  { name: "Week 3", total: 2 },
  { name: "Week 4", total: 7 },
  { name: "Week 5", total: 4 },
  { name: "Week 6", total: 6 },
]

export default function SummaryCard() {
  // In a real app, this would be calculated from actual meeting data
  const meetingsThisMonth = 12

  return (
    <Card className="col-span-3">
      <CardHeader>
        <CardTitle>Meeting Analytics</CardTitle>
        <CardDescription>You have {meetingsThisMonth} meetings this month</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[200px]">
          <BarChart data={chartData} />
        </div>
      </CardContent>
    </Card>
  )
}
