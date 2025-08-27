import { Link } from "react-router-dom"

export default function Home() {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null
  return (
    <div>
      <h1>GenAI Knowledge Analyst</h1>
      <p>Log in to upload documents and run RAG searches.</p>
      {!token ? (
        <p><Link to="/login">Go to Login →</Link></p>
      ) : (
        <p><Link to="/dashboard">Open Dashboard →</Link></p>
      )}
    </div>
  )
}
