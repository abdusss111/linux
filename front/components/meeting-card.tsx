"use client"

import Link from "next/link"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Calendar, Clock, Users, Trash2 } from "lucide-react"
import { formatDate, formatTimestamp } from "@/lib/meeting-utils"
import { useAuth } from "@/hooks/use-auth"
import type { Meeting } from "@/lib/types"

interface MeetingCardProps {
  meeting: Meeting
  onDelete?: (meeting: Meeting) => void
}

// Function to properly decline the word "участник" in Russian
function getParticipantWord(count: number): string {
  // Handle special cases for 11-19 (always "участников")
  if (count >= 11 && count <= 19) {
    return "участников"
  }

  // Get the last digit
  const lastDigit = count % 10

  if (lastDigit === 1) {
    return "участник"
  } else if (lastDigit >= 2 && lastDigit <= 4) {
    return "участника"
  } else {
    return "участников"
  }
}

export function MeetingCard({ meeting, onDelete }: MeetingCardProps) {
  const { user } = useAuth()

  // Get all speakers from the meeting
  const allSpeakers = meeting.speakers || []

  // Filter out current user from speakers list for display
  const otherSpeakers = allSpeakers.filter((speaker) => speaker !== user?.name)

  // Calculate total speakers count - ensure current user is always counted if they have access to this meeting
  // If meeting.speakers is empty or doesn't include current user, assume current user is still a participant
  let totalSpeakersCount = allSpeakers.length

  // If speakers list doesn't include current user but user has access to meeting, add them to count
  if (user?.name && !allSpeakers.includes(user.name)) {
    totalSpeakersCount = Math.max(1, allSpeakers.length + 1)
  }

  // Ensure minimum count is 1 if user has access to the meeting
  if (totalSpeakersCount === 0) {
    totalSpeakersCount = 1
  }

  // Create speakers text in format "Вы и [other speakers]"
  const speakersText = otherSpeakers.length > 0 ? `Вы и ${otherSpeakers.join(", ")}` : "Только вы"

  // Get properly declined word for participants
  const participantWord = getParticipantWord(totalSpeakersCount)

  // Check if this is a demo meeting (no real meeting_id)
  const isDemoMeeting = !meeting.meeting_id || meeting.meeting_id.startsWith('demo_')

  const handleDeleteClick = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (onDelete && !isDemoMeeting) {
      onDelete(meeting)
    }
  }

  return (
    <div className="relative group">
      <Link href={`/meetings/${meeting.meeting_id || meeting.id}`}>
        <Card className="hover:shadow-md transition-shadow cursor-pointer bg-white border-gray-200">
          <CardHeader className="pb-2 md:pb-3">
            <div className="flex items-start justify-between">
              <CardTitle className="text-sm md:text-lg font-semibold text-gray-900 line-clamp-2 pr-2">
                {meeting.title || "Без названия"}
              </CardTitle>
              {onDelete && !isDemoMeeting && (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={handleDeleteClick}
                  className="opacity-0 group-hover:opacity-100 transition-opacity h-8 w-8 text-red-500 hover:text-red-700 hover:bg-red-50"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              )}
            </div>
          </CardHeader>
        <CardContent className="pt-0 space-y-1.5 md:space-y-2">
          <div className="flex items-center text-xs md:text-sm text-gray-600">
            <Calendar className="w-3 h-3 md:w-4 md:h-4 mr-1.5 md:mr-2 flex-shrink-0" />
            <span className="truncate">{meeting.created_at ? formatDate(meeting.created_at) : "Дата не указана"}</span>
          </div>
          <div className="flex items-center text-xs md:text-sm text-gray-600">
            <Clock className="w-3 h-3 md:w-4 md:h-4 mr-1.5 md:mr-2 flex-shrink-0" />
            <span className="truncate">{meeting.created_at ? formatTimestamp(meeting.created_at) : "--:--"}</span>
          </div>
          <div className="flex items-start text-xs md:text-sm text-gray-600">
            <Users className="w-3 h-3 md:w-4 md:h-4 mr-1.5 md:mr-2 flex-shrink-0 mt-0.5" />
            <div className="min-w-0 flex-1">
              <div className="truncate">
                <span className="font-medium">
                  {totalSpeakersCount} {participantWord}
                </span>
                <span className="hidden sm:inline">: {speakersText}</span>
                <span className="sm:hidden">
                  :{" "}
                  {otherSpeakers.length > 0
                    ? `Вы и ${otherSpeakers[0]}${otherSpeakers.length > 1 ? ` и еще ${otherSpeakers.length - 1}` : ""}`
                    : "Только вы"}
                </span>
              </div>
            </div>
          </div>
        </CardContent>
        </Card>
      </Link>
    </div>
  )
}

export default MeetingCard
