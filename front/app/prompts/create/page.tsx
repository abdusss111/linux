"use client"

import type React from "react"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { ArrowLeft, Save } from "lucide-react"
import { useRouter } from "next/navigation"

export default function CreatePromptPage() {
  const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://api.dapmeet.kz"
  const [name, setName] = useState("")
  const [content, setContent] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState("")
  const [success, setSuccess] = useState(false)
  const router = useRouter()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!name.trim() || !content.trim()) {
      setError("Пожалуйста, заполните все поля")
      return
    }

    setIsLoading(true)
    setError("")

    try {
      const token = localStorage.getItem("APP_JWT")
      if (!token) {
        setError("Необходима авторизация")
        return
      }

  const response = await fetch(`${API_URL}/api/prompts/`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name: name.trim(),
          content: content.trim(),
          is_active: true,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.message || "Ошибка при создании промпта")
      }

      setSuccess(true)
      setTimeout(() => {
        window.close()
      }, 2000)
    } catch (error) {
      console.error("Error creating prompt:", error)
      setError(error instanceof Error ? error.message : "Произошла ошибка при создании промпта")
    } finally {
      setIsLoading(false)
    }
  }

  if (success) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <Card className="w-full max-w-md">
          <CardContent className="pt-6">
            <div className="text-center">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl">✓</span>
              </div>
              <h2 className="text-xl font-semibold text-gray-900 mb-2">Промпт создан!</h2>
              <p className="text-gray-600">Окно закроется автоматически через несколько секунд</p>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-2xl mx-auto">
        <div className="mb-6">
          <Button variant="ghost" onClick={() => window.close()} className="mb-4">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Закрыть
          </Button>
          <h1 className="text-2xl font-bold text-gray-900">Создать новый промпт</h1>
          <p className="text-gray-600 mt-2">Создайте собственный промпт для быстрого анализа встреч</p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Информация о промпте</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="name">Название промпта</Label>
                <Input
                  id="name"
                  type="text"
                  placeholder="Например: meeting_analyzer"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  disabled={isLoading}
                />
                <p className="text-sm text-gray-500">Используйте только латинские буквы, цифры и подчеркивания</p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="content">Содержание промпта</Label>
                <Textarea
                  id="content"
                  placeholder="Опишите, что должен делать AI с транскриптом встречи..."
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  disabled={isLoading}
                  rows={10}
                  className="resize-none"
                />
                <p className="text-sm text-gray-500">Подробно опишите, как AI должен анализировать встречу</p>
              </div>

              {error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-md">
                  <p className="text-sm text-red-600">{error}</p>
                </div>
              )}

              <div className="flex gap-3">
                <Button type="submit" disabled={isLoading || !name.trim() || !content.trim()} className="flex-1">
                  {isLoading ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Создание...
                    </>
                  ) : (
                    <>
                      <Save className="w-4 h-4 mr-2" />
                      Создать промпт
                    </>
                  )}
                </Button>
                <Button type="button" variant="outline" onClick={() => window.close()} disabled={isLoading}>
                  Отмена
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
