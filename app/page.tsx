import React from 'react'
import Header from './components/Header'
import Hero from './components/Hero'
import FeaturedMusic from './components/FeaturedMusic'
import MusicPlayer from './components/MusicPlayer'

export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-dark-900 via-dark-800 to-primary-900">
      <Header />
      <Hero />
      <FeaturedMusic />
      <MusicPlayer />
    </main>
  )
}