"use client"

import { useEffect, useState } from "react"
import { useSearchParams } from "next/navigation"
import { Loader2 } from "lucide-react"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://api.dapmeet.kz"

export default function GoogleCallbackPage() {
  const searchParams = useSearchParams()
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading")
  const [errorMsg, setErrorMsg] = useState("")

  useEffect(() => {
    const code = searchParams.get("code")

    if (!code) {
      setStatus("error")
      setErrorMsg("Код авторизации не получен из URL")
      return
    }

    const authenticate = async () => {
      try {
        const res = await fetch(`${API_URL}/auth/google`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ code }),
        })

        if (!res.ok) {
          const text = await res.text()
          throw new Error(text)
        }

        const data = await res.json()

        // Сохраняем данные пользователя
        localStorage.setItem("APP_JWT", data.access_token)
        localStorage.setItem("dapter_user", JSON.stringify(data.user))

        // Устанавливаем успешный статус перед редиректом
        setStatus("success")

        setTimeout(() => {
          window.location.href = "/meetings"
        }, 1000)
      } catch (err: any) {
        console.error("Ошибка авторизации:", err)
        setErrorMsg("Не удалось авторизоваться. Попробуйте снова.")
        setStatus("error")
      }
    }

    authenticate()
  }, [searchParams])

  if (status === "loading") {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4 text-center bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="bg-white p-8 rounded-2xl shadow-lg">
          <Loader2 className="animate-spin w-8 h-8 text-blue-600 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-800 mb-2">Авторизация</h2>
          <p className="text-gray-600">Завершаем вход через Google...</p>
        </div>
      </div>
    )
  }

  if (status === "success") {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4 text-center bg-gradient-to-br from-green-50 to-emerald-100">
        <div className="bg-white p-8 rounded-2xl shadow-lg">
          <div className="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-gray-800 mb-2">Успешно!</h2>
          <p className="text-gray-600">Перенаправляем вас...</p>
        </div>
      </div>
    )
  }

  if (status === "error") {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center text-center px-4 space-y-4 bg-gradient-to-br from-red-50 to-pink-100">
        <div className="bg-white p-8 rounded-2xl shadow-lg max-w-md">
          <div className="w-8 h-8 bg-red-500 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-gray-800 mb-2">Ошибка авторизации</h2>
          <p className="text-red-600 mb-4">{errorMsg}</p>
          <button
            onClick={() => (window.location.href = "/login")}
            className="px-6 py-3 bg-slate-900 text-white rounded-lg hover:bg-slate-800 transition-colors"
          >
            Вернуться на страницу входа
          </button>
        </div>
      </div>
    )
  }

  return null
}
