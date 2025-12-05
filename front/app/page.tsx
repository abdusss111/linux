"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/hooks/use-auth"

export default function Home() {
  const router = useRouter()
  const { user, isLoading } = useAuth()

  useEffect(() => {
    if (!isLoading) {
      if (user) {
        router.replace("/meetings")
      } else {
        router.replace("/login")
      }
    }
  }, [user, isLoading, router])

  // Show loading state while checking auth
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-br from-blue-50 via-white to-slate-100 px-4">
      <div className="mx-auto max-w-2xl text-center space-y-8">
        {/* Logo */}
        <div className="flex justify-center">
          <object
            data="/dapmeet-logo.png"
            type="image/png"
            className="h-auto w-auto rounded-2xl shadow-md border border-slate-400 dark:border-slate-400"
          >
            {/* fallback на случай, если object не загрузится */}
            <img src="/dapmeet-logo.png" alt="Dapmeet Logo" className="h-auto w-auto object-contain" />
          </object>
        </div>

        {/* Title */}
        <div>
          <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl mb-2">Dapmeet</h1>
        </div>
      </div>
    </div>
  )
}
