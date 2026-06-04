'use client'

import { useState, useEffect } from 'react'
import { ArrowLeft, Save, Loader2 } from 'lucide-react'
import Link from 'next/link'
import { settingsApi } from '@/lib/api'

const MODEL_OPTIONS = [
  { value: 'gpt-4o-mini', label: 'GPT-4o Mini (OpenAI)' },
  { value: 'gpt-4o', label: 'GPT-4o (OpenAI)' },
  { value: 'anthropic/claude-3-5-sonnet-20241022', label: 'Claude 3.5 Sonnet (Anthropic)' },
  { value: 'anthropic/claude-3-opus-20240229', label: 'Claude 3 Opus (Anthropic)' },
  { value: 'gemini/gemini-1.5-flash', label: 'Gemini 1.5 Flash (Google)' },
  { value: 'gemini/gemini-1.5-pro', label: 'Gemini 1.5 Pro (Google)' },
  { value: 'gemini/gemini-2.5-flash', label: 'Gemini 2.5 Flash (Google)' },
  { value: 'gemini/gemini-2.5-pro', label: 'Gemini 2.5 Pro (Google)' },
  { value: 'groq/llama-3.3-70b-versatile', label: 'Llama 3.3 70b (Groq)' },
  { value: 'groq/mixtral-8x7b-32768', label: 'Mixtral 8x7b (Groq)' },
  { value: 'custom', label: 'Custom Model...' },
]

const EMBEDDING_OPTIONS = [
  { value: 'text-embedding-3-small', label: 'text-embedding-3-small' },
  { value: 'text-embedding-3-large', label: 'text-embedding-3-large' },
]

const REASONING_OPTIONS = [
  { value: '', label: 'None' },
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
]

