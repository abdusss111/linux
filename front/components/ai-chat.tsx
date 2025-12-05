"use client"

import { useState, useEffect, useRef } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { ArrowUp, Bot, FileText, BookOpen, Copy, X } from "lucide-react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"

interface AIChatProps {
  sessionId: string
  meetingTitle: string
  meetingCreatedAt: string
  speakers: string[]
  transcript: string
}

interface ChatMessage {
  id: number
  session_id: string
  sender: string
  content: string
  created_at: string
}

interface ChatHistoryResponse {
  session_id: string
  total_messages: number
  messages: ChatMessage[]
}

interface CustomPrompt {
  id: number
  name: string
  content: string
  is_active: boolean
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://api.dapmeet.kz"

const calculateMeetingDuration = (transcript: string): string => {
  const timeMatches = transcript.match(/\d{2}:\d{2}:\d{2}/g)
  if (!timeMatches || timeMatches.length < 2) return "Не определена"

  const startTime = timeMatches[0]
  const endTime = timeMatches[timeMatches.length - 1]

  const start = new Date(`1970-01-01T${startTime}`)
  const end = new Date(`1970-01-01T${endTime}`)
  const duration = Math.round((end.getTime() - start.getTime()) / (1000 * 60))

  return `${duration} минут`
}

const cleanMarkdown = (text: string): string => {
  return text
    .replace(/\*\*(.*?)\*\*/g, "$1") // Remove bold markdown
    .replace(/\*(.*?)\*/g, "$1") // Remove italic markdown
    .replace(/`(.*?)`/g, "$1") // Remove inline code markdown
    .replace(/```[\s\S]*?```/g, "") // Remove code blocks
    .replace(/#{1,6}\s/g, "") // Remove headers
    .replace(/^\s*[-*+]\s/gm, "• ") // Convert list items to bullets
    .replace(/^\s*\d+\.\s/gm, "") // Remove numbered list formatting
    .replace(/\[([^\]]+)\]$$[^)]+$$/g, "$1") // Convert links to text only
    .replace(/\n{3,}/g, "\n\n") // Reduce multiple newlines
    .trim()
}

const ConfirmationModal = ({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
}: {
  isOpen: boolean
  onClose: () => void
  onConfirm: () => void
  title: string
  message: string
}) => {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4 shadow-xl">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>
        <p className="text-gray-600 mb-6">{message}</p>
        <div className="flex gap-3 justify-end">
          <Button variant="outline" onClick={onClose} className="px-4 py-2 bg-transparent">
            Отмена
          </Button>
          <Button onClick={onConfirm} className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white">
            Удалить
          </Button>
        </div>
      </div>
    </div>
  )
}

