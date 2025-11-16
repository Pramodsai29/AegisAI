import React, { useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import RiskMeter from './components/RiskMeter.jsx'
import LogsTable from './components/LogsTable.jsx'
import { Send, Shield, Wand2 } from 'lucide-react'
import Mascot from './components/Mascot.jsx'
import ContextAnalysis from './components/ContextAnalysis.jsx'
import LLMResponse from './components/LLMResponse.jsx'
import OutputFilter from './components/OutputFilter.jsx'
import FinalOutput from './components/FinalOutput.jsx'

// API base
const API = 'http://localhost:5000'

const App = () => {
  const [text, setText] = useState('')
  const [sanitized, setSanitized] = useState('')
  const [risk, setRisk] = useState(0)
  const [lastRisk, setLastRisk] = useState(0)
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(false)
  // Contextual analysis
  const [ctxCategory, setCtxCategory] = useState(null)
  const [ctxConfidence, setCtxConfidence] = useState(null)
  // LLM
  const [llmText, setLlmText] = useState('')
  // Output Filtering
  const [filteredOriginal, setFilteredOriginal] = useState('')
  const [filteredSafe, setFilteredSafe] = useState('')
  // Final Output
  const [finalText, setFinalText] = useState('')
  const [finalRisk, setFinalRisk] = useState(null)
  const [glow, setGlow] = useState({ x: -1000, y: -1000 })

  const clearPipeline = () => {
    setSanitized('')
    setCtxCategory(null)
    setCtxConfidence(null)
    setLlmText('')
    setFilteredOriginal('')
    setFilteredSafe('')
    setFinalText('')
    // Preserve risk and finalRisk so the meter doesn't reset during processing
  }

  useEffect(() => {
    // Optionally perform a health check here
  }, [])

  const handleSanitize = async () => {
    if (!text.trim()) return
    setLoading(true)
    clearPipeline()
    try {
      // 1) Sanitization - Get rehydration_map
      const sanitizeRes = await axios.post(`${API}/api/sanitize`, { input: text }, { timeout: 10000 })
      const out = sanitizeRes.data?.sanitized ?? ''
      const scoreRaw = sanitizeRes.data?.risk ?? sanitizeRes.data?.risk_score ?? 0
      const scoreNum = parseInt(scoreRaw, 10)
      const score = Math.max(0, Math.min(100, Number.isNaN(scoreNum) ? 0 : scoreNum))
      const rehydrationMap = sanitizeRes.data?.rehydration_map ?? {}
      const entities = sanitizeRes.data?.entities ?? []
      setSanitized(out)
      setRisk(score)
      setLastRisk(score)
      setLogs((prev) => [{ text: out, score }, ...prev.slice(0, 19)])

      // 2) Contextual Analysis
      const ctxRes = await axios.post(`${API}/api/context`, { input: text, sanitized: out }, { timeout: 10000 })
      const cat = ctxRes.data?.category ?? null
      const confRaw = ctxRes.data?.confidence ?? null
      const conf = confRaw == null ? null : (confRaw <= 1 ? Math.round(confRaw * 100) : Math.round(confRaw))
      setCtxCategory(cat)
      setCtxConfidence(conf)
      const context = { category: cat, confidence: conf }

      // 3) LLM Response - Pass rehydration_map through (but LLM never sees original values)
      const llmRes = await axios.post(`${API}/api/llm`, { 
        sanitized: out, 
        context: context,
        rehydration_map: rehydrationMap  // Pass through ephemerally
      }, { timeout: 20000 })
      const llmResult = {
        answer: llmRes.data?.answer ?? llmRes.data?.output ?? '',
        confidence: llmRes.data?.confidence ?? 0.0,
        explanations: llmRes.data?.explanations ?? '',
        fallback_used: llmRes.data?.fallback_used ?? false,
        raw: llmRes.data?.raw ?? ''
      }
      const llmRehydrationMap = llmRes.data?.rehydration_map ?? rehydrationMap
      setLlmText(llmResult.answer)

      // 4) Output Filtering - Work on sanitized content, pass rehydration_map through
      const filterRes = await axios.post(`${API}/api/output-filter`, { 
        answer: llmResult.answer,  // LLM answer (should contain placeholders)
        sanitized: out,
        context: context,
        rehydration_map: llmRehydrationMap  // Pass through ephemerally
      }, { timeout: 15000 })
      setFilteredOriginal(llmResult.answer)
      setFilteredSafe(filterRes.data?.safe_sanitized_text ?? llmResult.answer)
      const filterRehydrationMap = filterRes.data?.rehydration_map ?? llmRehydrationMap

      // 5) Final Output - Rehydrate placeholders here
      const finalRes = await axios.post(`${API}/api/final`, { 
        input: text, 
        sanitized: out, 
        llm_result: llmResult,  // Pass full LLM result dict
        filtered_output: {
          safe_sanitized_text: filterRes.data?.safe_sanitized_text ?? llmResult.answer,
          leak_detected: filterRes.data?.leak_detected ?? false,
          notes: filterRes.data?.notes ?? null
        },
        entities: entities,
        context: context,
        rehydration_map: filterRehydrationMap  // Final use - will be deleted after rehydration
      }, { timeout: 15000 })
      
      // Use final_rehydrated_text if available, otherwise fallback
      const finalTextValue = finalRes.data?.final_rehydrated_text ?? finalRes.data?.result ?? filterRes.data?.safe_sanitized_text ?? llmResult.answer
      setFinalText(finalTextValue)
      // Get final output risk (should be low since final output has no PII)
      const finalRaw = finalRes.data?.risk ?? finalRes.data?.risk_score ?? 0
      const finalNum = parseInt(finalRaw, 10)
      const finalR = Math.max(0, Math.min(100, Number.isNaN(finalNum) ? 0 : finalNum))
      setFinalRisk(finalR)
      // DO NOT overwrite lastRisk - keep the original input risk for the risk meter
      // lastRisk should remain as the original input risk (from sanitize step)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      className="min-h-screen bg-gray-900 text-white bg-aurora overflow-hidden"
      onMouseMove={(e) => setGlow({ x: e.clientX, y: e.clientY })}
    >
      <div
        className="cursor-glow"
        style={{ transform: `translate3d(${glow.x - 80}px, ${glow.y - 80}px, 0)` }}
        aria-hidden
      />
      {/* Header */}
      <header className="border-b border-gray-800/70 bg-gray-900/50 backdrop-blur-md sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-4 flex items-center gap-3">
          <Mascot className="w-7 h-7 drop-shadow" />
          <h1 className="text-xl sm:text-2xl font-semibold tracking-tight bg-gradient-to-r from-indigo-300 via-fuchsia-300 to-purple-300 bg-clip-text text-transparent">
            LeakyCauldron Privacy Dashboard
          </h1>
          <div className="ml-auto hidden sm:flex items-center gap-2 text-indigo-300">
            <Shield className="w-5 h-5" />
            <span className="text-sm">AI Privacy</span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-6">

        {/* Organized 12-col grid */}
        <div className="grid grid-cols-12 gap-6 relative z-10">
          {/* Left Column: User & Sanitization */}
          <section className="col-span-12 lg:col-span-7 space-y-6">
            <div className="px-1">
              <h2 className="text-sm uppercase tracking-wider text-gray-400">Sanitization</h2>
            </div>
            {/* Input Panel */}
            <div className="glass rounded-2xl p-5 hover-card">
              <div className="flex items-center gap-2 mb-3">
                <Wand2 className="w-5 h-5 text-indigo-400" />
                <h2 className="font-semibold text-gray-100">Input</h2>
              </div>
              <label htmlFor="prompt" className="sr-only">Prompt</label>
              <textarea
                id="prompt"
                placeholder="Type a prompt that may contain sensitive info (emails, phone numbers, IDs)..."
                className="w-full h-36 sm:h-44 resize-y bg-gray-900 text-gray-100 placeholder-gray-500 rounded-lg p-4 border border-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/60 focus:border-indigo-500/60 shadow-lg shadow-indigo-950/30 transition"
                value={text}
                onChange={(e) => setText(e.target.value)}
              />
              <div className="mt-4 flex items-center justify-between">
                <div className="text-xs text-gray-400">
                  Press Sanitize to redact sensitive elements.
                </div>
                <button
                  onClick={handleSanitize}
                  disabled={loading || !text.trim()}
                  className={`${
                    loading || !text.trim()
                      ? 'bg-indigo-900/40 text-indigo-300 cursor-not-allowed'
                      : 'bg-gradient-to-r from-indigo-600 via-fuchsia-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white btn-neon btn-sparkle'
                  } inline-flex items-center gap-2 px-4 py-2 rounded-lg transition focus:outline-none focus:ring-2 focus:ring-indigo-500/60`}
                >
                  <Send className="w-4 h-4" />
                  {loading ? (
                    <span className="inline-flex items-center">Sanitizing<span className="dots" aria-hidden><span className="dot"></span><span className="dot"></span><span className="dot"></span></span></span>
                  ) : (
                    'Sanitize'
                  )}
                </button>
              </div>
            </div>

            {/* Output Panel */}
            <div className="glass rounded-2xl p-5 hover-card">
              <div className="flex items-center gap-2 mb-3">
                <h2 className="font-semibold text-gray-100">Sanitized Output</h2>
              </div>
              <div className="min-h-[96px] bg-gray-900/80 rounded-lg border border-gray-700 p-4 text-gray-100 shadow-inner">
                {loading ? (
                  <div className="space-y-3">
                    <div className="h-4 w-5/6 bg-gray-800 rounded shimmer" />
                    <div className="h-4 w-4/6 bg-gray-800 rounded shimmer" />
                    <div className="h-4 w-3/6 bg-gray-800 rounded shimmer" />
                  </div>
                ) : sanitized ? (
                  <pre className="whitespace-pre-wrap break-words text-sm leading-relaxed">
                    {sanitized}
                  </pre>
                ) : (
                  <span className="text-gray-500 text-sm">
                    Output will appear here after sanitization.
                  </span>
                )}
              </div>
            </div>

            {/* Contextual Analysis */}
            <ContextAnalysis category={ctxCategory} confidence={ctxConfidence} loading={loading && !ctxCategory} />

            {/* LLM Response */}
            <LLMResponse text={llmText} loading={loading && !llmText} />

            {/* Output Filtering */}
            <OutputFilter original={filteredOriginal} filtered={filteredSafe} loading={loading && !filteredSafe} />
          </section>

          {/* Right Column: Insights */}
          <section className="col-span-12 lg:col-span-5 space-y-6">
            <div className="px-1">
              <h2 className="text-sm uppercase tracking-wider text-gray-400">Insights</h2>
            </div>
            <RiskMeter value={lastRisk} />
            <LogsTable logs={logs} maxHeight={360} />

            {/* Final Output */}
            <FinalOutput text={finalText} risk={finalRisk ?? lastRisk} loading={loading && !finalText} />
          </section>
        </div>
      </main>
    </div>
  )
}

export default App
