import { Link, useNavigate } from "react-router-dom"
import { useEffect, useState } from "react"
import { Upload, FileText, Database, Brain, ArrowRight, CheckCircle, Clock, AlertCircle } from "lucide-react"

type Document = {
  id: number
  original_filename: string
  status: string
  created_at: string
}

export default function Dashboard() {
  const navigate = useNavigate()
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string>("")
  const [stats, setStats] = useState({ total: 0, completed: 0, failed: 0, processing: 0 })

  useEffect(() => {
    const token = localStorage.getItem("token")
    if (!token) {
      navigate("/login")
      return
    }

    // Fetch documents
    fetchDocuments()
  }, [navigate])

  async function fetchDocuments() {
    try {
      const token = localStorage.getItem("token")
      if (!token) {
        console.error("No token found")
        navigate("/login")
        return
      }

      const res = await fetch("http://localhost:8000/documents/", {
        headers: { Authorization: `Bearer ${token}` }
      })
      
      if (res.ok) {
        const data = await res.json()
        const docs: Document[] = data.documents || data // Handle both response formats
        setDocuments(docs)
        
        // Calculate stats
        const stats = {
          total: docs.length,
          completed: docs.filter(d => d.status === 'completed').length,
          failed: docs.filter(d => d.status === 'failed').length,
          processing: docs.filter(d => d.status === 'processing' || d.status === 'uploaded').length,
        }
        setStats(stats)
      } else {
        const errorMsg = `Failed to fetch documents: ${res.status} ${res.statusText}`
        console.error(errorMsg)
        setError(errorMsg)
        if (res.status === 401) {
          // Token expired, redirect to login
          localStorage.removeItem("token")
          navigate("/login")
        }
      }
    } catch (error: any) {
      const errorMsg = `Network error: ${error.message || 'Unknown error'}`
      console.error(errorMsg, error)
      setError(errorMsg)
      // Don't redirect on network errors, just show empty state
    } finally {
      setLoading(false)
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />
      case 'failed':
        return <AlertCircle className="w-4 h-4 text-red-500" />
      case 'processing':
      case 'uploaded':
        return <Clock className="w-4 h-4 text-yellow-500" />
      default:
        return <Clock className="w-4 h-4 text-gray-500" />
    }
  }

  const getStatusBadge = (status: string) => {
    const baseClasses = "badge"
    switch (status) {
      case 'completed':
        return `${baseClasses} badge-success`
      case 'failed':
        return `${baseClasses} bg-red-100 text-red-800`
      case 'processing':
      case 'uploaded':
        return `${baseClasses} badge-warning`
      default:
        return `${baseClasses} badge-gray`
    }
  }

  // Early return for error state
  if (error && !loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Connection Error</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <button 
            onClick={() => {
              setError("")
              setLoading(true)
              fetchDocuments()
            }}
            className="btn-primary"
          >
            Try Again
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-2 text-gray-600">
          Manage your documents and explore AI-powered research capabilities
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="card">
          <div className="flex items-center">
            <div className="p-2 bg-blue-100 rounded-lg">
              <FileText className="w-6 h-6 text-blue-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Total Documents</p>
              <p className="text-2xl font-bold text-gray-900">{stats.total}</p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center">
            <div className="p-2 bg-green-100 rounded-lg">
              <CheckCircle className="w-6 h-6 text-green-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Ready for Search</p>
              <p className="text-2xl font-bold text-gray-900">{stats.completed}</p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center">
            <div className="p-2 bg-yellow-100 rounded-lg">
              <Clock className="w-6 h-6 text-yellow-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Processing</p>
              <p className="text-2xl font-bold text-gray-900">{stats.processing}</p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center">
            <div className="p-2 bg-red-100 rounded-lg">
              <AlertCircle className="w-6 h-6 text-red-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Failed</p>
              <p className="text-2xl font-bold text-gray-900">{stats.failed}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Link to="/upload" className="card hover:shadow-md transition-shadow group">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="p-3 bg-primary-100 rounded-xl">
                <Upload className="w-8 h-8 text-primary-600" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900">Upload Documents</h3>
                <p className="text-gray-600">Add new PDFs to your knowledge base</p>
              </div>
            </div>
            <ArrowRight className="w-5 h-5 text-gray-400 group-hover:text-primary-600 transition-colors" />
          </div>
        </Link>

        <Link to="/search" className="card hover:shadow-md transition-shadow group">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="p-3 bg-green-100 rounded-xl">
                <Brain className="w-8 h-8 text-green-600" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900">AI Search</h3>
                <p className="text-gray-600">Ask questions about your documents</p>
              </div>
            </div>
            <ArrowRight className="w-5 h-5 text-gray-400 group-hover:text-green-600 transition-colors" />
          </div>
        </Link>
      </div>

      {/* Recent Documents */}
      <div className="card">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-gray-900">Recent Documents</h2>
          <button 
            onClick={fetchDocuments}
            className="btn-secondary text-sm"
            disabled={loading}
          >
            Refresh
          </button>
        </div>

        {loading ? (
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto"></div>
            <p className="mt-2 text-gray-600">Loading documents...</p>
          </div>
        ) : documents.length === 0 ? (
          <div className="text-center py-8">
            <Database className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No documents yet</h3>
            <p className="text-gray-600 mb-4">Upload your first document to get started</p>
            <Link to="/upload" className="btn-primary">
              Upload Document
            </Link>
          </div>
        ) : (
          <div className="overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-4 font-medium text-gray-600">Document</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-600">Status</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-600">Uploaded</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {documents.slice(0, 10).map((doc) => (
                  <tr key={doc.id} className="hover:bg-gray-50">
                    <td className="py-3 px-4">
                      <div className="flex items-center space-x-3">
                        <FileText className="w-5 h-5 text-gray-400" />
                        <span className="font-medium text-gray-900">
                          {doc.original_filename}
                        </span>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center space-x-2">
                        {getStatusIcon(doc.status)}
                        <span className={getStatusBadge(doc.status)}>
                          {doc.status}
                        </span>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-gray-600">
                      {new Date(doc.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
