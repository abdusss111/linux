"use client"

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import DashboardLayout from "@/components/dashboard-layout"
import MeetingsList from "@/components/meetings-list"
// import MeetingFilters from "@/components/meeting-filters"
import SummaryCard from "@/components/summary-card"

export default function DashboardPage() {
  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex flex-col gap-4 md:flex-row md:justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Панель управления</h1>
            <p className="text-muted-foreground">Управляйте встречами и просматривайте аналитику</p>
          </div>
        </div>

        <Tabs defaultValue="all" className="space-y-4">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <TabsList>
              <TabsTrigger value="all">Все встречи</TabsTrigger>
              <TabsTrigger value="recent">Недавние</TabsTrigger>
              <TabsTrigger value="upcoming">Предстоящие</TabsTrigger>
            </TabsList>
            {/* <MeetingFilters /> */}
          </div>

          <div className="grid gap-6 md:grid-cols-3">
            <SummaryCard />
          </div>

          <TabsContent value="all" className="space-y-4">
            <MeetingsList />
          </TabsContent>

          <TabsContent value="recent" className="space-y-4">
            <MeetingsList filter="recent" />
          </TabsContent>

          <TabsContent value="upcoming" className="space-y-4">
            <MeetingsList filter="upcoming" />
          </TabsContent>
        </Tabs>
      </div>
    </DashboardLayout>
  )
}
