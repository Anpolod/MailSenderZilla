import React from 'react';

function EmailPreviewModal({ isOpen, onClose, htmlContent, loading }) {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content email-preview-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Email Preview</h2>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>
        <div className="modal-body">
          {loading ? (
            <div className="loading">Generating preview...</div>
          ) : htmlContent ? (
            <div className="email-preview-container">
              <iframe
                title="Email Preview"
                srcDoc={htmlContent}
                className="email-preview-iframe"
                sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox allow-top-navigation-by-user-activation"
              />
            </div>
          ) : (
            <div className="error-message">No content to preview</div>
          )}
        </div>
        <div className="modal-footer">
          <button className="btn-secondary" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}

export default EmailPreviewModal;
