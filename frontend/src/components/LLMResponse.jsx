import React from 'react'

const LLMResponse = ({ text, loading }) => {
  return (
    <div className="glass rounded-2xl p-5 hover-card">
      <h3 className="font-semibold text-gray-100 mb-3">LLM Response</h3>
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
          <span className="text-gray-500 text-sm">No LLM response yet.</span>
        )}
      </div>
    </div>
  )
}

export default LLMResponse
