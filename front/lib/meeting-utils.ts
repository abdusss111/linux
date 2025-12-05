import type { MeetingSegment, ProcessedSegment } from "./types"

// Speaker colors for consistent UI
const SPEAKER_COLORS = [
  "bg-blue-100 text-blue-800",
  "bg-green-100 text-green-800",
  "bg-purple-100 text-purple-800",
  "bg-orange-100 text-orange-800",
  "bg-pink-100 text-pink-800",
  "bg-indigo-100 text-indigo-800",
  "bg-yellow-100 text-yellow-800",
  "bg-red-100 text-red-800",
]

export const formatTimestamp = (isoString: string): string => {
  const date = new Date(isoString)
  return date.toLocaleTimeString("ru-RU", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  })
}

export const formatDate = (isoString: string): string => {
  const date = new Date(isoString)
  return date.toLocaleDateString("ru-RU", {
    year: "numeric",
    month: "long",
    day: "numeric",
  })
}

export const formatDateTime = (dateString: string): string => {
  const date = new Date(dateString)
  return date.toLocaleDateString("ru-RU", {
    day: "numeric",
    month: "long",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

export const calculateDuration = (segments: MeetingSegment[]): string => {
  if (!segments || segments.length === 0) return "0:00"

  const sortedSegments = [...segments].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())

  const first = new Date(sortedSegments[0].timestamp)
  const last = new Date(sortedSegments[sortedSegments.length - 1].timestamp)
  const diffMs = last.getTime() - first.getTime()

  const minutes = Math.floor(diffMs / 60000)
  const seconds = Math.floor((diffMs % 60000) / 1000)

  return `${minutes}:${seconds.toString().padStart(2, "0")}`
}

export const getUniqueSpeakers = (segments: MeetingSegment[]): string[] => {
  if (!segments || !Array.isArray(segments) || segments.length === 0) {
    return []
  }
  
  const speakers = new Set<string>()
  segments.forEach((segment) => {
    if (segment && segment.speaker_username && typeof segment.speaker_username === 'string') {
      speakers.add(segment.speaker_username)
    }
  })
  return Array.from(speakers)
}

export const getSpeakerColor = (speaker: string, allSpeakers: string[]): string => {
  const index = allSpeakers.indexOf(speaker)
  return SPEAKER_COLORS[index % SPEAKER_COLORS.length]
}

export const processSegments = (segments: MeetingSegment[]): ProcessedSegment[] => {
  if (!segments || segments.length === 0) return []

  // Если все сегменты от "модели" и один спикер — НЕ группируем (важно для загруженного транскриба)
  const singleSpeaker = new Set(segments.map(s => s.speaker_username)).size === 1
  const allModel = segments.every(s => (s.google_meet_user_id === 'model') || s.speaker_username === 'Model')
  const disableGrouping = singleSpeaker && allModel

  const allSpeakers = getUniqueSpeakers(segments)
  const processed: ProcessedSegment[] = []

  for (let i = 0; i < segments.length; i++) {
    const segment = segments[i]
    const prev = segments[i - 1]

    const timeDiff = prev ? (new Date(segment.timestamp).getTime() - new Date(prev.timestamp).getTime()) : Infinity
    const shouldGroup = !disableGrouping && !!prev && prev.speaker_username === segment.speaker_username && timeDiff < 120000 // 2 минуты

    if (shouldGroup && processed.length > 0) {
      const last = processed[processed.length - 1]
      last.groupedMessages.push(segment.text)
    } else {
      processed.push({
        ...segment,
        groupedMessages: [segment.text],
        isFirstInGroup: true,
        speakerColor: getSpeakerColor(segment.speaker_username, allSpeakers),
      })
    }
  }

  return processed
}

export const searchInTranscript = (segments: MeetingSegment[], query: string): MeetingSegment[] => {
  const q = query.trim()
  if (!q) return segments

  const lower = q.toLowerCase()
  // Фильтрация с сохранением исходного порядка
  return segments.filter(
    (s) =>
      s.text.toLowerCase().includes(lower) ||
      s.speaker_username.toLowerCase().includes(lower)
  )
}

export const exportTranscript = (segments: MeetingSegment[], title: string): void => {
  const sortedSegments = [...segments].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())

  const content = sortedSegments
    .map((segment) => {
      const time = formatTimestamp(segment.timestamp)
      return `${time} - ${segment.speaker_username}: ${segment.text}`
    })
    .join("\n")

  const blob = new Blob([content], { type: "text/plain" })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = `${title}_transcript.txt`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
