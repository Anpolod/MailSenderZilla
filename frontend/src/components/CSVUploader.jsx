import React, { useState, useRef } from 'react';
import { uploadCSV } from '../services/api';

function CSVUploader({ onUploadSuccess, onError }) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadedFile, setUploadedFile] = useState(null);
  const fileInputRef = useRef(null);

  const handleDragEnter = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const file = e.dataTransfer.files[0];
    if (file && file.name.endsWith('.csv')) {
      await handleFileUpload(file);
    } else {
      if (onError) onError('Please upload a CSV file');
    }
  };

  const handleFileSelect = async (e) => {
    const file = e.target.files[0];
    if (file) {
      await handleFileUpload(file);
    }
  };

  const handleFileUpload = async (file) => {
    setUploading(true);
    try {
      const result = await uploadCSV(file);
      setUploadedFile({
        filename: result.filename,
        path: result.path,
      });
      if (onUploadSuccess) {
        onUploadSuccess(result.path, result.filename);
      }
    } catch (error) {
      const errorMessage = error.response?.data?.error || error.message || 'Upload failed';
      if (onError) {
        onError(errorMessage);
      }
    } finally {
      setUploading(false);
    }
  };

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="csv-uploader">
      <div
        className={`upload-zone ${isDragging ? 'dragging' : ''} ${uploadedFile ? 'uploaded' : ''}`}
        onDragEnter={handleDragEnter}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleClick}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv"
          onChange={handleFileSelect}
          style={{ display: 'none' }}
        />
        
        {uploading ? (
          <div className="upload-status">
            <p>Uploading...</p>
          </div>
        ) : uploadedFile ? (
          <div className="upload-status">
            <p>✓ Uploaded: {uploadedFile.filename}</p>
          </div>
        ) : (
          <div className="upload-prompt">
            <p>📁 Drag and drop CSV file here</p>
            <p>or click to browse</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default CSVUploader;
