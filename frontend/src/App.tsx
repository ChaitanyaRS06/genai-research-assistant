import { Link, Outlet, useLocation, useNavigate } from "react-router-dom"
import { LogOut, Brain, Upload, Search, Home, User } from "lucide-react"

export default function App() {
  const location = useLocation()
  const navigate = useNavigate()
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null

  function logout() {
    localStorage.removeItem("token")
    navigate("/login")
  }

  const isAuthed = !!token

  // Don't show nav for login page
  const isLoginPage = location.pathname === "/login"

  return (
    <div className="min-h-screen bg-gray-50">
      {!isLoginPage && (
        <nav className="bg-white shadow-sm border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              {/* Logo and brand */}
              <div className="flex items-center space-x-2">
                <Brain className="w-8 h-8 text-primary-600" />
                <span className="text-xl font-bold text-gray-900">
                  AI Knowledge Analyst
                </span>
              </div>

              {/* Navigation links */}
              <div className="flex items-center space-x-6">
                <Link 
                  to="/" 
                  className={`flex items-center space-x-2 px-3 py-2 rounded-lg transition-colors ${
                    location.pathname === "/" 
                      ? "bg-primary-100 text-primary-700" 
                      : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"
                  }`}
                >
                  <Home className="w-4 h-4" />
                  <span>Home</span>
                </Link>

                {isAuthed ? (
                  <>
                    <Link 
                      to="/dashboard" 
                      className={`flex items-center space-x-2 px-3 py-2 rounded-lg transition-colors ${
                        location.pathname === "/dashboard" 
                          ? "bg-primary-100 text-primary-700" 
                          : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"
                      }`}
                    >
                      <User className="w-4 h-4" />
                      <span>Dashboard</span>
                    </Link>
                    <Link 
                      to="/upload" 
                      className={`flex items-center space-x-2 px-3 py-2 rounded-lg transition-colors ${
                        location.pathname === "/upload" 
                          ? "bg-primary-100 text-primary-700" 
                          : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"
                      }`}
                    >
                      <Upload className="w-4 h-4" />
                      <span>Upload</span>
                    </Link>
                    <Link 
                      to="/search" 
                      className={`flex items-center space-x-2 px-3 py-2 rounded-lg transition-colors ${
                        location.pathname === "/search" 
                          ? "bg-primary-100 text-primary-700" 
                          : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"
                      }`}
                    >
                      <Search className="w-4 h-4" />
                      <span>Search</span>
                    </Link>
                    <button 
                      onClick={logout}
                      className="flex items-center space-x-2 px-3 py-2 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                    >
                      <LogOut className="w-4 h-4" />
                      <span>Logout</span>
                    </button>
                  </>
                ) : (
                  <Link 
                    to="/login"
                    className="btn-primary"
                  >
                    Login
                  </Link>
                )}
              </div>
            </div>
          </div>
        </nav>
      )}

      <main className={isLoginPage ? "" : "max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8"}>
        <Outlet />
      </main>
    </div>
  )
}
