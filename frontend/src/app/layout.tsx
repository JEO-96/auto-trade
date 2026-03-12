import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { Providers } from './providers'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
    title: 'Backtested | 검증된 자동매매 플랫폼',
    description: '백테스트로 검증된 전략, 성과 기반 수수료. 자동매매의 새로운 기준.',
}

export default function RootLayout({
    children,
}: {
    children: React.ReactNode
}) {
    return (
        <html lang="ko">
            <body className={`${inter.className} bg-[#020617] text-white min-h-screen antialiased`}>
                <Providers>
                    {children}
                </Providers>
            </body>
        </html>
    )
}
