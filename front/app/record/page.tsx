"use client"

import { useState, useRef } from "react"
import DashboardLayout from "@/components/dashboard-layout"
import { AudioRecorder } from "@/components/audio-recorder"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Upload, FileAudio2, X, Loader2, Mic, Upload as UploadIcon } from "lucide-react"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

type Mode = "record" | "upload"

export default function RecordPage() {
  const router = useRouter()
  const [mode, setMode] = useState<Mode>("record")
  const [file, setFile] = useState<File | null>(null)
  const [meetingTitle, setMeetingTitle] = useState("")
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement | null>(null)
  
  const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://api.dapmeet.kz"

  const handleRecordingComplete = (audioBlob: Blob, title: string) => {
    // Optional: Redirect to meetings page after successful upload
    // router.push("/meetings")
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (!f) return
    if (f.size > 25 * 1024 * 1024) {
      setUploadError("Файл больше 25MB лимита")
      return
    }
    setUploadError(null)
    // Use filename as title automatically
    const titleFromFilename = f.name.replace(/\.[^.]+$/, "")
    setMeetingTitle(titleFromFilename)
    setFile(f)
  }

  const resetUpload = () => {
    setFile(null)
    setUploadError(null)
    setMeetingTitle("")
    if (inputRef.current) inputRef.current.value = ""
  }

  const generateMeetingId = () => {
    if (typeof crypto !== 'undefined' && (crypto as any).randomUUID) {
      return (crypto as any).randomUUID()
    }
    return `m_${Date.now().toString(36)}_${Math.random().toString(36).slice(2,8)}`
  }

  const submitUpload = async () => {
    if (!file) {
      setUploadError("Выберите аудио файл")
      return
    }
    const meetingId = generateMeetingId()
    setUploading(true)
    setUploadError(null)
    try {
      if (typeof window === 'undefined') {
        setUploadError("Недоступно на сервере")
        setUploading(false)
        return
      }

      const token = localStorage.getItem("APP_JWT")
      if (!token) {
        setUploadError("Нет токена авторизации (войдите снова)")
        setUploading(false)
        return
      }
      
      const form = new FormData()
      form.append("file", file)
      form.append("response_format", "json")
      form.append("with_segments", "true")

      const params = new URLSearchParams({
        meeting_id: meetingId,
        meeting_title: meetingTitle || file.name.replace(/\.[^.]+$/, ""),
        with_segments: 'true',
        store: 'true'
      })

      const res = await fetch(`${API_URL}/api/whisper/transcribe?${params.toString()}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      })
      
      if (!res.ok) {
        const text = await res.text()
        throw new Error(`Ошибка ${res.status}: ${text}`)
      }
      
      const data = await res.json()
      
      // Reset after successful upload
      resetUpload()
      alert("Аудио успешно отправлено на транскрибацию!")
      
    } catch (e: any) {
      setUploadError(e.message || "Ошибка запроса")
    } finally {
      setUploading(false)
      setFile(null)
    }
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Оффлайн встречи</h1>
          <p className="text-lg text-gray-700 mt-2">
            Записывайте встречи с помощью микрофона или загружайте аудио файлы
          </p>
        </div>

        {/* Mode Tabs */}
        <div className="flex gap-2 border-b border-gray-200">
          <button
            onClick={() => {
              setMode("record")
              resetUpload()
            }}
            className={`flex items-center gap-2 px-4 py-3 font-medium transition-colors border-b-2 ${
              mode === "record"
                ? "border-red-600 text-red-600"
                : "border-transparent text-gray-600 hover:text-gray-900"
            }`}
          >
            <Mic className="w-4 h-4" />
            Записать
          </button>
          <button
            onClick={() => {
              setMode("upload")
              resetUpload()
            }}
            className={`flex items-center gap-2 px-4 py-3 font-medium transition-colors border-b-2 ${
              mode === "upload"
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-gray-600 hover:text-gray-900"
            }`}
          >
            <UploadIcon className="w-4 h-4" />
            Загрузить
          </button>
        </div>

        {/* Main Content Card */}
        <Card className="w-full max-w-4xl mx-auto">
          <div className="p-6">
            <div className="transition-opacity duration-300">
              {mode === "record" ? (
                <div className="space-y-6">
                  <AudioRecorder onRecordingComplete={handleRecordingComplete} />
                </div>
              ) : (
                <div className="space-y-6">
                  <div className="flex items-center gap-2 mb-2">
                    <Upload className="w-5 h-5 text-blue-600" />
                    <h2 className="text-xl font-semibold">Загрузить аудио</h2>
                  </div>

                  <input
                    ref={inputRef}
                    type="file"
                    accept="audio/*"
                    className="hidden"
                    onChange={handleFileChange}
                  />

                  {uploadError && (
                    <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                      <p className="text-sm text-red-700">{uploadError}</p>
                    </div>
                  )}

                  {!file && !uploading && (
                    <div className="flex-1 flex flex-col justify-center space-y-4 py-8">
                      <div className="text-center">
                        <div className="text-6xl text-blue-500 mb-4">
                          <Upload className="w-16 h-16 mx-auto" />
                        </div>
                      </div>

                      <Button 
                        onClick={() => inputRef.current?.click()} 
                        className="w-full bg-blue-600 hover:bg-blue-700"
                        size="lg"
                      >
                        <Upload className="w-4 h-4 mr-2" />
                        Выбрать файл
                      </Button>
                    </div>
                  )}

                  {file && !uploading && (
                    <div className="flex-1 flex flex-col justify-center space-y-4">
                      <div className="flex items-center gap-3 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2">
                        <FileAudio2 className="w-5 h-5 text-blue-600" />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-gray-900 truncate">{file.name}</p>
                          <p className="text-xs text-gray-500">{(file.size / 1024 / 1024).toFixed(1)} MB</p>
                        </div>
                        <Button 
                          size="icon" 
                          variant="ghost" 
                          className="h-8 w-8" 
                          onClick={resetUpload}
                        >
                          <X className="w-4 h-4" />
                        </Button>
                      </div>

                      <div className="space-y-2">
                        <Button 
                          onClick={submitUpload} 
                          disabled={!meetingTitle.trim()}
                          className="w-full bg-green-600 hover:bg-green-700"
                          size="lg"
                        >
                          <Upload className="w-4 h-4 mr-2" />
                          Отправить на транскрибацию
                        </Button>
                        <Button 
                          onClick={() => inputRef.current?.click()}
                          variant="outline"
                          className="w-full"
                        >
                          Сменить файл
                        </Button>
                      </div>
                    </div>
                  )}

                  {uploading && (
                    <div className="flex items-center justify-center py-8">
                      <div className="text-center space-y-2">
                        <Loader2 className="w-12 h-12 animate-spin text-blue-600 mx-auto" />
                        <p className="text-sm text-gray-600">Идёт транскрибация...</p>
                        <p className="text-xs text-gray-500">Это может занять несколько минут</p>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </Card>

        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h3 className="font-semibold text-blue-800 mb-2">Инструкции по использованию</h3>
          <div className="text-blue-700 text-sm space-y-1">
            <p className="mb-2"><strong>Режим "Записать":</strong></p>
            <ul className="list-disc list-inside space-y-1">
              <li>Введите название встречи (обязательно) перед началом записи</li>
              <li>Нажмите "Начать запись" и разрешите доступ к микрофону</li>
              <li>Вы можете поставить запись на паузу или остановить её в любой момент</li>
              <li>После завершения записи можете прослушать результат</li>
            </ul>
            <p className="mb-2 mt-4"><strong>Режим "Загрузить":</strong></p>
            <ul className="list-disc list-inside space-y-1">
              <li>Нажмите "Выбрать файл" и выберите аудио файл (до 25MB)</li>
              <li>Название встречи будет автоматически заполнено именем файла</li>
              <li>Вы можете изменить название перед отправкой</li>
              <li>Нажмите "Отправить на транскрибацию" для обработки</li>
            </ul>
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}