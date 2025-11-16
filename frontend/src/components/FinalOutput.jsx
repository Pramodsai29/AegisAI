import React from 'react'

const FinalOutput = ({ text, risk, loading }) => {
  return (
    <div className="glass rounded-2xl p-5 hover-card">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-gray-100">Final Output</h3>
        <span
          className={`inline-flex items-center px-2 py-1 rounded-md text-xs font-medium ${
            (risk ?? 0) < 40
              ? 'bg-green-500/10 text-green-400'
              : (risk ?? 0) < 70
              ? 'bg-yellow-500/10 text-yellow-400'
              : 'bg-red-500/10 text-red-400'
          }`}
        >
          Risk: {risk ?? 0}%
        </span>
      </div>
      <div className="min-h-[96px] bg-gray-900/80 rounded-lg border border-gray-700 p-4 text-gray-100 shadow-inner">
        {loading ? (
          <div className="space-y-3">
            <div className="h-4 w-5/6 bg-gray-800 rounded shimmer" />
            <div className="h-4 w-4/6 bg-gray-800 rounded shimmer" />
            <div className="h-4 w-3/6 bg-gray-800 rounded shimmer" />
          </div>
        ) : text ? (
          <pre className="whitespace-pre-wrap break-words text-sm leading-relaxed">{text}</pre>
        ) : (
          <span className="text-gray-500 text-sm">No final output yet.</span>
        )}
      </div>
    </div>
  )
}

export default FinalOutput
