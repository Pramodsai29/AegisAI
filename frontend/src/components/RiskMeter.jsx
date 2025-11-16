import React from 'react'
import { RadialBarChart, RadialBar, PolarAngleAxis, ResponsiveContainer } from 'recharts'

/**
 * Circular risk visualization using Recharts RadialBarChart.
 * - value: number (0-100)
 * - Computes color based on thresholds: <40 green, <70 yellow, >=70 red
 */
const RiskMeter = ({ value = 0 }) => {
  const clamped = Math.max(0, Math.min(100, value))
  const color = clamped < 40 ? '#22c55e' : clamped < 70 ? '#facc15' : '#ef4444'
  const data = [{ name: 'Risk', value: clamped, fill: color }]

  return (
    <div className="w-full h-64 sm:h-72 glass rounded-2xl shadow-lg hover-card flex flex-col items-center justify-center">
      <div className="text-sm text-gray-300 mb-2">Privacy Risk</div>
      <div className="w-full h-44 sm:h-52">
        <ResponsiveContainer>
          <RadialBarChart
            cx="50%"
            cy="50%"
            innerRadius="70%"
            outerRadius="100%"
            barSize={18}
            data={data}
            startAngle={220}
            endAngle={-40}
          >
            <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
            <RadialBar dataKey="value" cornerRadius={18} background />
          </RadialBarChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-2 text-3xl font-semibold drop-shadow" style={{ color }} aria-label={`Risk score is ${clamped}`}>
        {clamped}
        <span className="text-gray-400 text-xl align-top">%</span>
      </div>
      <div className="text-xs text-gray-400 mt-1">
        {clamped < 40 ? 'Low' : clamped < 70 ? 'Moderate' : 'High'} risk
      </div>
    </div>
  )
}

export default RiskMeter
