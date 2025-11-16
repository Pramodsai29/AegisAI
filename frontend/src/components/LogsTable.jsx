import React from 'react'

/**
 * Logs table for recent sanitized outputs.
 * - logs: Array<{ text: string, score: number }>
 */
const LogsTable = ({ logs, maxHeight = 360 }) => {
  return (
    <div className="glass rounded-2xl shadow-lg overflow-hidden hover-card">
      <div className="px-4 py-3 border-b border-gray-700/60">
        <h3 className="font-semibold bg-gradient-to-r from-indigo-200 via-fuchsia-200 to-purple-200 bg-clip-text text-transparent">
          Recent Sanitized Logs
        </h3>
      </div>
      <div className="overflow-x-auto" style={{ maxHeight }}>
        <table className="min-w-full text-sm">
          <thead className="bg-gray-800/60 sticky top-0 z-10 backdrop-blur supports-[backdrop-filter]:bg-gray-800/40">
            <tr className="text-left text-gray-300">
              <th className="px-4 py-3 border-b border-gray-700/60">#</th>
              <th className="px-4 py-3 border-b border-gray-700/60">Sanitized Text</th>
              <th className="px-4 py-3 border-b border-gray-700/60">Risk Score</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700/60">
            {logs.length === 0 ? (
              <tr>
                <td className="px-4 py-4 text-gray-400" colSpan={3}>
                  No logs yet. Sanitize your first prompt.
                </td>
              </tr>
            ) : (
              logs.map((row, idx) => (
                <tr key={idx} className="transition-colors hover:bg-gray-900/40">
                  <td className="px-4 py-3 text-gray-400">{idx + 1}</td>
                  <td className="px-4 py-3 text-gray-100">{row.text}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center px-2 py-1 rounded-md text-xs font-medium shadow ${
                        row.score < 40
                          ? 'bg-green-500/10 text-green-400 shadow-green-500/20'
                          : row.score < 70
                          ? 'bg-yellow-500/10 text-yellow-300 shadow-yellow-500/20'
                          : 'bg-red-500/10 text-red-400 shadow-red-500/20'
                      }`}
                    >
                      {row.score}%
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default LogsTable
