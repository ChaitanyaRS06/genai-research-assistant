import { useEffect, useState, useRef } from "react"
import { useNavigate } from "react-router-dom"
import { Upload as UploadIcon, FileText, CheckCircle, XCircle, Loader2, ArrowRight } from "lucide-react"

type UploadStep = "upload" | "process" | "embed" | "complete"

export default function Upload() {
  const [file, setFile] = useState<File | null>(null)
  const [message, setMessage] = useState("")
  const [messageType, setMessageType] = useState<"success" | "error" | "">("")
  const [busy, setBusy] = useState(false)
  const [currentStep, setCurrentStep] = useState<UploadStep>("upload")
  const [dragOver, setDragOver] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()

  useEffect(() => {
    const token = localStorage.getItem("token")
    if (!token) navigate("/login")
  }, [navigate])

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    
    const files = e.dataTransfer.files
    if (files.length > 0) {
      const selectedFile = files[0]
      if (selectedFile.type === "application/pdf") {
        setFile(selectedFile)
      } else {
        setMessage("Please select a PDF file")
        setMessageType("error")
      }
    }
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0]
    if (selectedFile) {
      setFile(selectedFile)
      setMessage("")
      setMessageType("")
    }
  }

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault()
    if (!file) return
    
    const token = localStorage.getItem("token")
    setBusy(true)
    setMessage("")
    setMessageType("")

    try {
      // Step 1: Upload
      setCurrentStep("upload")
      const fd = new FormData()
      fd.append("file", file)
      const uploadRes = await fetch("http://localhost:8000/documents/upload", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: fd,
      })
      
      if (!uploadRes.ok) {
        const error = await uploadRes.json().catch(() => ({}))
        throw new Error(error.detail || "Upload failed")
      }
      
      const uploaded = await uploadRes.json()

      // Step 2: Process
      setCurrentStep("process")
      const processRes = await fetch(`http://localhost:8000/documents/${uploaded.id}/process`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      })
      
      if (!processRes.ok) {
        const error = await processRes.json().catch(() => ({}))
        throw new Error(error.detail || "Processing failed")
      }

      // Step 3: Generate embeddings
      setCurrentStep("embed")
      const embedRes = await fetch(`http://localhost:8000/embeddings/generate/${uploaded.id}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      })
      
      if (!embedRes.ok) {
        const error = await embedRes.json().catch(() => ({}))
        throw new Error(error.detail || "Embedding generation failed")
      }

      // Success
      setCurrentStep("complete")
      setMessage("Document uploaded and processed successfully! Ready for AI search.")
      setMessageType("success")
      
      // Reset after success
      setTimeout(() => {
        setFile(null)
        setCurrentStep("upload")
        if (fileInputRef.current) {
          fileInputRef.current.value = ""
        }
      }, 3000)

    } catch (err: any) {
      setMessage(err.message || "Upload pipeline failed")
      setMessageType("error")
      setCurrentStep("upload")
    } finally {
      setBusy(false)
    }
  }

  const getStepIcon = (step: UploadStep, active: boolean, completed: boolean) => {
    if (busy && active) {
      return <Loader2 className="w-5 h-5 animate-spin text-primary-600" />
    }
    if (completed) {
      return <CheckCircle className="w-5 h-5 text-green-600" />
    }
    
    switch (step) {
      case "upload":
        return <UploadIcon className={`w-5 h-5 ${active ? "text-primary-600" : "text-gray-400"}`} />
      case "process":
        return <FileText className={`w-5 h-5 ${active ? "text-primary-600" : "text-gray-400"}`} />
      case "embed":
        return <div className={`w-5 h-5 rounded border-2 ${active ? "border-primary-600" : "border-gray-400"}`} />
      case "complete":
        return <CheckCircle className={`w-5 h-5 ${active ? "text-green-600" : "text-gray-400"}`} />
    }
  }

  const steps = [
    { key: "upload", label: "Upload File", description: "Upload your PDF document" },
    { key: "process", label: "Process", description: "Extract text and create chunks" },
    { key: "embed", label: "Generate Embeddings", description: "Create vector embeddings for search" },
    { key: "complete", label: "Complete", description: "Ready for AI search" },
  ]

  const currentStepIndex = steps.findIndex(s => s.key === currentStep)

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Upload Document</h1>
        <p className="mt-2 text-gray-600">
          Add PDF documents to your knowledge base for AI-powered search
        </p>
      </div>

      {/* Upload Area */}
      <div className="card">
        <form onSubmit={handleUpload} className="space-y-6">
          {/* Drag and Drop Zone */}
          <div
            className={`relative border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
              dragOver 
                ? "border-primary-500 bg-primary-50" 
                : file 
                ? "border-green-300 bg-green-50" 
                : "border-gray-300 hover:border-gray-400"
            }`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              onChange={handleFileSelect}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              disabled={busy}
            />
            
            {file ? (
              <div className="space-y-3">
                <FileText className="w-12 h-12 text-green-600 mx-auto" />
                <div>
                  <p className="text-lg font-medium text-gray-900">{file.name}</p>
                  <p className="text-sm text-gray-500">
                    {(file.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setFile(null)
                    if (fileInputRef.current) {
                      fileInputRef.current.value = ""
                    }
                  }}
                  className="text-sm text-gray-500 hover:text-red-600"
                  disabled={busy}
                >
                  Remove file
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                <UploadIcon className="w-12 h-12 text-gray-400 mx-auto" />
                <div>
                  <p className="text-lg font-medium text-gray-900">
                    Drop your PDF here, or click to browse
                  </p>
                  <p className="text-sm text-gray-500">
                    Supports PDF files up to 50MB
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Upload Button */}
          <div className="flex justify-center">
            <button
              type="submit"
              disabled={!file || busy}
              className="btn-primary flex items-center space-x-2 px-8"
            >
              {busy ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Processing...</span>
                </>
              ) : (
                <>
                  <UploadIcon className="w-4 h-4" />
                  <span>Upload & Process</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Processing Steps */}
      {busy && (
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-6">Processing Pipeline</h3>
          <div className="space-y-4">
            {steps.map((step, index) => {
              const isActive = currentStep === step.key
              const isCompleted = index < currentStepIndex
              
              return (
                <div key={step.key} className="flex items-center space-x-4">
                  <div className="flex-shrink-0">
                    {getStepIcon(step.key as UploadStep, isActive, isCompleted)}
                  </div>
                  <div className="flex-grow">
                    <p className={`font-medium ${isActive ? "text-primary-600" : isCompleted ? "text-green-600" : "text-gray-500"}`}>
                      {step.label}
                    </p>
                    <p className="text-sm text-gray-500">{step.description}</p>
                  </div>
                  {index < steps.length - 1 && (
                    <ArrowRight className="w-4 h-4 text-gray-300" />
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Message */}
      {message && (
        <div className={`card flex items-center space-x-3 ${
          messageType === "success" 
            ? "bg-green-50 border-green-200" 
            : "bg-red-50 border-red-200"
        }`}>
          {messageType === "success" ? (
            <CheckCircle className="w-5 h-5 text-green-600" />
          ) : (
            <XCircle className="w-5 h-5 text-red-600" />
          )}
          <p className={`${messageType === "success" ? "text-green-800" : "text-red-800"}`}>
            {message}
          </p>
        </div>
      )}

      {/* Info Section */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">What happens after upload?</h3>
          <ul className="space-y-2 text-sm text-gray-600">
            <li className="flex items-start space-x-2">
              <div className="w-1.5 h-1.5 bg-primary-600 rounded-full mt-2 flex-shrink-0"></div>
              <span>PDF text is extracted and cleaned</span>
            </li>
            <li className="flex items-start space-x-2">
              <div className="w-1.5 h-1.5 bg-primary-600 rounded-full mt-2 flex-shrink-0"></div>
              <span>Content is split into semantic chunks</span>
            </li>
            <li className="flex items-start space-x-2">
              <div className="w-1.5 h-1.5 bg-primary-600 rounded-full mt-2 flex-shrink-0"></div>
              <span>Vector embeddings are generated using OpenAI</span>
            </li>
            <li className="flex items-start space-x-2">
              <div className="w-1.5 h-1.5 bg-primary-600 rounded-full mt-2 flex-shrink-0"></div>
              <span>Document becomes searchable via AI</span>
            </li>
          </ul>
        </div>

        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">Supported formats</h3>
          <ul className="space-y-2 text-sm text-gray-600">
            <li className="flex items-center space-x-2">
              <FileText className="w-4 h-4 text-red-600" />
              <span>PDF documents (.pdf)</span>
            </li>
            <li className="text-xs text-gray-500 ml-6">
              Research papers, reports, books, manuals
            </li>
          </ul>
        </div>
      </div>
    </div>
  )
}
