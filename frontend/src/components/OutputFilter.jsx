import React from 'react'

const OutputFilter = ({ original, filtered, loading }) => {
  return (
    <div className="glass rounded-2xl p-5 hover-card">
      <h3 className="font-semibold text-gray-100 mb-3">Output Filtering</h3>
      {loading ? (
        <div className="space-y-3">
          <div className="h-4 w-5/6 bg-gray-800 rounded shimmer" />
          <div className="h-4 w-4/6 bg-gray-800 rounded shimmer" />
          <div className="h-4 w-3/6 bg-gray-800 rounded shimmer" />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-gray-900/80 rounded-lg border border-gray-700 p-4">
            <h4 className="text-xs uppercase tracking-wide text-gray-400 mb-2">Original</h4>
            <pre className="whitespace-pre-wrap break-words text-sm leading-relaxed text-gray-200 min-h-[84px]">{original || '—'}</pre>
          </div>
          <div className="bg-gray-900/80 rounded-lg border border-gray-700 p-4">
            <h4 className="text-xs uppercase tracking-wide text-gray-400 mb-2">Filtered</h4>
            <pre className="whitespace-pre-wrap break-words text-sm leading-relaxed text-gray-200 min-h-[84px]">{filtered || '—'}</pre>
          </div>
        </div>
      )}
    </div>
  )
}

export default OutputFilter
