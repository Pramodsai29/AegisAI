import React from 'react'

const badgeClasses = (cat) => {
  switch ((cat || '').toLowerCase()) {
    case 'medical':
      return 'bg-rose-500/10 text-rose-300 border-rose-400/30'
    case 'financial':
      return 'bg-amber-500/10 text-amber-300 border-amber-400/30'
    case 'personal':
      return 'bg-sky-500/10 text-sky-300 border-sky-400/30'
    default:
      return 'bg-emerald-500/10 text-emerald-300 border-emerald-400/30'
  }
}

const ContextAnalysis = ({ category, confidence, loading }) => {
  return (
    <div className="glass rounded-2xl p-5 hover-card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-gray-100">Contextual Analysis</h3>
        <span className={`px-2 py-1 text-xs rounded-md border ${badgeClasses(category)}`}>
          {category ? category : '—'}
        </span>
      </div>

      {loading ? (
        <div className="space-y-3">
          <div className="h-4 w-40 bg-gray-800 rounded shimmer" />
          <div className="h-3 w-full bg-gray-800 rounded shimmer" />
        </div>
      ) : (
        <div>
          <div className="flex items-center justify-between text-xs text-gray-400 mb-2">
            <span>Confidence</span>
            <span>{confidence != null ? `${confidence}%` : '—'}</span>
          </div>
          <div className="h-2 w-full bg-gray-800 rounded overflow-hidden border border-gray-700">
            <div
              className="h-full bg-gradient-to-r from-indigo-500 via-fuchsia-500 to-purple-500"
              style={{ width: `${Math.max(0, Math.min(100, confidence || 0))}%` }}
            />
          </div>
        </div>
      )}
    </div>
  )
}

export default ContextAnalysis
