import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { 
  Brain, 
  MessageSquare, 
  Loader2, 
  CheckCircle, 
  Clock, 
  Search as SearchIcon, 
  FileText, 
  Globe, 
  ChevronDown, 
  ChevronRight,
  Lightbulb,
  Database,
  Zap,
  Target
} from "lucide-react"

type Source = {
  type: "document" | "web"
  title?: string
  url?: string
  text_preview?: string
  page_number?: number
  similarity_score?: number
  document_name?: string
}

type ReasoningStep = {
  node: string
  stage: string
  action: string
  analysis?: any
  results_count?: number
  avg_similarity?: number
  local_sufficient?: boolean
  metrics?: any
  timestamp: string
}

type RAGResponse = {
  answer?: string
  confidence?: number
  retrieval_method?: string
  sources?: Source[]
  reasoning_steps?: ReasoningStep[]
  processing_time_ms?: number
  workflow_metadata?: {
    iterations_performed: number
    workflow_type: string
    stages_completed: number
    workflow_time_ms: number
    final_confidence: number
  }
  detail?: string
}

export default function Search() {
  const [question, setQuestion] = useState("")
  const [resp, setResp] = useState<RAGResponse | null>(null)
  const [message, setMessage] = useState("")
  const [busy, setBusy] = useState(false)
  const [showReasoningDetails, setShowReasoningDetails] = useState(false)
  const navigate = useNavigate()

  // Example questions for better UX
  const exampleQuestions = [
    "What is RAG and how does it work?",
    "What are the main challenges in RAG evaluation?",
    "How can I improve retrieval quality in RAG systems?",
    "What are the latest advances in RAG architectures?",
  ]

  useEffect(() => {
    const token = localStorage.getItem("token")
    if (!token) navigate("/login")
  }, [navigate])

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setMessage("")
    setResp(null)
    const token = localStorage.getItem("token")

    try {
      const res = await fetch("http://localhost:8000/rag/ask-advanced", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          question,
          max_iterations: 3,
          enable_detailed_reasoning: true,
        }),
      })

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}))
        throw new Error(errJson.detail || "Search failed")
      }

      const data: RAGResponse = await res.json()
      setResp(data)
    } catch (err: any) {
      setMessage(err.message || "Error searching")
    } finally {
      setBusy(false)
    }
  }

  const getStageIcon = (stage: string) => {
    switch (stage) {
      case "planning":
        return <Lightbulb className="w-4 h-4 text-yellow-500" />
      case "retrieval":
        return <Database className="w-4 h-4 text-blue-500" />
      case "evaluation":
        return <Target className="w-4 h-4 text-purple-500" />
      case "synthesis":
        return <Zap className="w-4 h-4 text-green-500" />
      default:
        return <Clock className="w-4 h-4 text-gray-400" />
    }
  }

  const formatConfidence = (confidence: number) => {
    if (confidence >= 0.8) return { color: "text-green-600", bg: "bg-green-100", label: "High" }
    if (confidence >= 0.6) return { color: "text-yellow-600", bg: "bg-yellow-100", label: "Medium" }
    return { color: "text-red-600", bg: "bg-red-100", label: "Low" }
  }

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Header */}
      <div className="text-center">
        <div className="flex justify-center mb-4">
          <div className="p-4 bg-primary-100 rounded-full">
            <Brain className="w-12 h-12 text-primary-600" />
          </div>
        </div>
        <h1 className="text-3xl font-bold text-gray-900">AI Research Assistant</h1>
        <p className="mt-2 text-lg text-gray-600">
          Ask questions about your documents using advanced RAG technology
        </p>
      </div>

      {/* Search Form */}
      <div className="card">
        <form onSubmit={handleSearch} className="space-y-6">
          <div>
            <label htmlFor="question" className="block text-sm font-medium text-gray-700 mb-2">
              Your Question
            </label>
            <div className="relative">
              <textarea
                id="question"
                rows={4}
                className="textarea pr-12"
                placeholder="Ask anything about your uploaded documents..."
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                disabled={busy}
              />
              <div className="absolute bottom-3 right-3">
                <MessageSquare className="w-5 h-5 text-gray-400" />
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between">
            <button
              type="submit"
              disabled={!question.trim() || busy}
              className="btn-primary flex items-center space-x-2 px-6"
            >
              {busy ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Thinking...</span>
                </>
              ) : (
                <>
                  <SearchIcon className="w-4 h-4" />
                  <span>Ask AI</span>
                </>
              )}
            </button>

            {resp && (
              <div className="flex items-center space-x-4 text-sm text-gray-500">
                <div className="flex items-center space-x-1">
                  <Clock className="w-4 h-4" />
                  <span>{Math.round(resp.processing_time_ms || 0)}ms</span>
                </div>
                {resp.workflow_metadata && (
                  <div className="flex items-center space-x-1">
                    <Zap className="w-4 h-4" />
                    <span>{resp.workflow_metadata.stages_completed} stages</span>
                  </div>
                )}
              </div>
            )}
          </div>
        </form>

        {/* Example Questions */}
        {!resp && !busy && (
          <div className="mt-6 pt-6 border-t border-gray-200">
            <p className="text-sm text-gray-600 mb-3">Try these example questions:</p>
            <div className="flex flex-wrap gap-2">
              {exampleQuestions.map((q, i) => (
                <button
                  key={i}
                  onClick={() => setQuestion(q)}
                  className="text-sm bg-gray-100 hover:bg-gray-200 text-gray-700 px-3 py-2 rounded-lg transition-colors"
                  disabled={busy}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Error Message */}
      {message && (
        <div className="card bg-red-50 border-red-200 flex items-center space-x-3">
          <div className="p-1 bg-red-100 rounded-full">
            <SearchIcon className="w-4 h-4 text-red-600" />
          </div>
          <p className="text-red-800">{message}</p>
        </div>
      )}

      {/* Response */}
      {resp && (
        <div className="space-y-6">
          {/* Main Answer */}
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-gray-900">Answer</h2>
              <div className="flex items-center space-x-3">
                {resp.confidence && (
                  <div className={`badge ${formatConfidence(resp.confidence).bg} ${formatConfidence(resp.confidence).color}`}>
                    {Math.round(resp.confidence * 100)}% {formatConfidence(resp.confidence).label} Confidence
                  </div>
                )}
                <div className="badge badge-primary">
                  {resp.retrieval_method?.replace('_', ' ') || 'RAG'}
                </div>
              </div>
            </div>
            
            <div className="prose max-w-none">
              <div className="bg-gray-50 rounded-lg p-6 border-l-4 border-primary-500">
                <div className="whitespace-pre-wrap text-gray-800 leading-relaxed">
                  {resp.answer || "No answer provided"}
                </div>
              </div>
            </div>
          </div>

          {/* Sources */}
          {resp.sources && resp.sources.length > 0 && (
            <div className="card">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                Sources ({resp.sources.length})
              </h3>
              <div className="grid gap-4">
                {resp.sources.map((source, i) => (
                  <div key={i} className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition-colors">
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center space-x-3">
                        <div className="p-2 bg-gray-100 rounded-lg">
                          {source.type === "document" ? (
                            <FileText className="w-4 h-4 text-blue-600" />
                          ) : (
                            <Globe className="w-4 h-4 text-green-600" />
                          )}
                        </div>
                        <div>
                          <h4 className="font-medium text-gray-900">
                            {source.title || source.document_name || "Untitled"}
                          </h4>
                          {source.type === "document" && source.page_number && (
                            <p className="text-sm text-gray-500">Page {source.page_number}</p>
                          )}
                          {source.type === "web" && source.url && (
                            <a 
                              href={source.url} 
                              target="_blank" 
                              rel="noreferrer"
                              className="text-sm text-primary-600 hover:text-primary-700"
                            >
                              {source.url}
                            </a>
                          )}
                        </div>
                      </div>
                      {source.similarity_score && (
                        <div className="badge badge-gray">
                          {Math.round(source.similarity_score * 100)}% match
                        </div>
                      )}
                    </div>
                    <div className="text-sm text-gray-600 bg-white rounded p-3 border">
                      {source.text_preview || "No preview available"}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Reasoning Chain */}
          {resp.reasoning_steps && resp.reasoning_steps.length > 0 && (
            <div className="card">
              <button
                onClick={() => setShowReasoningDetails(!showReasoningDetails)}
                className="flex items-center justify-between w-full text-left"
              >
                <h3 className="text-lg font-semibold text-gray-900">
                  AI Reasoning Process ({resp.reasoning_steps.length} steps)
                </h3>
                {showReasoningDetails ? (
                  <ChevronDown className="w-5 h-5 text-gray-400" />
                ) : (
                  <ChevronRight className="w-5 h-5 text-gray-400" />
                )}
              </button>

              {showReasoningDetails && (
                <div className="mt-6 space-y-4">
                  {resp.reasoning_steps.map((step, idx) => (
                    <div key={idx} className="border border-gray-200 rounded-lg p-4">
                      <div className="flex items-center space-x-3 mb-3">
                        <div className="flex-shrink-0">
                          {getStageIcon(step.stage)}
                        </div>
                        <div className="flex-grow">
                          <div className="flex items-center space-x-2">
                            <span className="font-medium text-gray-900 capitalize">
                              {step.stage}
                            </span>
                            <span className="text-sm text-gray-500">•</span>
                            <span className="text-sm text-gray-600">
                              {step.node.replace('_', ' ')}
                            </span>
                          </div>
                          <p className="text-sm text-gray-600 mt-1">{step.action}</p>
                        </div>
                        <div className="text-xs text-gray-400">
                          Step {idx + 1}
                        </div>
                      </div>

                      {/* Step Details */}
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                        {step.results_count !== undefined && (
                          <div className="bg-blue-50 rounded p-2">
                            <span className="font-medium text-blue-800">Results:</span>
                            <span className="ml-1 text-blue-600">{step.results_count}</span>
                          </div>
                        )}
                        {step.avg_similarity !== undefined && (
                          <div className="bg-purple-50 rounded p-2">
                            <span className="font-medium text-purple-800">Avg Similarity:</span>
                            <span className="ml-1 text-purple-600">{(step.avg_similarity * 100).toFixed(1)}%</span>
                          </div>
                        )}
                        {step.local_sufficient !== undefined && (
                          <div className={`rounded p-2 ${step.local_sufficient ? 'bg-green-50' : 'bg-yellow-50'}`}>
                            <span className={`font-medium ${step.local_sufficient ? 'text-green-800' : 'text-yellow-800'}`}>
                              Local Sufficient:
                            </span>
                            <span className={`ml-1 ${step.local_sufficient ? 'text-green-600' : 'text-yellow-600'}`}>
                              {step.local_sufficient ? 'Yes' : 'No'}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Workflow Metadata */}
          {resp.workflow_metadata && (
            <div className="card bg-gray-50">
              <h4 className="font-medium text-gray-900 mb-3">Workflow Summary</h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <span className="text-gray-600">Iterations:</span>
                  <span className="ml-2 font-medium">{resp.workflow_metadata.iterations_performed}</span>
                </div>
                <div>
                  <span className="text-gray-600">Stages:</span>
                  <span className="ml-2 font-medium">{resp.workflow_metadata.stages_completed}</span>
                </div>
                <div>
                  <span className="text-gray-600">Workflow Time:</span>
                  <span className="ml-2 font-medium">{Math.round(resp.workflow_metadata.workflow_time_ms)}ms</span>
                </div>
                <div>
                  <span className="text-gray-600">Final Confidence:</span>
                  <span className="ml-2 font-medium">{Math.round(resp.workflow_metadata.final_confidence * 100)}%</span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
