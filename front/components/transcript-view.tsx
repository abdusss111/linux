"use client"

import { useMemo } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Separator } from "@/components/ui/separator"
import { MessageSquare, Clock } from 'lucide-react'
import { processSegments, formatTimestamp, searchInTranscript } from "@/lib/meeting-utils"
import type { Meeting } from "@/lib/types"

interface TranscriptViewProps {
  meeting: Meeting
  searchQuery: string
  selectedSpeakers: string[]
}

export function TranscriptView({ meeting, searchQuery, selectedSpeakers }: TranscriptViewProps) {
  // ВАЖНО: порядок сегментов сохраняется как пришёл из API.
  // searchInTranscript и processSegments НЕ сортируют массив.
  const filteredAndProcessedSegments = useMemo(() => {
    let segments = meeting.segments

    // Apply search filter
    if (searchQuery.trim()) {
      segments = searchInTranscript(segments, searchQuery)
    }

    // Apply speaker filter
    if (selectedSpeakers.length > 0) {
      segments = segments.filter((segment) => selectedSpeakers.includes(segment.speaker_username))
    }

    return processSegments(segments)
  }, [meeting.segments, searchQuery, selectedSpeakers])

  const highlightText = (text: string, query: string): string => {
    if (!query.trim()) return text

    const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "gi")
    return text.replace(regex, '<mark class="bg-yellow-200 px-1 rounded">$1</mark>')
  }

  if (filteredAndProcessedSegments.length === 0) {
    return (
      <Card className="bg-white border-gray-200">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageSquare className="w-5 h-5" />
            Транскрипт встречи
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12">
            <MessageSquare className="w-12 h-12 mx-auto mb-4 text-gray-300" />
            <p className="text-gray-500">
              {searchQuery || selectedSpeakers.length > 0
                ? "Ничего не найдено по вашему запросу"
                : "Транскрипт для этой встречи недоступен"}
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="bg-white border-gray-200">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <MessageSquare className="w-5 h-5" />
          Транскрипт
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-6 max-h-[600px] overflow-y-auto pr-2">
          {filteredAndProcessedSegments.map((segment, index) => (
            <div key={segment.id} className="group">
              <div className="flex items-start gap-3">
                {/* Speaker Avatar */}
                <Avatar className="w-8 h-8 flex-shrink-0">
                  <AvatarFallback className={`text-xs font-medium ${segment.speakerColor}`}>
                    {segment.speaker_username
                      .split(" ")
                      .map((n) => n[0])
                      .join("")
                      .slice(0, 2)
                      .toUpperCase()}
                  </AvatarFallback>
                </Avatar>

                {/* Message Content */}
                <div className="flex-1 min-w-0">
                  {/* Speaker and Timestamp */}
                  <div className="flex items-center gap-2 mb-2">
                    <span className="font-medium text-gray-900">{segment.speaker_username}</span>
                    <div className="flex items-center gap-1 text-xs text-gray-500">
                      {formatTimestamp(segment.timestamp)}
                    </div>
                  </div>

                  {/* Messages */}
                  <div className="space-y-2">
                    {segment.groupedMessages.map((message, msgIndex) => (
                      <div
                        key={msgIndex}
                        className="text-gray-700 leading-relaxed"
                        dangerouslySetInnerHTML={{
                          __html: highlightText(message, searchQuery),
                        }}
                      />
                    ))}
                  </div>

                  {/* Metadata (hidden by default, shown on hover) */}
                  <div className="mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <div className="text-xs text-gray-400">
                      <span>Создано: {formatTimestamp(segment.created_at)}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Separator */}
              {index < filteredAndProcessedSegments.length - 1 && <Separator className="mt-6" />}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
