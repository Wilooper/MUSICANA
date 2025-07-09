'use client'

import React, { useState, useRef, useEffect } from 'react'
import { 
  FaPlay, 
  FaPause, 
  FaStepForward, 
  FaStepBackward, 
  FaVolumeUp, 
  FaVolumeMute,
  FaRandom,
  FaRedo,
  FaHeart,
  FaExpand
} from 'react-icons/fa'

export default function MusicPlayer() {
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(240) // 4 minutes sample
  const [volume, setVolume] = useState(0.7)
  const [isMuted, setIsMuted] = useState(false)
  const [isShuffled, setIsShuffled] = useState(false)
  const [isRepeated, setIsRepeated] = useState(false)
  const [isLiked, setIsLiked] = useState(false)

  // Sample current song
  const currentSong = {
    title: "Tere Vaaste",
    artist: "Rahat Fateh Ali Khan",
    album: "Latest Hits",
    image: "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=100&h=100&fit=crop&crop=center"
  }

  // Simulate progress
  useEffect(() => {
    let interval: NodeJS.Timeout
    if (isPlaying) {
      interval = setInterval(() => {
        setCurrentTime(prev => {
          if (prev >= duration) {
            setIsPlaying(false)
            return 0
          }
          return prev + 1
        })
      }, 1000)
    }
    return () => clearInterval(interval)
  }, [isPlaying, duration])

  const formatTime = (time: number) => {
    const minutes = Math.floor(time / 60)
    const seconds = Math.floor(time % 60)
    return `${minutes}:${seconds.toString().padStart(2, '0')}`
  }

  const progressPercentage = (currentTime / duration) * 100

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 glass border-t border-white/10">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          {/* Song Info */}
          <div className="flex items-center space-x-4 w-1/3">
            <img
              src={currentSong.image}
              alt={currentSong.title}
              className="w-14 h-14 rounded-lg object-cover"
            />
            <div className="hidden sm:block">
              <h4 className="font-semibold text-white truncate">{currentSong.title}</h4>
              <p className="text-gray-400 text-sm truncate">{currentSong.artist}</p>
            </div>
            <button
              onClick={() => setIsLiked(!isLiked)}
              className={`p-2 hover:scale-110 transition-transform ${
                isLiked ? 'text-red-400' : 'text-gray-400 hover:text-red-400'
              }`}
            >
              <FaHeart />
            </button>
          </div>

          {/* Controls */}
          <div className="flex flex-col items-center w-1/3">
            <div className="flex items-center space-x-4 mb-2">
              <button
                onClick={() => setIsShuffled(!isShuffled)}
                className={`p-2 hover:scale-110 transition-transform ${
                  isShuffled ? 'text-primary-400' : 'text-gray-400 hover:text-white'
                }`}
              >
                <FaRandom />
              </button>
              
              <button className="p-2 hover:scale-110 transition-transform text-gray-400 hover:text-white">
                <FaStepBackward className="text-xl" />
              </button>
              
              <button
                onClick={() => setIsPlaying(!isPlaying)}
                className="bg-white text-dark-900 p-3 rounded-full hover:scale-110 transition-all duration-300 shadow-lg"
              >
                {isPlaying ? <FaPause className="text-xl" /> : <FaPlay className="text-xl ml-1" />}
              </button>
              
              <button className="p-2 hover:scale-110 transition-transform text-gray-400 hover:text-white">
                <FaStepForward className="text-xl" />
              </button>
              
              <button
                onClick={() => setIsRepeated(!isRepeated)}
                className={`p-2 hover:scale-110 transition-transform ${
                  isRepeated ? 'text-primary-400' : 'text-gray-400 hover:text-white'
                }`}
              >
                <FaRedo />
              </button>
            </div>

            {/* Progress Bar */}
            <div className="flex items-center space-x-2 w-full max-w-md">
              <span className="text-xs text-gray-400 w-10">{formatTime(currentTime)}</span>
              <div className="flex-1 h-1 bg-gray-600 rounded-full cursor-pointer">
                <div
                  className="h-full bg-gradient-to-r from-primary-400 to-purple-400 rounded-full transition-all duration-300"
                  style={{ width: `${progressPercentage}%` }}
                ></div>
              </div>
              <span className="text-xs text-gray-400 w-10">{formatTime(duration)}</span>
            </div>
          </div>

          {/* Volume & Options */}
          <div className="flex items-center space-x-4 w-1/3 justify-end">
            <div className="hidden md:flex items-center space-x-2">
              <button
                onClick={() => setIsMuted(!isMuted)}
                className="text-gray-400 hover:text-white transition-colors"
              >
                {isMuted || volume === 0 ? <FaVolumeMute /> : <FaVolumeUp />}
              </button>
              <div className="w-20 h-1 bg-gray-600 rounded-full">
                <div
                  className="h-full bg-white rounded-full"
                  style={{ width: `${isMuted ? 0 : volume * 100}%` }}
                ></div>
              </div>
            </div>
            
            <button className="p-2 text-gray-400 hover:text-white transition-colors">
              <FaExpand />
            </button>

            {/* Equalizer Animation */}
            <div className="hidden lg:flex items-end space-x-1">
              {[...Array(4)].map((_, i) => (
                <div
                  key={i}
                  className={`equalizer-bar bg-primary-400 w-1 rounded-full ${
                    isPlaying ? '' : 'opacity-30'
                  }`}
                  style={{
                    height: isPlaying ? `${Math.random() * 20 + 10}px` : '10px',
                    animationPlayState: isPlaying ? 'running' : 'paused'
                  }}
                ></div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}