export default function SettingsPage() {
  const [settings, setSettings] = useState<Record<string, unknown>>({})
  const [defaults, setDefaults] = useState<Record<string, unknown>>({})
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    settingsApi.get().then((data) => {
      setSettings(data.settings)
      setDefaults(data.defaults)
      setIsLoading(false)
    })
  }, [])

  const handleSave = async () => {
    setIsSaving(true)
    setSaved(false)
    try {
      const result = await settingsApi.update(settings)
      setSettings(result.settings)
      setDefaults(result.defaults)
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } finally {
      setIsSaving(false)
    }
  }

  const setValue = (key: string, value: unknown) => {
    setSettings((prev) => ({ ...prev, [key]: value }))
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  const Field = ({ label, children, defaultHint }: { label: string; children: React.ReactNode; defaultHint?: string }) => (
    <div>
      <label className="block text-sm font-medium mb-1.5">{label}</label>
      {children}
      {defaultHint && <p className="text-xs text-muted-foreground mt-1">Default: {defaultHint}</p>}
    </div>
  )

  const ModelSelector = ({
    label,
    settingKey,
    defaultHint,
    allowUseDefault = false,
  }: {
    label: string
    settingKey: string
    defaultHint?: string
    allowUseDefault?: boolean
  }) => {
    const currentValue = settings[settingKey] !== undefined ? String(settings[settingKey] || '') : ''
    
    // Check if the current value is a predefined option
    const isPredefined = MODEL_OPTIONS.some((o) => o.value === currentValue) || (allowUseDefault && currentValue === '')
    const selectValue = isPredefined ? currentValue : 'custom'

    const handleSelectChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
      const val = e.target.value
      if (val === 'custom') {
        setValue(settingKey, 'custom-model') // Default placeholder
      } else {
        setValue(settingKey, val === '' ? null : val)
      }
    }

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      setValue(settingKey, e.target.value)
    }

    return (
      <Field label={label} defaultHint={defaultHint}>
        <div className="space-y-2">
          <select
            value={selectValue}
            onChange={handleSelectChange}
            className="w-full px-3 py-2 rounded-lg border border-input bg-background text-sm"
          >
            {allowUseDefault && <option value="">(use default)</option>}
            {MODEL_OPTIONS.map((o) => (
              o.value !== 'custom' && <option key={o.value} value={o.value}>{o.label}</option>
            ))}
            <option value="custom">Custom Model...</option>
          </select>
          {selectValue === 'custom' && (
            <input
              type="text"
              value={currentValue}
              onChange={handleInputChange}
              placeholder="e.g. groq/llama-3.3-70b-versatile or ollama/gemma2"
              className="w-full px-3 py-2 rounded-lg border border-primary bg-background text-sm focus:ring-1 focus:ring-primary focus:outline-none"
            />
          )}
        </div>
      </Field>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card sticky top-0 z-10">
        <div className="container mx-auto px-4 py-4 flex items-center gap-4">
          <Link
            href="/"
            className="inline-flex items-center justify-center rounded-md text-sm font-medium h-9 w-9 hover:bg-accent"
          >
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <h1 className="text-xl font-bold">Settings</h1>
          <div className="flex-1" />
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="inline-flex items-center gap-2 rounded-lg text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 h-10 px-6"
          >
            {isSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            {saved ? 'Saved!' : 'Save'}
          </button>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8 max-w-2xl">
        <div className="space-y-8">
          {/* Models */}
          <section className="border rounded-xl bg-card p-6">
            <h2 className="text-lg font-semibold mb-4">Models</h2>
            <div className="space-y-4">
              <ModelSelector
                label="Default Model"
                settingKey="default_model"
                defaultHint={String(defaults.default_model)}
              />

              <Field label="Embedding Model" defaultHint={String(defaults.default_embedding_model)}>
                <select
                  value={String(settings.default_embedding_model)}
                  onChange={(e) => setValue('default_embedding_model', e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-input bg-background text-sm"
                >
                  {EMBEDDING_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </Field>

              <ModelSelector
                label="Triage Model (fast/cheap tasks)"
                settingKey="triage_model"
                defaultHint={String(defaults.triage_model || String(defaults.default_model))}
                allowUseDefault={true}
              />

              <ModelSelector
                label="Summarization Model"
                settingKey="summarization_model"
                defaultHint={String(defaults.summarization_model || String(defaults.default_model))}
                allowUseDefault={true}
              />

              <ModelSelector
                label="Answer Model (RAG responses)"
                settingKey="answer_model"
                defaultHint={String(defaults.answer_model || String(defaults.default_model))}
                allowUseDefault={true}
              />
            </div>
          </section>

          {/* Parameters */}
          <section className="border rounded-xl bg-card p-6">
            <h2 className="text-lg font-semibold mb-4">Parameters</h2>
            <div className="space-y-4">
              <Field label={`Temperature: ${settings.temperature}`} defaultHint={String(defaults.temperature)}>
                <input
                  type="range"
                  min="0"
                  max="2"
                  step="0.1"
                  value={Number(settings.temperature)}
                  onChange={(e) => setValue('temperature', parseFloat(e.target.value))}
                  className="w-full"
                />
              </Field>

              <Field label="Max Tokens" defaultHint={String(defaults.max_tokens)}>
                <input
                  type="number"
                  value={Number(settings.max_tokens)}
                  onChange={(e) => setValue('max_tokens', parseInt(e.target.value))}
                  min={256}
                  max={128000}
                  className="w-full px-3 py-2 rounded-lg border border-input bg-background text-sm"
                />
              </Field>

              <Field label="Reasoning Effort" defaultHint={String(defaults.reasoning_effort || 'none')}>
                <select
                  value={String(settings.reasoning_effort || '')}
                  onChange={(e) => setValue('reasoning_effort', e.target.value || null)}
                  className="w-full px-3 py-2 rounded-lg border border-input bg-background text-sm"
                >
                  {REASONING_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </Field>
            </div>
          </section>

          {/* Search */}
          <section className="border rounded-xl bg-card p-6">
            <h2 className="text-lg font-semibold mb-4">Search</h2>
            <div className="space-y-4">
              <Field label="Results per Term" defaultHint={String(defaults.search_results_per_term)}>
                <input
                  type="number"
                  value={Number(settings.search_results_per_term)}
                  onChange={(e) => setValue('search_results_per_term', parseInt(e.target.value))}
                  min={5}
                  max={50}
                  className="w-full px-3 py-2 rounded-lg border border-input bg-background text-sm"
                />
              </Field>

              <Field label="Pre-selected Count (Smart mode)" defaultHint={String(defaults.pre_selected_count)}>
                <input
                  type="number"
                  value={Number(settings.pre_selected_count)}
                  onChange={(e) => setValue('pre_selected_count', parseInt(e.target.value))}
                  min={0}
                  max={20}
                  className="w-full px-3 py-2 rounded-lg border border-input bg-background text-sm"
                />
              </Field>
            </div>
          </section>

          {/* RAG */}
          <section className="border rounded-xl bg-card p-6">
            <h2 className="text-lg font-semibold mb-4">RAG</h2>
            <div className="space-y-4">
              <Field label="Top-K Chunks" defaultHint={String(defaults.top_k_results)}>
                <input
                  type="number"
                  value={Number(settings.top_k_results)}
                  onChange={(e) => setValue('top_k_results', parseInt(e.target.value))}
                  min={1}
                  max={50}
                  className="w-full px-3 py-2 rounded-lg border border-input bg-background text-sm"
                />
              </Field>

              <Field label={`Similarity Threshold: ${settings.similarity_threshold}`} defaultHint={String(defaults.similarity_threshold)}>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={Number(settings.similarity_threshold)}
                  onChange={(e) => setValue('similarity_threshold', parseFloat(e.target.value))}
                  className="w-full"
                />
              </Field>
            </div>
          </section>
        </div>
      </main>
    </div>
  )
}
