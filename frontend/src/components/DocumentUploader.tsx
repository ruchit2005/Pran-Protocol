"use client";

import { useState, useEffect } from 'react';
import { Upload, FileText, X, CheckCircle, AlertCircle } from 'lucide-react';

interface UploadedDocument {
  id: string;
  file_name: string;
  upload_date: string;
  num_pages?: number;
  analysis?: {
    document_type?: string;
    summary?: string;
    medications?: string[];
    diagnoses?: string[];
  };
}

export default function DocumentUploader() {
  const [uploading, setUploading] = useState(false);
  const [documents, setDocuments] = useState<UploadedDocument[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Load documents on mount
  useEffect(() => {
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/documents', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setDocuments(data.documents || []);
      }
    } catch (err) {
      console.error('Failed to fetch documents:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setError('Only PDF files are supported');
      return;
    }

    // Check file size (max 10MB)
    const maxSize = 10 * 1024 * 1024; // 10MB in bytes
    if (file.size > maxSize) {
      setError(`File too large. Maximum size is 10MB (${(file.size / 1024 / 1024).toFixed(2)}MB provided)`);
      return;
    }

    setUploading(true);
    setError(null);
    setSuccess(null);

    try {
      const token = localStorage.getItem('token');
      if (!token) {
        setError('Not authenticated. Please log in again.');
        return;
      }

      console.log('Uploading file:', file.name, 'Size:', (file.size / 1024).toFixed(2), 'KB');
      
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('/api/documents', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      });

      console.log('Upload response status:', response.status);

      if (response.ok) {
        const result = await response.json();
        console.log('Upload success:', result);
        
        let successMsg = `✅ ${file.name} uploaded successfully`;
        
        // Add profile update notice
        if (result.profile_updated) {
          successMsg += ' | 📋 Profile updated with new medical data';
        } else if (result.ownership_status === 'different_patient') {
          successMsg += ' | ⚠️ Document appears to belong to a different patient';
        }
        
        setSuccess(successMsg);
        await fetchDocuments();
      } else {
        const error = await response.json();
        console.error('Upload failed:', response.status, error);
        setError(error.detail || `Upload failed (${response.status})`);
      }
    } catch (err) {
      console.error('Upload error:', err);
      setError('Network error during upload');
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  const handleDelete = async (docId: string) => {
    if (!confirm('Delete this document?')) return;

    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`/api/documents/${docId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      const data = await response.json();
      
      if (response.ok) {
        setSuccess('Document deleted');
        setError(null);
        await fetchDocuments();
      } else {
        setError(data.detail || 'Failed to delete document');
        console.error('Delete failed:', data);
      }
    } catch (err) {
      console.error('Delete error:', err);
      setError('Failed to delete document');
    }
  };

  return (
    <div className="space-y-4">
      {/* Upload Section */}
      <div className="border-2 border-dashed border-stone-300 rounded-lg p-6 text-center hover:border-primary transition-colors">
        <input
          type="file"
          accept=".pdf"
          onChange={handleUpload}
          disabled={uploading}
          className="hidden"
          id="document-upload"
        />
        <label htmlFor="document-upload" className="cursor-pointer">
          <Upload className={`mx-auto h-12 w-12 mb-3 ${uploading ? 'text-primary animate-pulse' : 'text-stone-400'}`} />
          <p className="text-sm text-stone-600 mb-1">
            {uploading ? 'Uploading & analyzing...' : 'Click to upload PDF'}
          </p>
          <p className="text-xs text-stone-500">
            Lab reports, prescriptions, medical records
          </p>
        </label>
      </div>

      {/* Status Messages */}
      {error && (
        <div className="flex items-center gap-2 p-3 bg-red-50 text-red-700 rounded-lg text-sm">
          <AlertCircle className="h-4 w-4" />
          {error}
        </div>
      )}
      {success && (
        <div className="flex items-center gap-2 p-3 bg-green-50 text-green-700 rounded-lg text-sm">
          <CheckCircle className="h-4 w-4" />
          {success}
        </div>
      )}

      {/* Documents List */}
      {loading ? (
        <div className="text-center py-8">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          <p className="text-sm text-stone-500 mt-2">Loading documents...</p>
        </div>
      ) : documents.length > 0 ? (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-stone-700">Uploaded Documents</h3>
          {documents.map((doc) => (
            <div
              key={doc.id}
              className="flex items-start justify-between p-3 bg-stone-50 rounded-lg hover:bg-stone-100 transition-colors"
            >
              <div className="flex items-start gap-3 flex-1">
                <FileText className="h-5 w-5 text-primary mt-0.5" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-stone-900 truncate">
                    {doc.file_name}
                  </p>
                  <p className="text-xs text-stone-500">
                    {new Date(doc.upload_date).toLocaleDateString()} • {doc.num_pages || 0} pages
                  </p>
                  {doc.analysis?.summary && (
                    <p className="text-xs text-stone-600 mt-1 line-clamp-2">
                      {doc.analysis.summary}
                    </p>
                  )}
                </div>
              </div>
              <button
                onClick={() => handleDelete(doc.id)}
                className="text-stone-400 hover:text-red-600 transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-8 text-stone-500">
          <FileText className="mx-auto h-12 w-12 text-stone-300 mb-2" />
          <p className="text-sm">No documents uploaded yet</p>
        </div>
      )}
    </div>
  );
}
