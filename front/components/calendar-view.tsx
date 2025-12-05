"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Calendar } from "@/components/ui/calendar"
import { ru } from "date-fns/locale"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Plus } from "lucide-react"
import Link from "next/link"

// Мок-данные для встреч
const mockMeetings = [
  {
    id: "1",
    title: "Еженедельная встреча команды",
    date: new Date(2023, 4, 15, 10, 0),
    participants: ["Иван Иванов", "Мария Петрова", "Алексей Сидоров"],
    status: "completed",
  },
  {
    id: "2",
    title: "Планирование продукта",
    date: new Date(2023, 4, 18, 14, 30),
    participants: ["Мария Петрова", "Анна Кузнецова", "Дмитрий Волков"],
    status: "scheduled",
  },
  {
    id: "3",
    title: "Презентация для клиента",
    date: new Date(2023, 4, 20, 9, 0),
    participants: ["Иван Иванов", "Алексей Сидоров", "Елена Смирнова"],
    status: "scheduled",
  },
  {
    id: "4",
    title: "Обзор спринта",
    date: new Date(2023, 4, 22, 11, 0),
    participants: ["Вся команда"],
    status: "scheduled",
  },
  {
    id: "5",
    title: "Ретроспектива",
    date: new Date(2023, 4, 22, 15, 0),
    participants: ["Вся команда"],
    status: "scheduled",
  },
]

export function CalendarView() {
  const [date, setDate] = useState<Date>(new Date())
  const [selectedDate, setSelectedDate] = useState<Date | undefined>(undefined)

  // Получить встречи для выбранной даты
  const getSelectedDateMeetings = () => {
    if (!selectedDate) return []

    return mockMeetings.filter((meeting) => {
      const meetingDate = new Date(meeting.date)
      return (
        meetingDate.getDate() === selectedDate.getDate() &&
        meetingDate.getMonth() === selectedDate.getMonth() &&
        meetingDate.getFullYear() === selectedDate.getFullYear()
      )
    })
  }

  // Получить даты, на которые запланированы встречи
  const meetingDates = mockMeetings.map((meeting) => {
    const date = new Date(meeting.date)
    return new Date(date.getFullYear(), date.getMonth(), date.getDate())
  })

  // Форматировать время встречи
  const formatMeetingTime = (date: Date) => {
    return date.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })
  }

  // Получить статус встречи на русском
  const getStatusText = (status: string) => {
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

  const selectedDateMeetings = getSelectedDateMeetings()

  return (
    <div className="grid gap-6 md:grid-cols-3">
      <Card className="md:col-span-2">
        <CardHeader>
          <CardTitle>Календарь встреч</CardTitle>
          <CardDescription>Просмотр и планирование встреч</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex justify-center">
            <Calendar
              mode="single"
              selected={selectedDate}
              onSelect={setSelectedDate}
              locale={ru}
              className="rounded-md border"
              modifiers={{
                meeting: meetingDates,
              }}
              modifiersStyles={{
                meeting: { fontWeight: "bold", backgroundColor: "hsl(var(--primary) / 0.1)" },
              }}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <div>
            <CardTitle>
              {selectedDate ? selectedDate.toLocaleDateString("ru-RU", { day: "numeric", month: "long" }) : "Встречи"}
            </CardTitle>
            <CardDescription>
              {selectedDate ? `${selectedDateMeetings.length} встреч` : "Выберите дату для просмотра встреч"}
            </CardDescription>
          </div>
          <Button size="sm" className="gap-1">
            <Plus className="h-4 w-4" />
            Новая встреча
          </Button>
        </CardHeader>
        <CardContent>
          {!selectedDate ? (
            <div className="flex items-center justify-center h-[300px] text-muted-foreground">
              Выберите дату в календаре
            </div>
          ) : selectedDateMeetings.length === 0 ? (
            <div className="flex items-center justify-center h-[300px] text-muted-foreground">
              Нет встреч на выбранную дату
            </div>
          ) : (
            <div className="space-y-4">
              {selectedDateMeetings.map((meeting) => (
                <div key={meeting.id} className="rounded-lg border p-3">
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <h3 className="font-medium">{meeting.title}</h3>
                      <p className="text-sm text-muted-foreground">{formatMeetingTime(meeting.date)}</p>
                    </div>
                    <Badge variant={meeting.status === "completed" ? "default" : "secondary"}>
                      {getStatusText(meeting.status)}
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground mb-2">{meeting.participants.join(", ")}</p>
                  <Button variant="outline" size="sm" className="w-full" asChild>
                    <Link href={`/meetings/${meeting.id}`}>Подробнее</Link>
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
