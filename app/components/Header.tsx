'use client'

import React, { useState } from 'react'
import { FaMusic, FaSearch, FaBars, FaTimes, FaUser } from 'react-icons/fa'

export default function Header() {
  const [isMenuOpen, setIsMenuOpen] = useState(false)

  return (
    <header className="fixed top-0 left-0 right-0 z-50 glass border-b border-white/10">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          {/* Logo */}
          <div className="flex items-center space-x-2">
            <FaMusic className="text-2xl text-primary-400" />
            <h1 className="text-2xl font-bold gradient-text">MUSICANA</h1>
          </div>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center space-x-8">
            <a href="#" className="hover:text-primary-400 transition-colors">Home</a>
            <a href="#" className="hover:text-primary-400 transition-colors">Browse</a>
            <a href="#" className="hover:text-primary-400 transition-colors">Artists</a>
            <a href="#" className="hover:text-primary-400 transition-colors">Playlists</a>
            <a href="#" className="hover:text-primary-400 transition-colors">Radio</a>
          </nav>

          {/* Search and User */}
          <div className="hidden md:flex items-center space-x-4">
            <div className="relative">
              <input
                type="text"
                placeholder="Search music..."
                className="bg-dark-800/50 border border-white/20 rounded-full px-4 py-2 pl-10 focus:outline-none focus:border-primary-400 transition-colors"
              />
              <FaSearch className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
            </div>
            <button className="p-2 hover:bg-white/10 rounded-full transition-colors">
              <FaUser className="text-xl" />
            </button>
          </div>

          {/* Mobile Menu Button */}
          <button
            className="md:hidden text-xl"
            onClick={() => setIsMenuOpen(!isMenuOpen)}
          >
            {isMenuOpen ? <FaTimes /> : <FaBars />}
          </button>
        </div>

        {/* Mobile Menu */}
        {isMenuOpen && (
          <div className="md:hidden mt-4 pb-4">
            <div className="flex flex-col space-y-4">
              <div className="relative mb-4">
                <input
                  type="text"
                  placeholder="Search music..."
                  className="w-full bg-dark-800/50 border border-white/20 rounded-full px-4 py-2 pl-10 focus:outline-none focus:border-primary-400 transition-colors"
                />
                <FaSearch className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
              </div>
              <a href="#" className="hover:text-primary-400 transition-colors">Home</a>
              <a href="#" className="hover:text-primary-400 transition-colors">Browse</a>
              <a href="#" className="hover:text-primary-400 transition-colors">Artists</a>
              <a href="#" className="hover:text-primary-400 transition-colors">Playlists</a>
              <a href="#" className="hover:text-primary-400 transition-colors">Radio</a>
              <button className="flex items-center space-x-2 hover:text-primary-400 transition-colors">
                <FaUser />
                <span>Profile</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </header>
  )
}