import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"

type Source = {
  type: "document" | "web"
  title?: string
  url?: string
  text_preview?: string
  page_number?: number
  similarity_score?: number
  document_name?: string
}

type RAGResponse = {
  answer?: string
  confidence?: number
  retrieval_method?: string
  sources?: Source[]
  reasoning_steps?: any[]
  processing_time_ms?: number
  detail?: string
}

export default function Search() {
  const [question, setQuestion] = useState("")
  const [resp, setResp] = useState<RAGResponse | null>(null)
  const [message, setMessage] = useState("")
  const [busy, setBusy] = useState(false)
  const navigate = useNavigate()

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
      setMessage(`❌ ${err.message || "Error searching"}`)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <h1>Search (Agentic RAG)</h1>
      <form onSubmit={handleSearch} style={{ display: "grid", gap: 8, maxWidth: 640 }}>
        <textarea
          placeholder="Ask a question about your documents…"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          rows={3}
        />
        <button type="submit" disabled={!question.trim() || busy}>
          {busy ? "Thinking…" : "Search"}
        </button>
      </form>

      {message && <p style={{ marginTop: 8 }}>{message}</p>}

      {resp && (
        <div style={{ marginTop: 16 }}>
          <div style={{ border: "1px solid #eee", padding: 12 }}>
            <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
              {typeof resp.confidence === "number" && (
                <span style={{ fontSize: 12, background: "#eef", padding: "2px 6px", borderRadius: 4 }}>
                  {Math.round(resp.confidence * 100)}% confidence
                </span>
              )}
              {resp.retrieval_method && (
                <span style={{ fontSize: 12, background: "#efe", padding: "2px 6px", borderRadius: 4 }}>
                  {resp.retrieval_method}
                </span>
              )}
            </div>
            <pre style={{ whiteSpace: "pre-wrap" }}>{resp.answer || "No answer"}</pre>
            {resp.processing_time_ms && (
              <div style={{ marginTop: 6, fontSize: 12, color: "#666" }}>
                Processing: {Math.round(resp.processing_time_ms)} ms
              </div>
            )}
          </div>

          {resp.sources && resp.sources.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <h3>Sources ({resp.sources.length})</h3>
              <ul style={{ display: "grid", gap: 8, paddingLeft: 0 }}>
                {resp.sources.map((s, i) => (
                  <li key={i} style={{ listStyle: "none", border: "1px solid #eee", padding: 10 }}>
                    <div style={{ display: "flex", gap: 8, fontSize: 12, marginBottom: 4 }}>
                      <span style={{ background: s.type === "document" ? "#efe" : "#eef", padding: "2px 6px", borderRadius: 4 }}>
                        {s.type}
                      </span>
                      {typeof s.similarity_score === "number" && (
                        <span style={{ background: "#f7f7ff", padding: "2px 6px", borderRadius: 4 }}>
                          {Math.round(s.similarity_score * 100)}% match
                        </span>
                      )}
                    </div>
                    <div style={{ fontWeight: 600 }}>
                      {s.title || s.document_name || "Untitled"}
                    </div>
                    {s.url && (
                      <div>
                        <a href={s.url} target="_blank" rel="noreferrer">{s.url}</a>
                      </div>
                    )}
                    {typeof s.page_number === "number" && (
                      <div style={{ fontSize: 12, color: "#666" }}>Page: {s.page_number}</div>
                    )}
                    <div style={{ marginTop: 6, fontSize: 14 }}>
                      {s.text_preview || "No preview available"}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {resp.reasoning_steps && resp.reasoning_steps.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <h3>Agentic Reasoning</h3>
              <ol>
                {resp.reasoning_steps.map((st, idx) => (
                  <li key={idx}><pre style={{ whiteSpace: "pre-wrap" }}>{JSON.stringify(st, null, 2)}</pre></li>
                ))}
              </ol>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
