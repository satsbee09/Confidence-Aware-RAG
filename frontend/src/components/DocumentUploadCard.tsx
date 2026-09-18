import React, { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { UploadCloud, FileText, CheckCircle2, AlertTriangle, AlertOctagon, Trash2, Check, RefreshCw } from 'lucide-react';
import type { DocumentSummary } from '../types';
import { uploadDocument, deleteDocument } from '../api';
import confetti from 'canvas-confetti';

interface DocumentUploadCardProps {
  documents: DocumentSummary[];
  selectedDocId: string | null;
  onSelectDocId: (docId: string | null) => void;
  onRefresh: () => void;
}

export const DocumentUploadCard: React.FC<DocumentUploadCardProps> = ({
  documents,
  selectedDocId,
  onSelectDocId,
  onRefresh,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      await handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      await handleFileUpload(e.target.files[0]);
    }
  };

  const handleFileUpload = async (file: File) => {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setUploadError('Please select a valid PDF document (.pdf).');
      return;
    }

    setIsUploading(true);
    setUploadError(null);
    setUploadSuccess(null);

    try {
      const res = await uploadDocument(file);
      setUploadSuccess(`Successfully ingested "${file.name}" (${res.pages} pages, ${res.chunks} confidence-scored chunks, average OCR confidence: ${(res.average_confidence * 100).toFixed(1)}%).`);
      confetti({
        particleCount: 50,
        spread: 60,
        origin: { y: 0.7 },
      });
      onRefresh();
      onSelectDocId(res.document_id);
    } catch (err: any) {
      setUploadError(err.message || 'Failed to upload and process document.');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleDelete = async (docId: string, filename: string) => {
    if (window.confirm(`Are you sure you want to remove "${filename}" from the vector store?`)) {
      try {
        await deleteDocument(docId);
        if (selectedDocId === docId) {
          onSelectDocId(null);
        }
        onRefresh();
      } catch (err: any) {
        alert(err.message || 'Failed to delete document.');
      }
    }
  };

  const getConfidenceBadge = (avgConf: number) => {
    const pct = (avgConf * 100).toFixed(1);
    if (avgConf >= 0.85) {
      return (
        <span className="badge badge-low-risk" title="Clean OCR quality with high word reliability">
          <CheckCircle2 size={13} /> {pct}% Confidence (Clean)
        </span>
      );
    } else if (avgConf >= 0.65) {
      return (
        <span className="badge badge-medium-risk" title="Moderate OCR quality with some uncertain tokens">
          <AlertTriangle size={13} /> {pct}% Confidence (Moderate)
        </span>
      );
    } else {
      return (
        <span className="badge badge-high-risk" title="Heavy degradation / scan noise detected">
          <AlertOctagon size={13} /> {pct}% Confidence (Noisy Scan)
        </span>
      );
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  return (
    <div className="section-container">
      {/* Header */}
      <div className="section-header">
        <div>
          <h2 className="section-title">Document Repository & OCR Ingestion</h2>
          <p className="section-desc">
            Upload Indian legal court orders, gazette notifications, or RTI replies. OCR token-level confidence scores are calculated and embedded into chunk metadata.
          </p>
        </div>
        <motion.button
          className="btn-secondary"
          onClick={onRefresh}
          title="Refresh Document List"
          whileHover={{ scale: 1.04 }}
          whileTap={{ scale: 0.96 }}
        >
          <RefreshCw size={16} />
          <span>Refresh</span>
        </motion.button>
      </div>

      {/* Drag and Drop Zone */}
      <motion.div
        className={`dropzone-card ${isDragging ? 'dropzone-active' : ''} ${isUploading ? 'dropzone-uploading' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !isUploading && fileInputRef.current?.click()}
        whileHover={{ scale: 1.01 }}
        whileTap={{ scale: 0.99 }}
      >
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          accept="application/pdf"
          style={{ display: 'none' }}
        />
        <div className="dropzone-content">
          <motion.div
            className="dropzone-icon-box"
            animate={isUploading ? { rotate: 360 } : {}}
            transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
          >
            <UploadCloud size={36} className="dropzone-icon" />
          </motion.div>
          <div className="dropzone-text">
            <span className="dropzone-primary-text">
              {isUploading ? 'Extracting text & calculating token confidence...' : 'Click or drag PDF files here to upload'}
            </span>
            <span className="dropzone-secondary-text">
              Supports scanned orders, gazettes, circulars, and RTI PDFs with automatic confidence tagging
            </span>
          </div>
        </div>
      </motion.div>

      {/* Alerts */}
      <AnimatePresence>
        {uploadError && (
          <motion.div
            className="alert-box alert-error"
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
          >
            <AlertOctagon size={18} />
            <span>{uploadError}</span>
          </motion.div>
        )}

        {uploadSuccess && (
          <motion.div
            className="alert-box alert-success"
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
          >
            <CheckCircle2 size={18} />
            <span>{uploadSuccess}</span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Document Repository List */}
      <div className="documents-list-section">
        <div className="list-header-row">
          <h3 className="subheading">
            Ingested Documents ({documents.length})
          </h3>
          {selectedDocId && (
            <button className="btn-text" onClick={() => onSelectDocId(null)}>
              Reset to Search All Documents
            </button>
          )}
        </div>

        {documents.length === 0 ? (
          <div className="empty-state-box">
            <FileText size={42} className="empty-state-icon" />
            <p className="empty-state-title">No documents ingested yet</p>
            <p className="empty-state-desc">Upload a PDF above to inspect confidence scores and begin asking questions.</p>
          </div>
        ) : (
          <div className="doc-grid">
            {documents.map((doc, idx) => {
              const isSelected = selectedDocId === doc.document_id;
              return (
                <motion.div
                  key={doc.document_id}
                  className={`doc-card ${isSelected ? 'doc-card-selected' : ''}`}
                  initial={{ opacity: 0, y: 15 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3, delay: idx * 0.05 }}
                  whileHover={{ y: -3, scale: 1.01 }}
                >
                  <div className="doc-card-top">
                    <div className="doc-card-title-row">
                      <FileText size={20} className="doc-icon" />
                      <span className="doc-filename" title={doc.filename}>
                        {doc.filename}
                      </span>
                    </div>
                    <motion.button
                      className="btn-icon-danger"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDelete(doc.document_id, doc.filename);
                      }}
                      title="Delete document"
                      whileHover={{ scale: 1.15 }}
                      whileTap={{ scale: 0.9 }}
                    >
                      <Trash2 size={16} />
                    </motion.button>
                  </div>

                  <div className="doc-card-metrics">
                    <div className="metric-pill">
                      <span className="metric-label">Pages</span>
                      <span className="metric-val">{doc.pages}</span>
                    </div>
                    <div className="metric-pill">
                      <span className="metric-label">Chunks</span>
                      <span className="metric-val">{doc.chunks}</span>
                    </div>
                    <div className="metric-pill">
                      <span className="metric-label">Size</span>
                      <span className="metric-val">{formatFileSize(doc.file_size_bytes)}</span>
                    </div>
                  </div>

                  <div className="doc-card-confidence">
                    <div className="confidence-label-row">
                      <span className="conf-title">OCR Reliability</span>
                      {getConfidenceBadge(doc.average_confidence)}
                    </div>
                    <div className="progress-bar-bg">
                      <motion.div
                        className="progress-bar-fill"
                        initial={{ width: 0 }}
                        animate={{ width: `${Math.min(100, Math.max(5, doc.average_confidence * 100))}%` }}
                        transition={{ duration: 0.8, ease: 'easeOut' }}
                        style={{
                          backgroundColor:
                            doc.average_confidence >= 0.85
                              ? 'var(--success-color)'
                              : doc.average_confidence >= 0.65
                              ? 'var(--warning-color)'
                              : 'var(--danger-color)',
                        }}
                      />
                    </div>
                    <div className="min-conf-note">
                      Min token confidence: {(doc.min_confidence * 100).toFixed(1)}%
                    </div>
                  </div>

                  <div className="doc-card-footer">
                    <motion.button
                      className={`btn-select-doc ${isSelected ? 'btn-select-active' : ''}`}
                      onClick={() => onSelectDocId(isSelected ? null : doc.document_id)}
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                    >
                      {isSelected ? (
                        <>
                          <Check size={14} /> Selected for Scoped Query
                        </>
                      ) : (
                        'Scope Query to this Doc'
                      )}
                    </motion.button>
                  </div>
                </motion.div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
