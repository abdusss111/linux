import type React from "react"
import type { Metadata } from "next"
import { Inter } from "next/font/google"
import "./globals.css"
import { AuthProvider } from "@/components/auth-provider"
import { Suspense } from "react"

const inter = Inter({ subsets: ["latin", "cyrillic"] })

export const metadata: Metadata = {
  title: "Dapmeet",
  description: "Платформа для анализа встреч",
  icons: {
    icon: [
      {
        url: "/favicon.png",
        sizes: "128x128",
        type: "image/png",
      },
    ],
    shortcut: "/favicon.png",
    apple: "/favicon.png",
  },
    generator: 'v0.app'
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ru" suppressHydrationWarning>
      <head>
        {/* Yandex.Metrika counter */}
        <script type="text/javascript" dangerouslySetInnerHTML={{
          __html: `
            (function(m,e,t,r,i,k,a){
                m[i]=m[i]||function(){(m[i].a=m[i].a||[]).push(arguments)};
                m[i].l=1*new Date();
                for (var j = 0; j < document.scripts.length; j++) {if (document.scripts[j].src === r) { return; }}
                k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,a.parentNode.insertBefore(k,a)
            })(window, document,'script','https://mc.yandex.ru/metrika/tag.js?id=104127058', 'ym');

            ym(104127058, 'init', {ssr:true, webvisor:true, clickmap:true, ecommerce:"dataLayer", accurateTrackBounce:true, trackLinks:true});
          `
        }} />
      </head>
      <body className={`${inter.className} bg-background text-foreground`}>
        {/* Yandex.Metrika noscript fallback */}
        <noscript>
          <div>
            <img src="https://mc.yandex.ru/watch/104127058" style={{position: 'absolute', left: '-9999px'}} alt="" />
          </div>
        </noscript>
        <AuthProvider>
          <Suspense fallback={<div className="text-center p-8">Загрузка...</div>}>{children}</Suspense>
          <footer className="border-t bg-gray-50">
            <div className="max-w-7xl mx-auto px-4 py-8">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-6">
                {/* Левая колонка - Информация о компании */}
                <div>
                  <h3 className="text-lg font-semibold mb-2 text-gray-900">Dapmeet</h3>
                  <p className="text-sm text-gray-600">
                    Сервис транскрибации онлайн встреч
                  </p>
                </div>

                {/* Средняя колонка - Правовая информация */}
                <div>
                  <h3 className="text-lg font-semibold mb-3 text-gray-900">Правовая информация</h3>
                  <ul className="space-y-2">
                    <li>
                      <a href="/privacy" className="text-sm text-gray-600 hover:text-gray-900 hover:underline">
                        Политика конфиденциальности
                      </a>
                    </li>
                    <li>
                      <a href="/offer" className="text-sm text-gray-600 hover:text-gray-900 hover:underline">
                        Договор публичной оферты
                      </a>
                    </li>
                  </ul>
                </div>

                {/* Правая колонка - Контакты */}
                <div>
                  <h3 className="text-lg font-semibold mb-3 text-gray-900">Контакты</h3>
                  <ul className="space-y-2 text-sm text-gray-600">
                    <li>
                      <span className="font-medium">Email:</span>{" "}
                      <a href="mailto:info@dapmeet.kz" className="hover:text-gray-900 hover:underline">
                        info@dapmeet.kz
                      </a>
                    </li>
                    <li>
                      <span className="font-medium">Телефон:</span>{" "}
                      <a href="tel:+77074861561" className="hover:text-gray-900 hover:underline">
                        +77074861561
                      </a>
                    </li>
                    <li>
                      <span className="font-medium">Адрес:</span> Казахстан, город Алматы, Бостандыкский район, Проспект Гагарина, дом 124, н.п. 785, почтовый индекс 050064
                    </li>
                  </ul>
                </div>
              </div>

              {/* Нижняя строка - Копирайт и БИН/ИИН */}
              <div className="border-t pt-4 flex flex-col md:flex-row justify-between items-center text-sm text-gray-600">
                <p>© 2025 ТОО "ROBOLABS". Все права защищены.</p>
                <p>БИН/ИИН: 251240007017</p>
              </div>
            </div>
          </footer>
        </AuthProvider>
      </body>
    </html>
  )
}
