"use client"

import { CardContent } from "@/components/ui/card"
import { CardDescription } from "@/components/ui/card"
import { CardTitle } from "@/components/ui/card"
import { CardHeader } from "@/components/ui/card"
import { Card } from "@/components/ui/card"
import { useEffect, useState } from "react"
import DashboardLayout from "@/components/dashboard-layout"
import { MeetingCard } from "@/components/meeting-card"
import { createDemoMeeting } from "@/lib/demo-meeting"
import type { Meeting } from "@/lib/types"
import { Button } from "@/components/ui/button"
import { ConfirmationDialog } from "@/components/ui/confirmation-dialog"

export default function MeetingsPage() {
  const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://api.dapmeet.kz"
  const [meetings, setMeetings] = useState<Meeting[]>([])
  const [loading, setLoading] = useState(true)
  // Delete meeting state
  const [deleteDialog, setDeleteDialog] = useState<{
    isOpen: boolean
    meeting: Meeting | null
  }>({ isOpen: false, meeting: null })
  const [deleting, setDeleting] = useState(false)


  const fetchMeetings = async () => {
      try {
        // Check if we're on the client side
        if (typeof window === 'undefined') {
          setLoading(false)
          return
        }

        const token = localStorage.getItem("APP_JWT")
        if (!token) {
          setMeetings([])
          setLoading(false)
          return
        }

        const res = await fetch(`${API_URL}/api/meetings/`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        })

        if (!res.ok) throw new Error("Failed to fetch meetings")

        const data = await res.json()
        const normalized = Array.isArray(data)
          ? data
          : Array.isArray((data as any)?.results)
            ? (data as any).results
            : Array.isArray((data as any)?.meetings)
              ? (data as any).meetings
              : []
        setMeetings(normalized as Meeting[])
      } catch (err) {
        console.error(err)
        setMeetings([])
      } finally {
        setLoading(false)
      }
    }

  const handleDeleteMeeting = async () => {
    if (!deleteDialog.meeting) return

    setDeleting(true)
    try {
      // Check if we're on the client side
      if (typeof window === 'undefined') {
        throw new Error("Недоступно на сервере")
      }

      const token = localStorage.getItem("APP_JWT")
      if (!token) {
        throw new Error("Нет токена авторизации")
      }

      const meetingId = deleteDialog.meeting.meeting_id
      const res = await fetch(`${API_URL}/api/meetings/${meetingId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      if (!res.ok) {
        const text = await res.text()
        throw new Error(`Ошибка ${res.status}: ${text}`)
      }

      // Remove meeting from local state
      setMeetings(prev => prev.filter(m => m.meeting_id !== meetingId))
      setDeleteDialog({ isOpen: false, meeting: null })
    } catch (error: any) {
      console.error("Error deleting meeting:", error)
      alert(error.message || "Ошибка при удалении встречи")
    } finally {
      setDeleting(false)
    }
  }

  const openDeleteDialog = (meeting: Meeting) => {
    setDeleteDialog({ isOpen: true, meeting })
  }

  const closeDeleteDialog = () => {
    if (!deleting) {
      setDeleteDialog({ isOpen: false, meeting: null })
    }
  }

  useEffect(() => {
    fetchMeetings()
  }, [])

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex flex-col md:flex-row justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Просмотр и управление встречами</h1>
            {meetings.length === 0 && !loading && (
              <div className="mt-2 space-y-2">
                <p className="text-lg text-gray-700">
                  Для работы с сервисом требуется установка расширения в браузере Google Chrome с компьютера
                </p>
                <Button asChild size="sm" className="w-fit">
                  <a
                    href="https://chromewebstore.google.com/detail/dapmeet/lldjmemepbogdgfdeeodbipoggpbkcgg?utm_source=item-share-cb"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Установить расширение
                  </a>
                </Button>
              </div>
            )}
          </div>
        </div>

        <div className="grid gap-6">
          <MeetingsList meetings={meetings} loading={loading} onDeleteMeeting={openDeleteDialog} />
        </div>

        {/* Delete Confirmation Dialog */}
        <ConfirmationDialog
          isOpen={deleteDialog.isOpen}
          onClose={closeDeleteDialog}
          onConfirm={handleDeleteMeeting}
          title="Удалить встречу"
          message={`Вы уверены, что хотите удалить встречу "${deleteDialog.meeting?.title || "Без названия"}"? Это действие нельзя отменить.`}
          confirmText="Удалить"
          cancelText="Отмена"
          isLoading={deleting}
          variant="destructive"
        />
      </div>
    </DashboardLayout>
  )
}

function MeetingsList({ meetings, loading, onDeleteMeeting }: { meetings: Meeting[]; loading: boolean; onDeleteMeeting: (meeting: Meeting) => void }) {
  const safeMeetings = Array.isArray(meetings) ? meetings : []
  const displayMeetings = safeMeetings.length === 0 && !loading ? [createDemoMeeting()] : safeMeetings

  // const processingSet = useMemo(() => new Set(Object.values(opsMap)), [opsMap])

  return (
    <div className="space-y-4">
      {loading ? (
        <p className="text-muted-foreground">Загрузка встреч...</p>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>Встречи</CardTitle>
            {meetings.length === 0 && !loading && (
              <CardDescription className="text-blue-600">
                Демонстрационная встреча - показывает как работает сервис
              </CardDescription>
            )}
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {displayMeetings.length === 0 ? (
                <p className="text-muted-foreground">Нет встреч</p>
              ) : (
                displayMeetings.map((meeting) => <MeetingCard key={meeting.meeting_id || meeting.unique_session_id} meeting={meeting} onDelete={onDeleteMeeting} />)
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
