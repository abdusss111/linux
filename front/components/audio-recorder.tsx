"use client"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Mic, MicOff, Square, Play, Pause, Upload, Loader2, AlertTriangle } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

interface AudioRecorderProps {
  onRecordingComplete?: (audioBlob: Blob, title: string) => void
}

export function AudioRecorder({ onRecordingComplete }: AudioRecorderProps) {
  const [isRecording, setIsRecording] = useState(false)
  const [isPaused, setIsPaused] = useState(false)
  const [recordedAudio, setRecordedAudio] = useState<Blob | null>(null)
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const [recordingDuration, setRecordingDuration] = useState(0)
  const [meetingTitle, setMeetingTitle] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [isUploading, setIsUploading] = useState(false)

  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const timerRef = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current)
      }
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl)
      }
    }
  }, [audioUrl])

  const formatTime = (seconds: number) => {
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    return `${minutes.toString().padStart(2, "0")}:${remainingSeconds.toString().padStart(2, "0")}`
  }

  const startRecording = async () => {
    try {
      setError(null)
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      
      const mediaRecorder = new MediaRecorder(stream)
      mediaRecorderRef.current = mediaRecorder
      audioChunksRef.current = []

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data)
        }
      }

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" })
        setRecordedAudio(audioBlob)
        const url = URL.createObjectURL(audioBlob)
        setAudioUrl(url)
        stream.getTracks().forEach(track => track.stop())
      }

      mediaRecorder.start(1000) // Collect data every second
      setIsRecording(true)
      setRecordingDuration(0)

      // Start timer
      timerRef.current = setInterval(() => {
        setRecordingDuration(prev => prev + 1)
      }, 1000)

    } catch (err) {
      setError("Не удалось получить доступ к микрофону. Проверьте разрешения браузера.")
      console.error("Error accessing microphone:", err)
    }
  }

  const pauseRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      if (isPaused) {
        mediaRecorderRef.current.resume()
      } else {
        mediaRecorderRef.current.pause()
      }
      setIsPaused(!isPaused)
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
      setIsPaused(false)
      if (timerRef.current) {
        clearInterval(timerRef.current)
      }
    }
  }

  const playRecording = () => {
    if (audioUrl) {
      if (audioRef.current) {
        audioRef.current.play()
        setIsPlaying(true)
      }
    }
  }

  const pausePlayback = () => {
    if (audioRef.current) {
      audioRef.current.pause()
      setIsPlaying(false)
    }
  }

  const resetRecording = () => {
    setRecordedAudio(null)
    setAudioUrl(null)
    setIsRecording(false)
    setIsPaused(false)
    setRecordingDuration(0)
    setMeetingTitle("")
    setError(null)
    if (timerRef.current) {
      clearInterval(timerRef.current)
    }
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl)
      setAudioUrl(null)
    }
  }

  const uploadRecording = async () => {
    if (!recordedAudio) return

    setIsUploading(true)
    setError(null)

    try {
      const token = localStorage.getItem("APP_JWT")
      if (!token) {
        throw new Error("Нет токена авторизации (войдите снова)")
      }

      const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://api.dapmeet.kz"
      
      const generateMeetingId = () => {
        if (typeof crypto !== 'undefined' && (crypto as any).randomUUID) {
          return (crypto as any).randomUUID()
        }
        return `m_${Date.now().toString(36)}_${Math.random().toString(36).slice(2,8)}`
      }

      const meetingId = generateMeetingId()
      const formData = new FormData()
      formData.append('file', recordedAudio, 'recording.webm')
      formData.append('response_format', 'json')
      formData.append('with_segments', 'true')

      const params = new URLSearchParams({
        meeting_id: meetingId,
        meeting_title: meetingTitle || 'Business Meeting Recording',
        with_segments: 'true',
        store: 'true'
      })

      const response = await fetch(`${API_URL}/api/whisper/transcribe?${params.toString()}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      })

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`Ошибка ${response.status}: ${errorText}`)
      }

      const meeting = await response.json()
      
      if (onRecordingComplete) {
        onRecordingComplete(recordedAudio, meetingTitle)
      }

      // Reset after successful upload
      resetRecording()
      
      // You could also show a success message or redirect
      alert("Запись успешно отправлена на транскрибацию!")

    } catch (err: any) {
      setError(err.message || "Ошибка при отправке записи")
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <div className="space-y-6 flex flex-col h-full">
      <div className="flex items-center gap-2">
        <Mic className="w-5 h-5" />
        <h2 className="text-xl font-semibold">Запись оффлайн встречи</h2>
      </div>
      
      <div className="space-y-4 flex-1 flex flex-col">
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-red-600 mt-0.5 flex-shrink-0" />
              <div>
                <h3 className="font-semibold text-red-800 mb-1">Ошибка</h3>
                <p className="text-red-700 text-sm">{error}</p>
              </div>
            </div>
          </div>
        )}

        <div className="space-y-4 flex-1 flex flex-col">
          <div>
            <Label htmlFor="meeting-title">Название встречи</Label>
            <Input
              id="meeting-title"
              placeholder="Введите название встречи"
              value={meetingTitle}
              onChange={(e) => setMeetingTitle(e.target.value)}
              className="mt-1"
            />
          </div>

          <div className="flex items-center justify-center flex-1">
            <div className="text-center space-y-4">
              {!isRecording && !recordedAudio && (
                <div className="space-y-2">
                  <div className="text-6xl text-red-500 mb-4">
                    <Mic className="w-16 h-16 mx-auto" />
                  </div>
                  <Button onClick={startRecording} size="lg" className="bg-red-600 hover:bg-red-700">
                    <Mic className="w-4 h-4 mr-2" />
                    Начать запись
                  </Button>
                </div>
              )}

              {isRecording && (
                <div className="space-y-4">
                  <div className="text-center">
                    <div className="text-6xl text-red-500 mb-2">
                      <div className="w-16 h-16 mx-auto rounded-full bg-red-500 animate-pulse flex items-center justify-center">
                        <MicOff className="w-8 h-8 text-white" />
                      </div>
                    </div>
                    <div className="text-2xl font-mono font-bold text-red-600">
                      {formatTime(recordingDuration)}
                    </div>
                    <p className="text-sm text-gray-600 mt-1">Идёт запись...</p>
                  </div>
                  <div className="flex gap-3 justify-center">
                    <Button 
                      onClick={pauseRecording} 
                      variant="outline"
                      className="bg-yellow-50 border-yellow-300 hover:bg-yellow-100"
                    >
                      {isPaused ? <Play className="w-4 h-4 mr-2" /> : <Pause className="w-4 h-4 mr-2" />}
                      {isPaused ? "Продолжить" : "Пауза"}
                    </Button>
                    <Button onClick={stopRecording} variant="destructive">
                      <Square className="w-4 h-4 mr-2" />
                      Остановить
                    </Button>
                  </div>
                </div>
              )}

              {recordedAudio && !isRecording && (
                <div className="space-y-4">
                  <div className="text-center">
                    <div className="text-6xl text-green-500 mb-2">
                      <Mic className="w-16 h-16 mx-auto" />
                    </div>
                    <div className="text-lg font-semibold text-gray-800">
                      Запись завершена
                    </div>
                    <div className="text-sm text-gray-600">
                      Длительность: {formatTime(recordingDuration)}
                    </div>
                  </div>

                  <div className="flex gap-3 justify-center">
                    <Button 
                      onClick={isPlaying ? pausePlayback : playRecording}
                      variant="outline"
                      className="bg-blue-50 border-blue-300 hover:bg-blue-100"
                    >
                      {isPlaying ? <Pause className="w-4 h-4 mr-2" /> : <Play className="w-4 h-4 mr-2" />}
                      {isPlaying ? "Пауза" : "Прослушать"}
                    </Button>
                    <Button onClick={resetRecording} variant="outline">
                      <Mic className="w-4 h-4 mr-2" />
                      Новая запись
                    </Button>
                  </div>

                  <div className="pt-4">
                    <Button 
                      onClick={uploadRecording} 
                      disabled={isUploading || !meetingTitle.trim()}
                      className="w-full bg-green-600 hover:bg-green-700"
                    >
                      {isUploading ? (
                        <>
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                          Отправка...
                        </>
                      ) : (
                        <>
                          <Upload className="w-4 h-4 mr-2" />
                          Отправить на транскрибацию
                        </>
                      )}
                    </Button>
                    {!meetingTitle.trim() && (
                      <p className="text-xs text-red-600 mt-2 text-center">
                        Введите название встречи для отправки
                      </p>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Hidden audio element for playback */}
          {audioUrl && (
            <audio
              ref={audioRef}
              src={audioUrl}
              onEnded={() => setIsPlaying(false)}
              className="hidden"
            />
          )}
        </div>
      </div>
    </div>
  )
}
