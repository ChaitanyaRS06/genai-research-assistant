import { useState } from "react"

export default function Docs() {
  const [file, setFile] = useState<File | null>(null)
  const [message, setMessage] = useState("")

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault()

    if (!file) {
      setMessage("❌ No file selected")
      return
    }

    const token = localStorage.getItem("token")
    const formData = new FormData()
    formData.append("file", file)

    try {
      const response = await fetch("http://localhost:8000/documents/upload", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      })

      if (!response.ok) throw new Error("Upload failed")

      setMessage("✅ Document uploaded successfully")
    } catch (err) {
      setMessage("❌ Upload failed")
    }
  }

  return (
    <div>
      <h1>Upload Document</h1>
      <form onSubmit={handleUpload}>
        <input type="file" onChange={(e) => setFile(e.target.files?.[0] || null)} />
        <br />
        <button type="submit">Upload</button>
      </form>
      <p>{message}</p>
    </div>
  )
}
