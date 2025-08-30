import { Link } from "react-router-dom"
import { Brain, Upload, Search, FileText, Zap, ArrowRight, CheckCircle } from "lucide-react"

export default function Home() {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null
  
  const features = [
    {
      icon: <Upload className="w-6 h-6 text-primary-600" />,
      title: "Smart Document Processing",
      description: "Upload PDFs and let our AI extract, chunk, and vectorize content for optimal search performance."
    },
    {
      icon: <Brain className="w-6 h-6 text-primary-600" />,
      title: "Advanced RAG Technology",
      description: "Powered by OpenAI's latest models with agentic workflow for intelligent question answering."
    },
    {
      icon: <Search className="w-6 h-6 text-primary-600" />,
      title: "Semantic Search",
      description: "Find relevant information using natural language queries with vector similarity matching."
    },
    {
      icon: <Zap className="w-6 h-6 text-primary-600" />,
      title: "Real-time Processing",
      description: "Get instant answers with detailed reasoning chains and source citations."
    }
  ]

  const benefits = [
    "Upload unlimited PDF documents",
    "AI-powered semantic search",
    "Detailed reasoning chains",
    "Source citation and verification",
    "Fast processing pipeline",
    "Secure and private"
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 to-blue-100">
      {/* Hero Section */}
      <div className="relative overflow-hidden">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
          <div className="text-center">
            <div className="flex justify-center mb-8">
              <div className="p-6 bg-white rounded-2xl shadow-lg">
                <Brain className="w-16 h-16 text-primary-600" />
              </div>
            </div>
            
            <h1 className="text-4xl sm:text-6xl font-bold text-gray-900 mb-6">
              AI Knowledge
              <span className="text-primary-600 block">Analyst</span>
            </h1>
            
            <p className="text-xl text-gray-600 max-w-3xl mx-auto mb-8">
              Transform your documents into an intelligent knowledge base. Upload PDFs, ask questions, 
              and get AI-powered answers with detailed reasoning and source citations.
            </p>
            
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              {!token ? (
                <>
                  <Link
                    to="/login"
                    className="btn-primary flex items-center space-x-2 text-lg px-8 py-3"
                  >
                    <span>Get Started</span>
                    <ArrowRight className="w-5 h-5" />
                  </Link>
                  <button className="btn-secondary text-lg px-8 py-3">
                    Learn More
                  </button>
                </>
              ) : (
                <>
                  <Link
                    to="/dashboard"
                    className="btn-primary flex items-center space-x-2 text-lg px-8 py-3"
                  >
                    <span>Open Dashboard</span>
                    <ArrowRight className="w-5 h-5" />
                  </Link>
                  <Link
                    to="/search"
                    className="btn-secondary text-lg px-8 py-3"
                  >
                    Start Searching
                  </Link>
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="bg-white py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">
              Powerful AI Research Capabilities
            </h2>
            <p className="text-lg text-gray-600">
              Everything you need to turn documents into actionable insights
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {features.map((feature, index) => (
              <div key={index} className="card text-center">
                <div className="flex justify-center mb-4">
                  <div className="p-3 bg-primary-100 rounded-xl">
                    {feature.icon}
                  </div>
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  {feature.title}
                </h3>
                <p className="text-gray-600">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Benefits Section */}
      <div className="bg-gray-50 py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <div>
              <h2 className="text-3xl font-bold text-gray-900 mb-6">
                Why Choose Our RAG System?
              </h2>
              <p className="text-lg text-gray-600 mb-8">
                Built with cutting-edge AI technology to provide the most accurate and insightful 
                answers from your document collection.
              </p>
              
              <div className="space-y-4">
                {benefits.map((benefit, index) => (
                  <div key={index} className="flex items-center space-x-3">
                    <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0" />
                    <span className="text-gray-700">{benefit}</span>
                  </div>
                ))}
              </div>
              
              {!token && (
                <div className="mt-8">
                  <Link
                    to="/login"
                    className="btn-primary flex items-center space-x-2 w-fit"
                  >
                    <span>Start Free Trial</span>
                    <ArrowRight className="w-4 h-4" />
                  </Link>
                </div>
              )}
            </div>
            
            <div className="relative">
              <div className="bg-white rounded-2xl shadow-xl p-8 space-y-6">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-primary-100 rounded-lg">
                    <FileText className="w-5 h-5 text-primary-600" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-gray-900">Document Upload</h4>
                    <p className="text-sm text-gray-600">PDF processing complete</p>
                  </div>
                  <CheckCircle className="w-5 h-5 text-green-500 ml-auto" />
                </div>
                
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-primary-100 rounded-lg">
                    <Brain className="w-5 h-5 text-primary-600" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-gray-900">AI Analysis</h4>
                    <p className="text-sm text-gray-600">Vector embeddings generated</p>
                  </div>
                  <CheckCircle className="w-5 h-5 text-green-500 ml-auto" />
                </div>
                
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-primary-100 rounded-lg">
                    <Search className="w-5 h-5 text-primary-600" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-gray-900">Smart Search</h4>
                    <p className="text-sm text-gray-600">Ready for questions</p>
                  </div>
                  <CheckCircle className="w-5 h-5 text-green-500 ml-auto" />
                </div>
                
                <div className="bg-gray-50 rounded-lg p-4 mt-6">
                  <div className="text-sm text-gray-600 mb-2">Example Question:</div>
                  <div className="text-gray-900 font-medium mb-3">
                    "What are the main challenges in RAG evaluation?"
                  </div>
                  <div className="text-sm text-gray-600">
                    <span className="font-medium text-primary-600">AI Answer:</span> Based on your documents, 
                    the main challenges include retrieval quality assessment, answer hallucination detection...
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* CTA Section */}
      <div className="bg-primary-600 py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold text-white mb-4">
            Ready to Transform Your Research?
          </h2>
          <p className="text-xl text-primary-100 mb-8 max-w-2xl mx-auto">
            Join researchers and professionals who are already using AI to unlock insights 
            from their document collections.
          </p>
          
          {!token && (
            <Link
              to="/login"
              className="bg-white text-primary-600 font-semibold px-8 py-3 rounded-lg hover:bg-gray-100 transition-colors inline-flex items-center space-x-2"
            >
              <span>Get Started Today</span>
              <ArrowRight className="w-5 h-5" />
            </Link>
          )}
        </div>
      </div>
    </div>
  )
}
