"use client"

import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import DashboardLayout from "@/components/dashboard-layout"
import { useAuth } from "@/hooks/use-auth"

export default function SettingsPage() {
  const { user, logout } = useAuth()

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Настройки</h1>
          <p className="text-muted-foreground">Управляйте настройками учетной записи и предпочтениями</p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Профиль</CardTitle>
            <CardDescription>Обновите свою личную информацию</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Имя</Label>
              <Input id="name" defaultValue={user?.name || ""} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">Электронная почта</Label>
              <Input id="email" defaultValue={user?.email || ""} disabled />
              <p className="text-xs text-muted-foreground">
                Ваша электронная почта управляется вашей учетной записью Google
              </p>
            </div>
          </CardContent>
          <CardFooter className="flex justify-between">
            <Button variant="outline">Отмена</Button>
            <Button>Сохранить изменения</Button>
          </CardFooter>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Учетная запись</CardTitle>
            <CardDescription>Управляйте настройками учетной записи</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="language">Язык</Label>
              <select
                id="language"
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                defaultValue="ru"
              >
                <option value="ru">Русский</option>
              </select>
            </div>
          </CardContent>
          <CardFooter>
            <Button variant="destructive" className="ml-auto" onClick={logout}>
              Выйти
            </Button>
          </CardFooter>
        </Card>
      </div>
    </DashboardLayout>
  )
}
