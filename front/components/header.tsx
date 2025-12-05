"use client"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { LogOut, User, Menu } from "lucide-react"
import Image from "next/image"
import { useAuth } from "@/hooks/use-auth"
import { useRouter } from "next/navigation"
import { useState, useEffect } from "react"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://api.dapmeet.kz"

interface Subscription {
  plan: string
  status: string
  days_remaining: number | null
}

interface HeaderProps {
  onMenuClick?: () => void
}

export function Header({ onMenuClick }: HeaderProps) {
  const { user, logout } = useAuth()
  const router = useRouter()
  const [subscription, setSubscription] = useState<Subscription | null>(null)
  const [isLoadingSubscription, setIsLoadingSubscription] = useState(true)

  useEffect(() => {
    const fetchSubscription = async () => {
      if (!user) {
        setIsLoadingSubscription(false)
        return
      }

      try {
        const token = localStorage.getItem("APP_JWT")
        if (!token) {
          setIsLoadingSubscription(false)
          return
        }

        const response = await fetch(`${API_URL}/api/subscriptions/verify`, {
          method: "GET",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        })

        if (response.ok) {
          const data = await response.json()
          setSubscription(data)
        }
      } catch (error) {
        console.error("Ошибка при загрузке подписки:", error)
      } finally {
        setIsLoadingSubscription(false)
      }
    }

    fetchSubscription()
  }, [user])

  const handleLogout = async () => {
    try {
      await logout()
      router.push("/login")
    } catch (error) {
      console.error("Ошибка при выходе:", error)
    }
  }

  const getPlanDisplayName = (plan: string) => {
    const planNames: Record<string, string> = {
      free: "Free",
      standard: "Standard",
      premium: "Premium",
    }
    return planNames[plan] || plan
  }

  const getPlanBadgeVariant = (plan: string) => {
    if (plan === "free") return "secondary"
    if (plan === "standard") return "default"
    if (plan === "premium") return "outline"
    return "secondary"
  }

  return (
    <header className="bg-white border-b border-gray-200 px-4 md:px-6 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="md:hidden" onClick={onMenuClick}>
            <Menu className="h-6 w-6" />
          </Button>
          <Image src="/dapmeet-logo.png" alt="Dapmeet" width={180} height={60} className="h-8 sm:h-10 md:h-12 w-auto" />
        </div>

        <div className="flex items-center gap-4">
          {user && (
            <div className="hidden md:flex items-center gap-3">
              <span className="text-sm font-medium text-gray-700">{user.name}</span>
              {!isLoadingSubscription && subscription && (
                <Badge variant={getPlanBadgeVariant(subscription.plan)}>
                  {getPlanDisplayName(subscription.plan)}
                  {subscription.days_remaining !== null && subscription.days_remaining > 0 && (
                    <span className="ml-1">({subscription.days_remaining} дн.)</span>
                  )}
                </Badge>
              )}
            </div>
          )}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Avatar className="w-8 h-8 cursor-pointer hover:opacity-80 transition-opacity">
                <AvatarImage src="/placeholder-avatar.jpg" />
                <AvatarFallback>{user?.name?.charAt(0)?.toUpperCase() || "U"}</AvatarFallback>
              </Avatar>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuItem className="flex items-center gap-2 cursor-pointer">
                <User className="w-4 h-4" />
                <span>{user?.name || "Пользователь"}</span>
              </DropdownMenuItem>
              {!isLoadingSubscription && subscription && (
                <DropdownMenuItem className="flex items-center gap-2 cursor-default">
                  <Badge variant={getPlanBadgeVariant(subscription.plan)} className="text-xs">
                    {getPlanDisplayName(subscription.plan)}
                    {subscription.days_remaining !== null && subscription.days_remaining > 0 && (
                      <span className="ml-1">({subscription.days_remaining} дн.)</span>
                    )}
                  </Badge>
                </DropdownMenuItem>
              )}
              <DropdownMenuItem
                className="flex items-center gap-2 cursor-pointer text-red-600 focus:text-red-600"
                onClick={handleLogout}
              >
                <LogOut className="w-4 h-4" />
                <span>Выйти</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  )
}
