"use client"

import { useState, useRef } from "react"
import { DashboardLayout } from "@/components/dashboard-layout"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Separator } from "@/components/ui/separator"
import { Loader2, Upload, FileAudio2, Copy, Download, RefreshCcw, List, Wand2 } from "lucide-react"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://api.dapmeet.kz"

interface SimpleSegment {
  index: number
  start: number
  end: number
  text: string
}

interface TranscribeResult {
  text: string | null
  segments: SimpleSegment[]
  raw: any
}

export default function TranscribePage() {
  const [file, setFile] = useState<File | null>(null)
  const [prompt, setPrompt] = useState("")
  const [withSegments, setWithSegments] = useState(true)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<TranscribeResult | null>(null)
  const [copied, setCopied] = useState(false)
  const inputRef = useRef<HTMLInputElement | null>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (!f) return
    if (f.size > 25 * 1024 * 1024) {
      setError("Файл больше 25MB лимита")
      return
    }
    setError(null)
    setResult(null)
    setFile(f)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    const f = e.dataTransfer.files?.[0]
    if (!f) return
    if (f.size > 25 * 1024 * 1024) {
      setError("Файл больше 25MB лимита")
      return
    }
    setError(null)
    setResult(null)
    setFile(f)
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
  }

  const reset = () => {
    setFile(null)
    setResult(null)
    setError(null)
    setPrompt("")
    setCopied(false)
    if (inputRef.current) inputRef.current.value = ""
  }

  const copyText = () => {
    if (!result?.text) return
    navigator.clipboard.writeText(result.text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    })
  }

  const downloadTxt = () => {
    if (!result) return
    const content = result.segments?.length
      ? result.segments
          .map((s) => {
            const start = formatTime(s.start)
            const end = formatTime(s.end)
            return `${start} - ${end}: ${s.text}`
          })
          .join("\n")
      : result.text || ""
    const blob = new Blob([content], { type: "text/plain" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `${file?.name || "transcript"}.txt`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60)
    const s = Math.floor(seconds % 60)
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`
  }

  const submit = async () => {
    if (!file) {
      setError("Выберите аудио файл")
      return
    }
    setIsLoading(true)
    setError(null)
    setResult(null)
    try {
      const token = localStorage.getItem("APP_JWT")
      if (!token) {
        setError("Нет токена авторизации (войдите снова)")
        setIsLoading(false)
        return
      }
      const form = new FormData()
      form.append("file", file)
      form.append("response_format", "json")
      form.append("with_segments", withSegments ? "true" : "false")
      if (prompt.trim()) form.append("prompt", prompt.trim())

      const res = await fetch(`${API_URL}/api/whisper/transcribe`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: form,
      })
      if (!res.ok) {
        const text = await res.text()
        throw new Error(`Ошибка ${res.status}: ${text}`)
      }
      const data = await res.json()
      setResult(data)
    } catch (e: any) { // eslint-disable-line @typescript-eslint/no-explicit-any
      setError(e.message || "Ошибка запроса")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <h1 className="text-2xl font-semibold">Транскрибировать аудио</h1>
        <div className="grid gap-6 md:grid-cols-3">
          <div className="md:col-span-1 space-y-6">
            <Card className="bg-white border-gray-200">
              <CardHeader>
                <CardTitle className="flex items-center gap-2"><Upload className="w-5 h-5" /> Файл</CardTitle>
              </CardHeader>
              <CardContent>
                <div
                  onDrop={handleDrop}
                  onDragOver={handleDragOver}
                  className="border-2 border-dashed rounded-md p-4 text-center cursor-pointer hover:border-blue-400 transition"
                  onClick={() => inputRef.current?.click()}
                >
                  {file ? (
                    <div className="flex flex-col items-center gap-2">
                      <FileAudio2 className="w-8 h-8 text-blue-600" />
                      <span className="text-sm font-medium">{file.name}</span>
                      <span className="text-xs text-gray-500">{(file.size / 1024 / 1024).toFixed(2)} MB</span>
                    </div>
                  ) : (
                    <div className="text-sm text-gray-500">
                      Перетащите аудио или нажмите чтобы выбрать (макс 25MB)
                    </div>
                  )}
                  <Input ref={inputRef} type="file" accept="audio/*" className="hidden" onChange={handleFileChange} />
                </div>
                {file && (
                  <Button variant="ghost" size="sm" className="mt-2" onClick={reset}><RefreshCcw className="w-4 h-4 mr-1"/>Сбросить</Button>
                )}
              </CardContent>
            </Card>

            <Card className="bg-white border-gray-200">
              <CardHeader>
                <CardTitle className="flex items-center gap-2"><Wand2 className="w-5 h-5" /> Опции</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Промпт (опционально)</label>
                  <Textarea rows={3} placeholder="Контекст или слова для подсказки модели" value={prompt} onChange={(e) => setPrompt(e.target.value)} />
                </div>
                <div className="flex items-center gap-2">
                  <input
                    id="withSegments"
                    type="checkbox"
                    checked={withSegments}
                    onChange={(e) => setWithSegments(e.target.checked)}
                    className="h-4 w-4"
                  />
                  <label htmlFor="withSegments" className="text-sm">Вернуть сегменты с таймкодами</label>
                </div>
                <Button className="w-full" onClick={submit} disabled={isLoading || !file}>
                  {isLoading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                  Транскрибировать
                </Button>
                {error && <p className="text-sm text-red-600 whitespace-pre-line">{error}</p>}
              </CardContent>
            </Card>
          </div>

          <div className="md:col-span-2 space-y-6">
            <Card className="bg-white border-gray-200">
              <CardHeader>
                <CardTitle className="flex items-center gap-2"><List className="w-5 h-5" /> Результат</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {!result && !isLoading && <p className="text-sm text-gray-500">Здесь появится результат транскрибации.</p>}
                {isLoading && (
                  <div className="flex items-center gap-3 text-sm text-gray-600"><Loader2 className="w-5 h-5 animate-spin" /> Обработка файла...</div>
                )}
                {result && (
                  <div className="space-y-4">
                    {result.text && (
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <h3 className="text-sm font-semibold">Полный текст</h3>
                          <div className="flex gap-2">
                            <Button size="sm" variant="outline" onClick={copyText}><Copy className="w-4 h-4 mr-1" />{copied ? "Скопировано" : "Копировать"}</Button>
                            <Button size="sm" variant="outline" onClick={downloadTxt}><Download className="w-4 h-4 mr-1" />TXT</Button>
                          </div>
                        </div>
                        <div className="max-h-72 overflow-y-auto p-3 border rounded-md bg-gray-50 whitespace-pre-wrap text-sm leading-relaxed">
                          {result.text}
                        </div>
                      </div>
                    )}
                    {withSegments && result.segments?.length > 0 && (
                      <div className="space-y-3">
                        <Separator />
                        <h3 className="text-sm font-semibold">Сегменты ({result.segments.length})</h3>
                        <div className="max-h-[420px] overflow-y-auto space-y-3 pr-2">
                          {result.segments.map((s) => (
                            <div key={s.index} className="p-3 rounded-md border bg-white hover:shadow-sm transition">
                              <div className="flex items-center justify-between mb-2 text-xs text-gray-500">
                                <span>#{s.index}</span>
                                <span>{formatTime(s.start)} - {formatTime(s.end)}</span>
                              </div>
                              <div className="text-sm leading-relaxed text-gray-800">{s.text}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    {!isLoading && result && withSegments && result.segments?.length === 0 && (
                      <p className="text-xs text-gray-500">Сегменты не найдены в ответе.</p>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}
