import React, { useState, useEffect } from 'react';
import { getTemplates, createTemplate, updateTemplate, deleteTemplate } from '../services/api';

function TemplateManager({ isOpen, onSelectTemplate, onClose }) {
  if (!isOpen) return null;
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [editing, setEditing] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    subject: '',
    html_body: '',
    vacancies_text: ''
  });
  const [showForm, setShowForm] = useState(false);

  useEffect(() => {
    loadTemplates();
  }, []);

  const loadTemplates = async () => {
    try {
      setLoading(true);
      const data = await getTemplates();
      setTemplates(data);
      setError('');
    } catch (err) {
      setError('Failed to load templates: ' + (err.message || 'Unknown error'));
      console.error('Failed to load templates:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    try {
      if (editing) {
        await updateTemplate(editing.id, formData);
      } else {
        await createTemplate(formData);
      }
      
      await loadTemplates();
      resetForm();
      alert(editing ? 'Template updated successfully!' : 'Template created successfully!');
    } catch (err) {
      setError('Failed to save template: ' + (err.response?.data?.error || err.message));
      console.error('Failed to save template:', err);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this template?')) {
      return;
    }

    try {
      await deleteTemplate(id);
      await loadTemplates();
      if (editing && editing.id === id) {
        resetForm();
      }
      alert('Template deleted successfully!');
    } catch (err) {
      setError('Failed to delete template: ' + (err.response?.data?.error || err.message));
      console.error('Failed to delete template:', err);
    }
  };

  const handleEdit = (template) => {
    setEditing(template);
    setFormData({
      name: template.name,
      subject: template.subject,
      html_body: template.html_body || '',
      vacancies_text: template.vacancies_text || ''
    });
    setShowForm(true);
  };

  const handleUseTemplate = (template) => {
    if (onSelectTemplate) {
      onSelectTemplate({
        subject: template.subject,
        html_body: template.html_body,
        vacancies_text: template.vacancies_text || ''
      });
    }
    if (onClose) {
      onClose();
    }
  };

  const resetForm = () => {
    setEditing(null);
    setFormData({
      name: '',
      subject: '',
      html_body: '',
      vacancies_text: ''
    });
    setShowForm(false);
  };

  return (
    <div className="template-manager-modal">
      <div className="modal-content template-manager-content">
        <div className="template-manager-header">
          <div className="header-left">
            <h2>Email Templates</h2>
            <span className="templates-count">({templates.length} saved)</span>
          </div>
          <div className="header-actions">
            {!showForm && (
              <button onClick={() => setShowForm(true)} className="btn-primary">
                <span className="btn-icon">+</span>
                Create New Template
              </button>
            )}
            <button onClick={onClose} className="modal-close-btn">
              <span>×</span>
            </button>
          </div>
        </div>

        {error && <div className="error-message">{error}</div>}

        {showForm && (
          <div className="template-form-section">
            <div className="form-section-header">
              <h3>{editing ? 'Edit Template' : 'Create New Template'}</h3>
              <button 
                type="button" 
                onClick={resetForm} 
                className="btn-form-close"
                title="Close form"
              >
                ×
              </button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Template Name *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                  placeholder="e.g., Weekly Vacancies"
                />
              </div>

              <div className="form-group">
                <label>Subject *</label>
                <input
                  type="text"
                  value={formData.subject}
                  onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
                  required
                  placeholder="Email subject line"
                />
              </div>

              <div className="form-group">
                <label>HTML Body</label>
                <textarea
                  value={formData.html_body}
                  onChange={(e) => setFormData({ ...formData, html_body: e.target.value })}
                  rows={8}
                  placeholder="HTML content (optional)"
                />
              </div>

              <div className="form-group">
                <label>Vacancies Text</label>
                <textarea
                  value={formData.vacancies_text}
                  onChange={(e) => setFormData({ ...formData, vacancies_text: e.target.value })}
                  rows={6}
                  placeholder="Plain text vacancies (optional)"
                />
              </div>

              <div className="form-actions">
                <button type="submit" className="btn-primary">
                  {editing ? 'Update Template' : 'Create Template'}
                </button>
                <button type="button" onClick={resetForm} className="btn-secondary">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        <div className="templates-list">
          <h3>Saved Templates ({templates.length})</h3>
          {loading ? (
            <div>Loading templates...</div>
          ) : templates.length === 0 ? (
            <div className="empty-state">No templates yet. Create your first template!</div>
          ) : (
            <div className="templates-grid">
              {templates.map(template => (
                <div key={template.id} className="template-card">
                  <div className="template-card-header">
                    <h4>{template.name}</h4>
                    <div className="template-card-actions">
                      {onSelectTemplate && (
                        <button
                          onClick={() => handleUseTemplate(template)}
                          className="btn-use-template"
                          title="Use this template"
                        >
                          Use
                        </button>
                      )}
                      <button
                        onClick={() => handleEdit(template)}
                        className="btn-edit-template"
                        title="Edit template"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDelete(template.id)}
                        className="btn-delete-template"
                        title="Delete template"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                  <div className="template-card-body">
                    <p><strong>Subject:</strong> {template.subject}</p>
                    <p className="template-meta">
                      Created: {new Date(template.created_ts).toLocaleDateString()}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default TemplateManager;
