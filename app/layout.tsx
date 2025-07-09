import React from 'react'
import './globals.css'
import type { Metadata } from 'next'
import { Inter } from 'next/font/google'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'MUSICANA - Free Music Site',
  description: 'A free music site made in India - Discover, stream, and enjoy music',
  keywords: ['music', 'streaming', 'free music', 'India', 'songs', 'artists'],
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={`${inter.className} bg-dark-900 text-white min-h-screen`}>
        {children}
      </body>
    </html>
  )
}