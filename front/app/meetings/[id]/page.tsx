"use client"

import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { ArrowLeft } from "lucide-react"
import Link from "next/link"
import { DashboardLayout } from "@/components/dashboard-layout"
import { MeetingHeader } from "@/components/meeting-header"
import { MeetingControls } from "@/components/meeting-controls"
import { TranscriptView } from "@/components/transcript-view"
import { AIChat } from "@/components/ai-chat"
import type { Meeting } from "@/lib/types"
import { DEMO_MEETING } from "@/lib/demo-meeting"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://api.dapmeet.kz"

export default function MeetingDetailPage() {
  const params = useParams()
  const router = useRouter()
  const meetingId = params.id as string
  const [meeting, setMeeting] = useState<Meeting | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedSpeakers, setSelectedSpeakers] = useState<string[]>([])

  const handleSpeakerToggle = (speaker: string) => {
    setSelectedSpeakers((prev) => (prev.includes(speaker) ? prev.filter((s) => s !== speaker) : [...prev, speaker]))
  }

  useEffect(() => {
    const fetchMeeting = async () => {
      try {
        if (meetingId === DEMO_MEETING.meeting_id) {
          setMeeting(DEMO_MEETING)
          setLoading(false)
          return
        }

        // Check if we're on the client side
        if (typeof window === 'undefined') {
          setLoading(false)
          return
        }

        const token = localStorage.getItem("APP_JWT")
        if (!token) {
          setError("Токен авторизации не найден")
          return
        }

        const response = await fetch(`${API_URL}/api/meetings/${meetingId}`, {
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
        })

        if (!response.ok) {
          throw new Error(`Ошибка ${response.status}: ${response.statusText}`)
        }

        const data = await response.json()
        setMeeting(data)
      } catch (err) {
        console.error("Ошибка загрузки встречи:", err)
        setError(err instanceof Error ? err.message : "Неизвестная ошибка")
      } finally {
        setLoading(false)
      }
    }

    if (meetingId) {
      fetchMeeting()
    }
  }, [meetingId])

  const formatTranscript = (meeting: Meeting): string => {
    if (!meeting.segments || meeting.segments.length === 0) return ""

    const sortedSegments = [...meeting.segments].sort(
      (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
    )

    return sortedSegments
      .map((segment) => {
        const time = new Date(segment.timestamp).toLocaleTimeString("ru-RU", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        })
        return `${time}, ${segment.speaker_username}: ${segment.text}`
      })
      .join("\n")
  }

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600">Загрузка встречи...</p>
          </div>
        </div>
      </DashboardLayout>
    )
  }

  if (error) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="text-center">
            <p className="text-red-600 mb-4">{error}</p>
            <Link href="/meetings">
              <Button variant="outline">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Вернуться к встречам
              </Button>
            </Link>
          </div>
        </div>
      </DashboardLayout>
    )
  }

  if (!meeting) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="text-center">
            <p className="text-gray-600 mb-4">Встреча не найдена</p>
            <Link href="/meetings">
              <Button variant="outline">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Вернуться к встречам
              </Button>
            </Link>
          </div>
        </div>
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Navigation */}
        <div className="flex items-center gap-4">
          <Link href="/meetings">
            <Button variant="outline" size="sm">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Назад к встречам
            </Button>
          </Link>
        </div>

        {/* Content */}
        <div className="space-y-6">
          <MeetingHeader meeting={meeting} />

          <MeetingControls
            meeting={meeting}
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
            selectedSpeakers={selectedSpeakers}
            onSpeakerToggle={handleSpeakerToggle}
          />
          <TranscriptView meeting={meeting} searchQuery={searchQuery} selectedSpeakers={selectedSpeakers} />

          <AIChat
            sessionId={meeting.meeting_id}
            meetingTitle={meeting.title}
            meetingCreatedAt={meeting.created_at}
            speakers={meeting.speakers || []}
            transcript={formatTranscript(meeting)}
          />

         
        </div>
      </div>
    </DashboardLayout>
  )
}
