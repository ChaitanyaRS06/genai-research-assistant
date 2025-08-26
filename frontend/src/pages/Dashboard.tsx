import { Link, useNavigate } from "react-router-dom"
import { useEffect } from "react"

export default function Dashboard() {
  const navigate = useNavigate()
  useEffect(() => {
    const token = localStorage.getItem("token")
    if (!token) navigate("/login")
  }, [navigate])

  return (
    <div>
      <h1>Dashboard</h1>
      <ul>
        <li><Link to="/upload">📤 Upload Document</Link></li>
        <li><Link to="/search">🔍 Search (Agentic RAG)</Link></li>
      </ul>
    </div>
  )
}
