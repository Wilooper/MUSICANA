'use client'

import React from 'react'
import { FaPlay, FaHeadphones, FaDownload } from 'react-icons/fa'

export default function Hero() {
  return (
    <section className="relative pt-24 pb-16 px-4 overflow-hidden">
      {/* Background Effects */}
      <div className="absolute inset-0 bg-gradient-to-r from-primary-600/20 to-purple-600/20 opacity-30"></div>
      <div className="absolute top-10 left-10 w-72 h-72 bg-primary-500/20 rounded-full blur-3xl"></div>
      <div className="absolute bottom-10 right-10 w-96 h-96 bg-purple-500/20 rounded-full blur-3xl"></div>
      
      <div className="container mx-auto text-center relative z-10">
        <div className="max-w-4xl mx-auto">
          {/* Main Heading */}
          <h1 className="text-5xl md:text-7xl font-bold mb-6 leading-tight">
            <span className="gradient-text">Discover</span>
            <br />
            <span className="text-white">Music Like Never Before</span>
          </h1>
          
          {/* Subtitle */}
          <p className="text-xl md:text-2xl text-gray-300 mb-8 max-w-2xl mx-auto">
            Stream millions of songs for free. Made in India, loved worldwide. 
            Experience music with crystal clear quality and no interruptions.
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-12">
            <button className="group bg-gradient-to-r from-primary-500 to-purple-600 hover:from-primary-600 hover:to-purple-700 text-white px-8 py-4 rounded-full font-semibold text-lg transition-all duration-300 transform hover:scale-105 flex items-center space-x-2">
              <FaPlay className="group-hover:scale-110 transition-transform" />
              <span>Start Listening</span>
            </button>
            <button className="border-2 border-white/30 hover:border-primary-400 text-white px-8 py-4 rounded-full font-semibold text-lg transition-all duration-300 hover:bg-white/10 flex items-center space-x-2">
              <FaDownload />
              <span>Download App</span>
            </button>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-3xl mx-auto">
            <div className="text-center">
              <div className="text-3xl md:text-4xl font-bold gradient-text mb-2">10M+</div>
              <div className="text-gray-400">Songs Available</div>
            </div>
            <div className="text-center">
              <div className="text-3xl md:text-4xl font-bold gradient-text mb-2">1M+</div>
              <div className="text-gray-400">Active Users</div>
            </div>
            <div className="text-center">
              <div className="text-3xl md:text-4xl font-bold gradient-text mb-2">50K+</div>
              <div className="text-gray-400">Artists</div>
            </div>
          </div>

          {/* Audio Visualizer */}
          <div className="flex justify-center items-end space-x-1 mt-12">
            {[...Array(20)].map((_, i) => (
              <div
                key={i}
                className="wave-bar bg-gradient-to-t from-primary-500 to-purple-400 w-2 rounded-full"
                style={{
                  height: `${Math.random() * 40 + 10}px`,
                  animationDelay: `${i * 0.1}s`
                }}
              ></div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}