export function AIChat({ sessionId, meetingTitle, meetingCreatedAt, speakers, transcript }: AIChatProps) {
  const [message, setMessage] = useState("")
  const [messages, setMessages] = useState<Array<{ role: "user" | "assistant"; content: string }>>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isLoadingHistory, setIsLoadingHistory] = useState(true)
  const [copySuccess, setCopySuccess] = useState<number | null>(null)
  const [customPrompts, setCustomPrompts] = useState<CustomPrompt[]>([])
  const [isLoadingPrompts, setIsLoadingPrompts] = useState(true)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [promptToDelete, setPromptToDelete] = useState<number | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const chatContainerRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight
    }
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    const loadChatHistory = async () => {
      try {
        const token = localStorage.getItem("APP_JWT")
        if (!token) {
          setIsLoadingHistory(false)
          return
        }

  const response = await fetch(`${API_URL}/api/chat/${sessionId}/history?page=1&size=50`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        })

        if (response.ok) {
          const data: ChatHistoryResponse = await response.json()
          const formattedMessages = data.messages.map((msg) => ({
            role: msg.sender === "user" ? ("user" as const) : ("assistant" as const),
            content: msg.content,
          }))
          setMessages(formattedMessages)
        }
      } catch (error) {
        console.error("Error loading chat history:", error)
      } finally {
        setIsLoadingHistory(false)
      }
    }

    loadChatHistory()
  }, [sessionId])

  useEffect(() => {
    const loadCustomPrompts = async () => {
      try {
        const token = localStorage.getItem("APP_JWT")
        if (!token) {
          setIsLoadingPrompts(false)
          return
        }

  const response = await fetch(`${API_URL}/api/prompts/`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        })

        if (response.ok) {
          const data = await response.json()
          const filteredPrompts = data.prompts.filter(
            (prompt: CustomPrompt) =>
              prompt.is_active && prompt.name !== "brief-resume" && prompt.name !== "detailed-resume" && prompt.name !== "meeting-notes",
          )
          setCustomPrompts(filteredPrompts)
        }
      } catch (error) {
        console.error("Error loading custom prompts:", error)
      } finally {
        setIsLoadingPrompts(false)
      }
    }

    loadCustomPrompts()
  }, [])

  const saveMessage = async (sender: "user" | "ai", content: string) => {
    try {
      const token = localStorage.getItem("APP_JWT")
      if (!token) return

  const response = await fetch(`${API_URL}/api/chat/${sessionId}/messages`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          sender,
          content,
        }),
      })

      if (!response.ok) {
        console.error("Failed to save message")
      }
    } catch (error) {
      console.error("Error saving message:", error)
    }
  }

  const handleSend = async (customMessage?: string, displayMessage?: string) => {
    const messageToSend = customMessage || message
    const messageToDisplay = displayMessage || messageToSend
    const messageToSave = displayMessage || messageToSend

    if (!messageToSend.trim()) return

    if (!customMessage) {
      setMessage("")
    }

    setMessages((prev) => [...prev, { role: "user", content: messageToDisplay }])
    setIsLoading(true)

    await saveMessage("user", messageToSave)

    try {
      const meetingContext = `
Информация о встрече:
- Название: ${meetingTitle}
- Дата и время: ${new Date(meetingCreatedAt).toLocaleDateString("ru-RU")} ${new Date(meetingCreatedAt).toLocaleTimeString("ru-RU")}
- Участники: ${speakers.length > 0 ? speakers.join(", ") : "Не определены"}
- Продолжительность: ${calculateMeetingDuration(transcript)}

Транскрипт встречи:
${transcript}
      `.trim()

      const response = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          prompt: messageToSend,
          context: meetingContext,
        }),
      })

      if (!response.ok) throw new Error("Failed to send message")

      const data = await response.json()
      const assistantMessage = data.text

      setMessages((prev) => [...prev, { role: "assistant", content: assistantMessage }])

      await saveMessage("ai", assistantMessage)
    } catch (error) {
      console.error("Error sending message:", error)
      const errorMessage = "Извините, произошла ошибка при обработке вашего запроса."
      setMessages((prev) => [...prev, { role: "assistant", content: errorMessage }])

      await saveMessage("ai", errorMessage)
    } finally {
      setIsLoading(false)
    }
  }

  const handleQuickPrompt = async (promptType: "brief" | "detailed" | "notes") => {
    const promptNames = {
      brief: "brief-resume",
      detailed: "detailed-resume",
      notes: "meeting-notes",
    }

    try {
      const token = localStorage.getItem("APP_JWT")
      if (!token) {
        console.error("No auth token found")
        return
      }

  const response = await fetch(`${API_URL}/api/prompts/by-name/${promptNames[promptType]}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      if (!response.ok) {
        throw new Error("Failed to fetch prompt")
      }

      const promptData = await response.json()
      const promptContent = promptData.content
      const displayName = promptType === "brief" 
        ? "Краткое резюме и следующие действия" 
        : promptType === "detailed"
          ? "Подробное резюме"
          : "Конспект встречи"

      handleSend(promptContent, displayName)
    } catch (error) {
      console.error("Error fetching prompt:", error)
      const prompts = {
        brief: {
          full: `Сделай краткое официальное резюме онлайн-встречи. Включи следующие элементы:

        Цель встречи и основные обсуждённые темы — сформулируй сжато, но по существу.

        Участников встречи — с указанием ролей, если это важно.

        Краткий обзор ключевых обсуждений — изложи без лишних деталей, но с акцентом на суть и сделанные выводы. Без нумерации.

        Следующие шаги для каждого участника — чётко укажи, кто за что отвечает и в какие сроки.

        Упомяни, если была согласована дата следующей встречи.

        Стиль оформления — официальный, важные моменты выделяй жирным шрифтом.

        Краткое резюме и действия`,
          display: "Краткое резюме и следующие действия",
        },
        detailed: {
          full: `Создай подробное официальное резюме внутренней командной онлайн-встречи. Включи следующие структурированные блоки:

        Контекст и повестка встречи — 1–2 предложения с описанием цели встречи и ключевых тем обсуждения.

        Общие сведения о встрече — укажи дату и время проведения (включая точное время начала и окончания), формат встречи (онлайн/гибридный), платформу проведения (Zoom, Teams, Google Meet и т.д.) и список участников с их ролями (если применимо).

        Обсуждаемые темы и подробное резюме — представь нумерованный список всех ключевых тем, поднятых на встрече, и по каждой теме подробно опиши, что обсуждалось. Используй подзаголовки, логичный пересказ, отрази мнения, предложения и выводы участников.

        Результаты и действия участников — перечисли принятые решения и договоренности (включая цифры, сроки, показатели), затем распиши следующие шаги и задачи для каждого участника, включая сроки. Укажи также открытые вопросы, перенесённые на следующую встречу.

        Цитаты и замечания участников — включи ключевые формулировки, предложения, инициативы и сомнения, прозвучавшие в ходе обсуждения.

        Дата следующей встречи — если согласована.

        Весь текст должен быть официальным по стилю. Ключевые детали и важные моменты выделяй жирным шрифтом для акцента.`,
          display: "Подробное резюме",
        },
        notes: {
          full: `Проанализируй транскрипт лекции и создай структурированный конспект.

ТРАНСКРИПТ:
[Текст транскрипта]

---

ЗАДАЧА:
Преобразуй устную речь в четкий письменный конспект, который легко читать и по которому удобно учиться.

СТРУКТУРА КОНСПЕКТА:

1. ОСНОВНАЯ ИНФОРМАЦИЯ
- Тема лекции (1 предложение)
- Ключевой вопрос или проблема, которую разбирает лектор

2. ГЛАВНЫЕ ИДЕИ
Выдели 3-7 основных мыслей или концепций лекции. Каждую идею опиши кратко (1-3 предложения).

3. ПОДРОБНЫЙ РАЗБОР
Раздели материал на логические блоки. Для каждого блока укажи:
- Основные понятия и определения
- Объяснения и аргументы
- Примеры, иллюстрации, кейсы
- Цифры, данные, факты
- Важные цитаты (если есть)

4. ПРАКТИЧЕСКОЕ ПРИМЕНЕНИЕ
- Как использовать эти знания?
- Какие методы, техники, алгоритмы упоминались?
- Пошаговые инструкции (если были)

5. ВАЖНЫЕ НЮАНСЫ
- На что обратить особое внимание
- Частые ошибки или заблуждения
- Связи с другими темами

6. КЛЮЧЕВЫЕ ВЫВОДЫ
3-5 главных takeaways - самое важное, что нужно запомнить.

7. ДОПОЛНИТЕЛЬНО (если упоминалось)
- Рекомендованная литература
- Ресурсы для изучения
- Упомянутые исследования или авторы

---

ПРАВИЛА ОБРАБОТКИ:
Удали слова-паразиты, повторы, оговорки
Сохрани всю важную информацию и детали
Используй точную терминологию из лекции
Структурируй материал логично, даже если в речи он был хаотичным
Выделяй жирным ключевые термины и понятия
Используй маркированные списки для наглядности
Пиши простым языком, но без потери смысла
Целевой объем: 25% от исходного текста

ФОРМАТ:
Используй четкую иерархию заголовков, списки и визуальное разделение блоков для удобства чтения.`,
          display: "Конспект встречи",
        },
      }

      const selectedPrompt = prompts[promptType]
      handleSend(selectedPrompt.full, selectedPrompt.display)
    }
  }

  const handleCustomPrompt = async (prompt: CustomPrompt) => {
    handleSend(prompt.content, prompt.name)
  }

  const handleCopyMessage = async (content: string, index: number) => {
    try {
      const cleanedContent = cleanMarkdown(content)
      const textToCopy = `${cleanedContent}\n\nСоздано на dapmeet.kz`
      await navigator.clipboard.writeText(textToCopy)
      setCopySuccess(index)
      setTimeout(() => setCopySuccess(null), 2000)
    } catch (error) {
      console.error("Failed to copy message:", error)
    }
  }

  const deletePrompt = async (promptId: number) => {
    setPromptToDelete(promptId)
    setShowDeleteModal(true)
  }

  const handleConfirmDelete = async () => {
    if (!promptToDelete) return

    try {
      const token = localStorage.getItem("APP_JWT")
      if (!token) {
        console.error("No auth token found")
        return
      }

  const response = await fetch(`${API_URL}/api/prompts/${promptToDelete}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      if (response.ok) {
        setCustomPrompts((prev) => prev.filter((prompt) => prompt.id !== promptToDelete))
      } else {
        console.error("Failed to delete prompt")
        alert("Не удалось удалить промпт. Попробуйте еще раз.")
      }
    } catch (error) {
      console.error("Error deleting prompt:", error)
      alert("Произошла ошибка при удалении промпта.")
    } finally {
      setShowDeleteModal(false)
      setPromptToDelete(null)
    }
  }

  const handleCancelDelete = () => {
    setShowDeleteModal(false)
    setPromptToDelete(null)
  }

  if (isLoadingHistory) {
    return (
      <Card className="bg-white border-gray-200">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bot className="w-5 h-5" />
            AI
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="h-40 flex items-center justify-center">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
              <p className="text-gray-600">Загрузка истории чата...</p>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <>
      <ConfirmationModal
        isOpen={showDeleteModal}
        onClose={handleCancelDelete}
        onConfirm={handleConfirmDelete}
        title="Удалить промпт"
        message="Вы уверены, что хотите удалить этот промпт? Это действие нельзя отменить."
      />

      <Card className="bg-white border-gray-200">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bot className="w-5 h-5" />
            AI
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div ref={chatContainerRef} className="min-h-40 max-h-[1200px] overflow-y-auto p-4 space-y-4">
            {messages.length === 0 ? (
              <div className="text-center text-gray-500 py-4">
                <Bot className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                <p className="text-sm">Задайте вопрос о встрече, и я помогу вам найти ответ!</p>
              </div>
            ) : (
              messages.map((msg, index) => (
                <div
                  key={index}
                  className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"} group animate-in slide-in-from-bottom-2 duration-500`}
                  style={{ animationDelay: `${index * 100}ms` }}
                >
                  <div
                    className={`max-w-[85%] md:max-w-[80%] p-2 md:p-3 rounded-lg relative ${
                      msg.role === "user" ? "bg-blue-600 text-white" : "bg-white border border-gray-200"
                    }`}
                  >
                    {msg.role === "assistant" ? (
                      <div className="prose prose-xs max-w-none prose-headings:text-gray-900 prose-p:text-gray-700 prose-strong:text-gray-900 prose-code:text-gray-800 prose-code:bg-gray-100 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-pre:bg-gray-100 prose-pre:text-gray-800">
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm] as any}
                          components={{
                            p: ({ children }) => (
                              <p className="mb-1.5 last:mb-0 text-xs md:text-sm leading-relaxed">{children}</p>
                            ),
                            ul: ({ children }) => (
                              <ul className="mb-1.5 last:mb-0 pl-3 md:pl-4 text-xs md:text-sm">{children}</ul>
                            ),
                            ol: ({ children }) => (
                              <ol className="mb-1.5 last:mb-0 pl-3 md:pl-4 text-xs md:text-sm">{children}</ol>
                            ),
                            li: ({ children }) => <li className="mb-0.5 text-xs md:text-sm">{children}</li>,
                            h1: ({ children }) => <h1 className="text-sm md:text-lg font-bold mb-1.5">{children}</h1>,
                            h2: ({ children }) => <h2 className="text-xs md:text-base font-bold mb-1.5">{children}</h2>,
                            h3: ({ children }) => <h3 className="text-xs md:text-sm font-bold mb-1">{children}</h3>,
                            strong: ({ children }) => (
                              <strong className="font-semibold text-xs md:text-sm">{children}</strong>
                            ),
                            code: ({ children }) => <code className="text-xs">{children}</code>,
                          }}
                        >
                          {msg.content}
                        </ReactMarkdown>
                      </div>
                    ) : (
                      <span className="text-xs md:text-sm leading-relaxed">{msg.content}</span>
                    )}

                    <div className="flex justify-end mt-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        className={`opacity-0 group-hover:opacity-100 transition-opacity h-8 w-16 text-xs ${
                          msg.role === "user"
                            ? "bg-blue-500 hover:bg-blue-400 text-white"
                            : "bg-gray-100 hover:bg-gray-200 text-gray-600"
                        } ${copySuccess === index ? "opacity-100" : ""}`}
                        onClick={() => handleCopyMessage(msg.content, index)}
                        title="Копировать сообщение"
                      >
                        {copySuccess === index ? <span className="text-xs">✓</span> : <Copy className="w-4 h-4" />}
                      </Button>
                    </div>
                  </div>
                </div>
              ))
            )}
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-white border border-gray-200 p-3 rounded-lg">
                  <div className="flex items-center gap-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                    Думаю...
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div
            className="flex flex-col gap-2 p-3 rounded-lg border border-blue-200"
            style={{ backgroundColor: "rgba(7, 65, 210, 0.05)" }}
          >
            <div className="flex flex-col sm:flex-row gap-2 flex-wrap">
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleQuickPrompt("brief")}
                disabled={isLoading}
                className="flex-1 justify-start gap-1 md:gap-2 bg-white hover:bg-blue-50 border-blue-200 transition-all duration-200 text-xs md:text-sm px-2 md:px-3 py-1.5 md:py-2"
                style={{ color: "rgb(7, 65, 210)" }}
              >
                <FileText className="w-3 h-3 md:w-4 md:h-4 flex-shrink-0" />
                <span className="truncate">Краткое резюме</span>
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleQuickPrompt("detailed")}
                disabled={isLoading}
                className="flex-1 justify-start gap-1 md:gap-2 bg-white hover:bg-blue-50 border-blue-200 transition-all duration-200 text-xs md:text-sm px-2 md:px-3 py-1.5 md:py-2"
                style={{ color: "rgb(7, 65, 210)" }}
              >
                <BookOpen className="w-3 h-3 md:w-4 md:h-4 flex-shrink-0" />
                <span className="truncate">Подробное резюме</span>
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleQuickPrompt("notes")}
                disabled={isLoading}
                className="flex-1 justify-start gap-1 md:gap-2 bg-white hover:bg-blue-50 border-blue-200 transition-all duration-200 text-xs md:text-sm px-2 md:px-3 py-1.5 md:py-2"
                style={{ color: "rgb(7, 65, 210)" }}
              >
                <FileText className="w-3 h-3 md:w-4 md:h-4 flex-shrink-0" />
                <span className="truncate">Конспект</span>
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => window.open("/prompts/create", "_blank")}
                disabled={isLoading}
                className="flex-1 justify-start gap-1 md:gap-2 bg-white hover:bg-green-50 border-green-200 transition-all duration-200 text-xs md:text-sm px-2 md:px-3 py-1.5 md:py-2"
                style={{ color: "rgb(34, 197, 94)" }}
              >
                <span className="text-lg leading-none">+</span>
                <span className="truncate">Создать свою кнопку</span>
              </Button>
            </div>

            {!isLoadingPrompts && customPrompts.length > 0 && (
              <div className="flex flex-col sm:flex-row gap-2 flex-wrap">
                {customPrompts.map((prompt) => (
                  <div key={prompt.id} className="relative flex-1 group">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleCustomPrompt(prompt)}
                      disabled={isLoading}
                      className="w-full justify-start gap-1 md:gap-2 bg-white hover:bg-purple-50 border-purple-200 transition-all duration-200 text-xs md:text-sm px-2 md:px-3 py-1.5 md:py-2 pr-8"
                      style={{ color: "rgb(147, 51, 234)" }}
                    >
                      <span className="truncate">{prompt.name}</span>
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation()
                        deletePrompt(prompt.id)
                      }}
                      className="absolute top-0 right-0 h-full w-6 p-0 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-100 hover:text-red-600"
                      title="Удалить промпт"
                    >
                      <X className="w-3 h-3" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="flex gap-2">
            <Textarea
              placeholder="Задайте вопрос о встрече..."
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault()
                  handleSend()
                }
              }}
              className="flex-1 h-10 resize-none"
            />
            <Button onClick={() => handleSend()} disabled={!message.trim() || isLoading}>
              <ArrowUp className="w-4 h-4" />
            </Button>
          </div>
        </CardContent>
      </Card>
    </>
  )
}
