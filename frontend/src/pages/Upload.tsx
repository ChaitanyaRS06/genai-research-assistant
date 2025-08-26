import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"

export default function Upload() {
  const [file, setFile] = useState<File | null>(null)
  const [message, setMessage] = useState("")
  const [busy, setBusy] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    const token = localStorage.getItem("token")
    if (!token) navigate("/login")
  }, [navigate])

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault()
    if (!file) return
    const token = localStorage.getItem("token")
    setBusy(true)
    setMessage("")
    try {
      // 1) upload
      const fd = new FormData()
      fd.append("file", file)
      const up = await fetch("http://localhost:8000/documents/upload", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: fd,
      })
      if (!up.ok) throw new Error((await up.json().catch(() => ({}))).detail || "Upload failed")
      const uploaded = await up.json()

      // 2) process
      const proc = await fetch(`http://localhost:8000/documents/${uploaded.id}/process`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!proc.ok) throw new Error((await proc.json().catch(() => ({}))).detail || "Process failed")

      // 3) embeddings
      const emb = await fetch(`http://localhost:8000/embeddings/generate/${uploaded.id}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!emb.ok) throw new Error((await emb.json().catch(() => ({}))).detail || "Embeddings failed")

      setMessage("✅ Uploaded, processed, and embedded. Ready for search!")
    } catch (err: any) {
      setMessage(`❌ ${err.message || "Upload pipeline failed"}`)
    } finally {
      setBusy(false)
      setFile(null)
    }
  }

  return (
    <div>
      <h1>Upload Document</h1>
      <form onSubmit={handleUpload} style={{ display: "grid", gap: 8, maxWidth: 420 }}>
        <input type="file" accept=".pdf" onChange={(e) => setFile(e.target.files?.[0] || null)} />
        <button type="submit" disabled={!file || busy}>{busy ? "Working…" : "Upload & Process"}</button>
      </form>
      {message && <p style={{ marginTop: 8 }}>{message}</p>}
    </div>
  )
}
