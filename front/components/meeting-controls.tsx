"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Search, Download, Filter, X } from "lucide-react"
import { exportTranscript } from "@/lib/meeting-utils"
import type { Meeting } from "@/lib/types"

interface MeetingControlsProps {
  meeting: Meeting
  searchQuery: string
  onSearchChange: (query: string) => void
  selectedSpeakers: string[]
  onSpeakerToggle: (speaker: string) => void
}

export function MeetingControls({
  meeting,
  searchQuery,
  onSearchChange,
  selectedSpeakers,
  onSpeakerToggle,
}: MeetingControlsProps) {
  const [showSpeakerFilter, setShowSpeakerFilter] = useState(false)
  // Используем speakers из API ответа вместо извлечения из segments
  const uniqueSpeakers = meeting.speakers || []

  const handleExport = () => {
    exportTranscript(meeting.segments, meeting.title)
  }

  const clearFilters = () => {
    onSearchChange("")
    selectedSpeakers.forEach((speaker) => onSpeakerToggle(speaker))
  }

  return (
    <Card className="bg-white border-gray-200">
      <CardHeader>
        <CardTitle className="text-lg">Найти реплику</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
          <Input
            placeholder="Поиск по тексту или имени участника..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="pl-10"
          />
        </div>

        {/* Controls */}
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowSpeakerFilter(!showSpeakerFilter)}
            className="gap-1"
          >
            <Filter className="w-4 h-4" />
            Фильтр участников
            {selectedSpeakers.length > 0 && (
              <Badge variant="secondary" className="ml-1">
                {selectedSpeakers.length}
              </Badge>
            )}
          </Button>

          <Button variant="outline" size="sm" onClick={handleExport} className="gap-1 bg-transparent">
            <Download className="w-4 h-4" />
            Экспорт реплик
          </Button>

          {(searchQuery || selectedSpeakers.length > 0) && (
            <Button
              variant="outline"
              size="sm"
              onClick={clearFilters}
              className="gap-1 text-red-600 hover:text-red-700 bg-transparent"
            >
              <X className="w-4 h-4" />
              Очистить фильтры
            </Button>
          )}
        </div>

        {/* Speaker Filter */}
        {showSpeakerFilter && (
          <div className="border-t pt-4">
            <div className="text-sm font-medium text-gray-700 mb-2">Выберите участников:</div>
            <div className="flex flex-wrap gap-2">
              {uniqueSpeakers.map((speaker) => (
                <Badge
                  key={speaker}
                  variant={selectedSpeakers.includes(speaker) ? "default" : "outline"}
                  className="cursor-pointer hover:bg-gray-100"
                  onClick={() => onSpeakerToggle(speaker)}
                >
                  {speaker}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Active Filters Display */}
        {(searchQuery || selectedSpeakers.length > 0) && (
          <div className="border-t pt-4">
            <div className="text-sm font-medium text-gray-700 mb-2">Активные фильтры:</div>
            <div className="flex flex-wrap gap-2">
              {searchQuery && (
                <Badge variant="secondary" className="gap-1">
                  Поиск: "{searchQuery}"
                  <X className="w-3 h-3 cursor-pointer hover:text-red-600" onClick={() => onSearchChange("")} />
                </Badge>
              )}
              {selectedSpeakers.map((speaker) => (
                <Badge key={speaker} variant="secondary" className="gap-1">
                  {speaker}
                  <X className="w-3 h-3 cursor-pointer hover:text-red-600" onClick={() => onSpeakerToggle(speaker)} />
                </Badge>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
