import React, { useState, useEffect } from 'react';
import { getTemplates } from '../services/api';

function TemplateSelector({ onSelectTemplate, selectedTemplateId = null }) {
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

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

  const handleSelect = (template) => {
    if (onSelectTemplate) {
      onSelectTemplate({
        subject: template.subject,
        html_body: template.html_body,
        vacancies_text: template.vacancies_text || ''
      });
    }
  };

  if (loading) {
    return <div className="template-selector-loading">Loading templates...</div>;
  }

  if (error) {
    return <div className="template-selector-error">{error}</div>;
  }

  if (templates.length === 0) {
    return (
      <div className="template-selector-empty">
        No templates available. Create a template to use it here.
      </div>
    );
  }

  return (
    <div className="template-selector">
      <label>Select Template:</label>
      <select
        value={selectedTemplateId || ''}
        onChange={(e) => {
          const templateId = parseInt(e.target.value);
          if (templateId) {
            const template = templates.find(t => t.id === templateId);
            if (template) {
              handleSelect(template);
            }
          }
        }}
        className="template-select"
      >
        <option value="">-- Select a template --</option>
        {templates.map(template => (
          <option key={template.id} value={template.id}>
            {template.name} - {template.subject}
          </option>
        ))}
      </select>
      {selectedTemplateId && (
        <div className="template-info">
          {(() => {
            const selected = templates.find(t => t.id === parseInt(selectedTemplateId));
            return selected ? (
              <div>
                <strong>Template:</strong> {selected.name}<br />
                <strong>Subject:</strong> {selected.subject}
              </div>
            ) : null;
          })()}
        </div>
      )}
    </div>
  );
}

export default TemplateSelector;
