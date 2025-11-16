import React from 'react'

// Simple wizard hat mascot SVG
const Mascot = ({ className = 'w-6 h-6' }) => (
  <svg
    className={className}
    viewBox="0 0 64 64"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
  >
    <defs>
      <linearGradient id="hatGrad" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stopColor="#6366f1" />
        <stop offset="50%" stopColor="#a855f7" />
        <stop offset="100%" stopColor="#ec4899" />
      </linearGradient>
    </defs>
    <path d="M6 48c10-6 20-9 26-28 6 19 16 22 26 28 2 1 1 4-2 4H8c-3 0-4-3-2-4z" fill="url(#hatGrad)" />
    <ellipse cx="32" cy="50" rx="22" ry="4" fill="#0f172a" opacity="0.6" />
    <circle cx="44" cy="20" r="3" fill="#fde047" />
    <circle cx="20" cy="26" r="2" fill="#f472b6" />
    <circle cx="36" cy="30" r="1.6" fill="#4ade80" />
  </svg>
)

export default Mascot
