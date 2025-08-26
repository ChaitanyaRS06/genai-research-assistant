import { Link, Outlet, useLocation, useNavigate } from "react-router-dom"

export default function App() {
  const location = useLocation()
  const navigate = useNavigate()
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null

  function logout() {
    localStorage.removeItem("token")
    navigate("/login")
  }

  const isAuthed = !!token

  return (
    <div>
      <nav style={{ padding: "10px 16px", borderBottom: "1px solid #eee" }}>
        <ul style={{ display: "flex", gap: "16px", alignItems: "center", listStyle: "none", margin: 0 }}>
          <li><Link to="/">Home</Link></li>
          {!isAuthed && <li><Link to="/login">Login</Link></li>}
          {isAuthed && (
            <>
              <li><Link to="/dashboard">Dashboard</Link></li>
              <li><Link to="/upload">Upload</Link></li>
              <li><Link to="/search">Search</Link></li>
              <li>
                <button onClick={logout} style={{ cursor: "pointer" }}>
                  Logout
                </button>
              </li>
            </>
          )}
          <li style={{ marginLeft: "auto", color: "#666", fontSize: 12 }}>
            {location.pathname}
          </li>
        </ul>
      </nav>

      <main style={{ padding: "20px" }}>
        <Outlet />
      </main>
    </div>
  )
}
