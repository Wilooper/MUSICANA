'use client'

import React from 'react'
import { FaPlay, FaHeart, FaShare } from 'react-icons/fa'

// Sample data - in a real app, this would come from an API
const featuredSongs = [
  {
    id: 1,
    title: "Bollywood Hits 2024",
    artist: "Various Artists",
    album: "Latest Bollywood",
    duration: "3:45",
    image: "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=300&h=300&fit=crop&crop=center"
  },
  {
    id: 2,
    title: "Classical Indian Music",
    artist: "Ravi Shankar",
    album: "Indian Classical",
    duration: "4:20",
    image: "https://images.unsplash.com/photo-1558618047-3c8c76ca7d13?w=300&h=300&fit=crop&crop=center"
  },
  {
    id: 3,
    title: "Punjabi Party Mix",
    artist: "Diljit Dosanjh",
    album: "Party Anthems",
    duration: "3:12",
    image: "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=300&h=300&fit=crop&crop=center"
  },
  {
    id: 4,
    title: "South Indian Melodies",
    artist: "A.R. Rahman",
    album: "Tamil Hits",
    duration: "4:05",
    image: "https://images.unsplash.com/photo-1558618047-3c8c76ca7d13?w=300&h=300&fit=crop&crop=center"
  }
]

const trendingPlaylists = [
  {
    id: 1,
    title: "Top 50 India",
    description: "Most played tracks in India",
    image: "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=300&h=300&fit=crop&crop=center",
    songCount: 50
  },
  {
    id: 2,
    title: "Indie India",
    description: "Independent Indian artists",
    image: "https://images.unsplash.com/photo-1558618047-3c8c76ca7d13?w=300&h=300&fit=crop&crop=center",
    songCount: 35
  },
  {
    id: 3,
    title: "Workout Beats",
    description: "High energy tracks for your workout",
    image: "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=300&h=300&fit=crop&crop=center",
    songCount: 28
  }
]

export default function FeaturedMusic() {
  return (
    <section className="py-16 px-4">
      <div className="container mx-auto">
        {/* Trending Songs */}
        <div className="mb-16">
          <h2 className="text-3xl md:text-4xl font-bold mb-8 gradient-text">Trending Now</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {featuredSongs.map((song) => (
              <div key={song.id} className="group glass rounded-xl p-4 hover:scale-105 transition-all duration-300">
                <div className="relative mb-4">
                  <img
                    src={song.image}
                    alt={song.title}
                    className="w-full h-48 object-cover rounded-lg"
                  />
                  <button className="absolute inset-0 flex items-center justify-center bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity duration-300 rounded-lg">
                    <FaPlay className="text-3xl text-white" />
                  </button>
                </div>
                <h3 className="font-semibold text-lg mb-1 truncate">{song.title}</h3>
                <p className="text-gray-400 mb-2 truncate">{song.artist}</p>
                <div className="flex items-center justify-between text-sm text-gray-500">
                  <span>{song.duration}</span>
                  <div className="flex space-x-2">
                    <button className="hover:text-red-400 transition-colors">
                      <FaHeart />
                    </button>
                    <button className="hover:text-blue-400 transition-colors">
                      <FaShare />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Featured Playlists */}
        <div>
          <h2 className="text-3xl md:text-4xl font-bold mb-8 gradient-text">Featured Playlists</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {trendingPlaylists.map((playlist) => (
              <div key={playlist.id} className="group glass rounded-xl p-6 hover:scale-105 transition-all duration-300">
                <div className="relative mb-4">
                  <img
                    src={playlist.image}
                    alt={playlist.title}
                    className="w-full h-56 object-cover rounded-lg"
                  />
                  <button className="absolute inset-0 flex items-center justify-center bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity duration-300 rounded-lg">
                    <FaPlay className="text-4xl text-white" />
                  </button>
                </div>
                <h3 className="font-semibold text-xl mb-2">{playlist.title}</h3>
                <p className="text-gray-400 mb-3">{playlist.description}</p>
                <p className="text-sm text-primary-400">{playlist.songCount} songs</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}