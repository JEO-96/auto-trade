import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
    title: 'Momentum Breakout Platform',
    description: 'Automated algorithmic trading platform leveraging James Momentum Breakout strategy',
}

export default function RootLayout({
    children,
}: {
    children: React.ReactNode
}) {
    return (
        <html lang="en">
            <body className={`${inter.className} bg-[#0B0F19] text-white min-h-screen antialiased`}>
                {children}
            </body>
        </html>
    )
}
