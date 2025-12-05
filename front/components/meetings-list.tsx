"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Calendar, Search, User } from "lucide-react"
import { Input } from "@/components/ui/input"
import Link from "next/link"
import { formatDate } from "@/lib/utils"
import { createDemoMeeting } from "@/lib/demo-meeting"

// Mock data for development
const mockMeetings = [
  {
    id: "1",
    title: "Еженедельная встреча команды",
    date: "2023-05-15T10:00:00Z",
    participants: ["Иван Иванов", "Мария Петрова", "Алексей Сидоров"],
    status: "completed",
  },
  {
    id: "2",
    title: "Планирование продукта",
    date: "2023-05-18T14:30:00Z",
    participants: ["Мария Петрова", "Анна Кузнецова", "Дмитрий Волков"],
    status: "scheduled",
  },
  {
    id: "3",
    title: "Презентация для клиента",
    date: "2023-05-20T09:00:00Z",
    participants: ["Иван Иванов", "Алексей Сидоров", "Елена Смирнова"],
    status: "scheduled",
  },
]

interface MeetingsListProps {
  filter?: "all" | "recent" | "upcoming"
  realMeetings?: any[]
}

export default function MeetingsList({ filter = "all", realMeetings }: MeetingsListProps) {
  const [searchQuery, setSearchQuery] = useState("")

  let meetingsToShow = realMeetings !== undefined ? realMeetings : mockMeetings

  if (realMeetings !== undefined && realMeetings.length === 0) {
    const demoMeeting = createDemoMeeting()
    meetingsToShow = [
      {
        id: demoMeeting.meeting_id,
        title: demoMeeting.title,
        date: demoMeeting.created_at,
        participants: demoMeeting.speakers,
        status: "completed",
        isDemo: true,
      },
    ]
  }

  // Filter meetings based on the filter prop
  const filteredMeetings = meetingsToShow.filter((meeting) => {
    if (searchQuery && !meeting.title.toLowerCase().includes(searchQuery.toLowerCase())) {
      return false
    }

    if (filter === "recent") {
      return new Date(meeting.date) < new Date()
    }

    if (filter === "upcoming") {
      return new Date(meeting.date) > new Date()
    }

    return true
  })

  // Translate meeting status
  const getStatusTranslation = (status: string) => {
    switch (status) {
      case "completed":
        return "Завершена"
      case "scheduled":
        return "Запланирована"
      case "in-progress":
        return "В процессе"
      case "cancelled":
        return "Отменена"
      default:
        return status
    }
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div>
          <CardTitle>Встречи</CardTitle>
          {realMeetings !== undefined && realMeetings.length === 0 && (
            <p className="text-sm text-blue-600 mt-1">Демонстрационная встреча - показывает как работает сервис</p>
          )}
        </div>
        <div className="relative w-full max-w-sm">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            type="search"
            placeholder="Поиск встреч..."
            className="w-full pl-8"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid gap-4 md:gap-6">
          {filteredMeetings.length === 0 ? (
            <div className="py-6 text-center">
              <p className="text-muted-foreground">Встречи не найдены</p>
            </div>
          ) : (
            filteredMeetings.map((meeting) => (
              <div
                key={meeting.id}
                className="flex flex-col gap-3 rounded-lg border p-3 md:p-4 hover:shadow-md transition-shadow"
              >
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <h3 className="font-medium text-sm md:text-base line-clamp-2">{meeting.title}</h3>
                    {meeting.isDemo && (
                      <Badge variant="outline" className="text-xs bg-blue-50 text-blue-700 border-blue-200">
                        Демо
                      </Badge>
                    )}
                  </div>
                  <div className="flex flex-col gap-1 text-xs md:text-sm text-muted-foreground">
                    <div className="flex items-center gap-1">
                      <Calendar className="h-3 w-3 md:h-4 md:w-4 flex-shrink-0" />
                      <span className="truncate">{formatDate(meeting.date)}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <User className="h-3 w-3 md:h-4 md:w-4 flex-shrink-0" />
                      <span className="truncate">{meeting.participants.length} участников</span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center justify-between gap-2">
                  <Badge variant={meeting.status === "completed" ? "default" : "secondary"} className="text-xs">
                    {getStatusTranslation(meeting.status)}
                  </Badge>
                  <Button variant="outline" size="sm" asChild className="text-xs px-2 py-1 h-7 bg-transparent">
                    <Link href={`/meetings/${meeting.id}`}>Подробнее</Link>
                  </Button>
                </div>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  )
}
