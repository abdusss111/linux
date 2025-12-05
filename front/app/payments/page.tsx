"use client"

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Copy, QrCode } from "lucide-react"
import DashboardLayout from "@/components/dashboard-layout"
import Image from "next/image"
import { useState } from "react"

export default function PaymentsPage() {
  const [copied, setCopied] = useState(false)

  const walletAddress = "https://pay.kaspi.kz/pay/cuephjyv"

  const handleCopy = () => {
    navigator.clipboard.writeText(walletAddress)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <DashboardLayout>
      <div className="max-w-xl mx-auto space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <QrCode className="w-5 h-5" />
              Стоимость подписки: 10000 тг/мес
            </CardTitle>
            <CardDescription>
              Отсканируйте QR-код или пройдите по ссылке ниже для оплаты.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col items-center gap-4">
            {/* QR-код (вставьте свою картинку или генератор) */}
            <Image
              src="/kaspi-qr.png" // замените на реальный QR-код или вставьте компонент генерации
              alt="QR Code"
              width={300}
              height={200}
              className="rounded-md border w-full max-w-sm mx-auto"
            />

            {/* Реквизиты */}
            <div className="flex flex-col items-center gap-2 hover:shadow-md transition-shadow">
  <p className="text-sm text-muted-foreground">Ссылка:</p>

  <div className="flex items-center gap-2 bg-muted px-4 py-2 rounded-md">
    <a
      href="https://pay.kaspi.kz/pay/cuephjyv"
      target="_blank"
      rel="noopener noreferrer"
      className="text-sm text-blue-600 hover:underline hover:text-blue-700 transition-colors"
    >
      https://pay.kaspi.kz/pay/cuephjyv
    </a>

    <Button variant="ghost" size="icon" onClick={handleCopy}>
      <Copy className="h-4 w-4" />
      <span className="sr-only">Скопировать</span>
    </Button>
  </div>

  {copied && <span className="text-sm text-green-600">Скопировано!</span>}
</div>


            {/* Инструкция */}
            <div className="text-sm text-center text-muted-foreground mt-4">
              После оплаты вернитесь на сайт — активация произойдёт автоматически в течение 1–5 минут.
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  )
}
