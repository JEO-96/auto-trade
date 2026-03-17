import type { Metadata, Viewport } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { Providers } from './providers'
import ServiceWorkerRegistration from '@/components/ServiceWorkerRegistration'

const inter = Inter({ subsets: ['latin'] })

export const viewport: Viewport = {
    width: 'device-width',
    initialScale: 1,
    maximumScale: 1,
    userScalable: false,
    themeColor: '#020617',
}

export const metadata: Metadata = {
    title: 'Backtested | 검증된 자동매매 플랫폼',
    description: '백테스트로 검증된 전략, 성과 기반 수수료. 자동매매의 새로운 기준.',
    manifest: '/manifest.json',
    appleWebApp: {
        capable: true,
        statusBarStyle: 'black-translucent',
        title: 'Backtested',
    },
    icons: {
        icon: [
            { url: '/icon.svg', type: 'image/svg+xml' },
            { url: '/icons/icon-192x192.svg', sizes: '192x192', type: 'image/svg+xml' },
            { url: '/icons/icon-512x512.svg', sizes: '512x512', type: 'image/svg+xml' },
        ],
        apple: [
            { url: '/icons/apple-touch-icon.svg', sizes: '180x180', type: 'image/svg+xml' },
        ],
    },
}

export default function RootLayout({
    children,
}: {
    children: React.ReactNode
}) {
    return (
        <html lang="ko" suppressHydrationWarning>
            <body className={`${inter.className} bg-background text-th-text min-h-screen antialiased`}>
                <ServiceWorkerRegistration />
                <Providers>
                    {children}
                </Providers>
            </body>
        </html>
    )
}
