import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
    title: 'Momentum PRO | 자동 트레이딩 플랫폼',
    description: '검증된 모멘텀 돌파 전략으로 암호화폐 매매를 자동화하세요.',
}

export default function RootLayout({
    children,
}: {
    children: React.ReactNode
}) {
    return (
        <html lang="ko">
            <body className={`${inter.className} bg-[#020617] text-white min-h-screen antialiased`}>
                {children}
            </body>
        </html>
    )
}
