import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { createCampaign, previewEmail, getSettings } from '../services/api';
import CSVUploader from './CSVUploader';
import DatabaseSelector from './DatabaseSelector';
import EmailPreviewModal from './EmailPreviewModal';
import TemplateSelector from './TemplateSelector';

function CampaignForm() {
  const navigate = useNavigate();
  const [dataSource, setDataSource] = useState('csv'); // 'csv' or 'database'
  const [formData, setFormData] = useState({
    name: '',
    provider: 'mailersend',
    subject: '',
    sender_email: '',
    csv_path: '',
    database_table: '',
    email_column: 'email',
    batch_size: 1,
    delay_between_batches: 45,
    daily_limit: 2000,
    api_token: '',
    app_password: '',
    vacancies_text: '',
    selected_rowids: null,
  });
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewHtml, setPreviewHtml] = useState('');
  const [previewLoading, setPreviewLoading] = useState(false);
  const [useSavedCredentials, setUseSavedCredentials] = useState(true);
  const [selectedTemplateId, setSelectedTemplateId] = useState(null);

  // Load saved credentials from settings on mount
  useEffect(() => {
    loadSavedCredentials();
  }, []);

  const loadSavedCredentials = async () => {
    try {
      const settings = await getSettings();
      if (settings.mailersend_api_token || settings.gmail_app_password) {
        setFormData(prev => ({
          ...prev,
          api_token: settings.mailersend_api_token || prev.api_token,
          app_password: settings.gmail_app_password || prev.app_password,
        }));
        setUseSavedCredentials(true);
      }
    } catch (err) {
      console.error('Failed to load settings:', err);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleCSVUpload = (path, filename) => {
    setFormData(prev => ({
      ...prev,
      csv_path: path,
      database_table: '', // Clear database selection
    }));
  };

  const handleCSVError = (errorMessage) => {
    setError(`CSV Upload: ${errorMessage}`);
  };

  const handleTemplateSelect = (templateData) => {
    setFormData(prev => ({
      ...prev,
      subject: templateData.subject || prev.subject,
      vacancies_text: templateData.vacancies_text || prev.vacancies_text,
    }));
  };

  const handleDatabaseSelect = (selectedTables, tableConfigs) => {
    if (selectedTables && selectedTables.length > 0) {
      // Store as JSON array
      const databaseTables = JSON.stringify(selectedTables);
      // Use first table's email column (assuming all tables use same column name)
      const emailColumn = tableConfigs && tableConfigs[0] ? tableConfigs[0].emailColumn : 'email';
      
      setFormData(prev => ({
        ...prev,
        database_table: databaseTables,
        email_column: emailColumn,
        csv_path: '', // Clear CSV selection
      }));
    } else {
      setFormData(prev => ({
        ...prev,
        database_table: '',
        email_column: prev.email_column,
      }));
    }
  };

  const handleDatabaseError = (errorMessage) => {
    setError(`Database: ${errorMessage}`);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSubmitting(true);

    // Validate required fields
    if (!formData.name || !formData.subject || !formData.sender_email) {
      setError('Please fill in all required fields');
      setSubmitting(false);
      return;
    }

    // Validate data source
    if (dataSource === 'csv' && !formData.csv_path) {
      setError('Please upload a CSV file');
      setSubmitting(false);
      return;
    }

    if (dataSource === 'database' && !formData.database_table) {
      setError('Please select a database table');
      setSubmitting(false);
      return;
    }

    // Validate provider config - load from settings if using saved credentials
    let finalApiToken = formData.api_token;
    let finalAppPassword = formData.app_password;

    if (formData.provider === 'mailersend') {
      if (useSavedCredentials && !finalApiToken) {
        try {
          const settings = await getSettings();
          finalApiToken = settings.mailersend_api_token;
          if (!finalApiToken) {
            setError('MailerSend API token is required. Please enter it or save it in Settings.');
            setSubmitting(false);
            return;
          }
        } catch (err) {
          setError('Failed to load saved credentials. Please enter API token manually.');
          setSubmitting(false);
          return;
        }
      } else if (!useSavedCredentials && !finalApiToken) {
        setError('MailerSend API token is required');
        setSubmitting(false);
        return;
      }
    }

    if (formData.provider === 'gmail') {
      if (useSavedCredentials && !finalAppPassword) {
        try {
          const settings = await getSettings();
          finalAppPassword = settings.gmail_app_password;
          if (!finalAppPassword) {
            setError('Gmail App Password is required. Please enter it or save it in Settings.');
            setSubmitting(false);
            return;
          }
        } catch (err) {
          setError('Failed to load saved credentials. Please enter App Password manually.');
          setSubmitting(false);
          return;
        }
      } else if (!useSavedCredentials && !finalAppPassword) {
        setError('Gmail App Password is required');
        setSubmitting(false);
        return;
      }
    }

    try {
      // Build provider config
      const provider_config = formData.provider === 'mailersend'
        ? { api_token: finalApiToken }
        : { app_password: finalAppPassword };

      // Build campaign payload
      const campaignData = {
        name: formData.name,
        provider: formData.provider,
        subject: formData.subject,
        sender_email: formData.sender_email,
        email_column: formData.email_column || 'email',
        batch_size: parseInt(formData.batch_size) || 1,
        delay_between_batches: parseInt(formData.delay_between_batches) || 45,
        daily_limit: parseInt(formData.daily_limit) || 2000,
        provider_config,
        vacancies_text: formData.vacancies_text || '',
        html_body: null,
      };

      // Add data source
      if (dataSource === 'csv') {
        campaignData.csv_path = formData.csv_path;
      } else {
        // database_table is already a JSON string array
        campaignData.database_table = formData.database_table;
      }

      const result = await createCampaign(campaignData);
      
      if (result.success) {
        navigate(`/campaign/${result.campaign_id}`);
      } else {
        setError(result.error || 'Failed to create campaign');
      }
    } catch (err) {
      setError(err.response?.data?.error || err.message || 'Failed to create campaign');
    } finally {
      setSubmitting(false);
    }
  };

  const handlePreview = async () => {
    if (!formData.vacancies_text) {
      setError('Please enter vacancies text to preview');
      return;
    }

    setPreviewOpen(true);
    setPreviewLoading(true);
    setError('');

    try {
      const result = await previewEmail(
        formData.vacancies_text,
        formData.subject || 'ASAP Marine Update',
        null
      );
      
      if (result.success) {
        setPreviewHtml(result.html);
      } else {
        setError('Failed to generate preview: ' + (result.error || 'Unknown error'));
        setPreviewOpen(false);
      }
    } catch (err) {
      setError('Failed to generate preview: ' + err.message);
      setPreviewOpen(false);
    } finally {
      setPreviewLoading(false);
    }
  };

  return (
    <div className="campaign-form-container">
      <div className="campaign-form-page-header">
        <h2>Create New Campaign</h2>
        <p>Configure delivery on the left, prepare email content on the right.</p>
      </div>
      
      {error && <div className="error-message">{error}</div>}

      <form onSubmit={handleSubmit} className="campaign-form">
        <div className="campaign-form-layout">
          <div className="campaign-form-column">
            <div className="form-section">
              <h3>Basic Information</h3>
              
              <div className="form-group">
                <label htmlFor="name">Campaign Name *</label>
                <input
                  type="text"
                  id="name"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  required
                  placeholder="My Email Campaign"
                />
              </div>

              <div className="form-group">
                <label htmlFor="sender_email">Sender Email *</label>
                <input
                  type="email"
                  id="sender_email"
                  name="sender_email"
                  value={formData.sender_email}
                  onChange={handleChange}
                  required
                  placeholder="sender@example.com"
                />
              </div>
            </div>

            <div className="form-section">
              <h3>Email Provider</h3>
              
              <div className="form-group">
                <label>Provider *</label>
                <div className="radio-group">
                  <label>
                    <input
                      type="radio"
                      name="provider"
                      value="mailersend"
                      checked={formData.provider === 'mailersend'}
                      onChange={handleChange}
                    />
                    MailerSend
                  </label>
                  <label>
                    <input
                      type="radio"
                      name="provider"
                      value="gmail"
                      checked={formData.provider === 'gmail'}
                      onChange={handleChange}
                    />
                    Gmail
                  </label>
                </div>
              </div>

              {formData.provider === 'mailersend' && (
                <div className="form-group">
                  <div className="form-group-header">
                    <label htmlFor="api_token">MailerSend API Token *</label>
                    <label className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={useSavedCredentials}
                        onChange={(e) => {
                          setUseSavedCredentials(e.target.checked);
                          if (e.target.checked) {
                            loadSavedCredentials();
                          }
                        }}
                      />
                      Use saved credentials
                    </label>
                  </div>
                  <input
                    type="password"
                    id="api_token"
                    name="api_token"
                    value={formData.api_token}
                    onChange={handleChange}
                    required={formData.provider === 'mailersend'}
                    placeholder="mlsn.xxxxx"
                    disabled={useSavedCredentials}
                  />
                  {useSavedCredentials && formData.api_token && (
                    <small className="form-help">Using saved MailerSend API token from settings</small>
                  )}
                </div>
              )}

              {formData.provider === 'gmail' && (
                <div className="form-group">
                  <div className="form-group-header">
                    <label htmlFor="app_password">Gmail App Password *</label>
                    <label className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={useSavedCredentials}
                        onChange={(e) => {
                          setUseSavedCredentials(e.target.checked);
                          if (e.target.checked) {
                            loadSavedCredentials();
                          }
                        }}
                      />
                      Use saved credentials
                    </label>
                  </div>
                  <input
                    type="password"
                    id="app_password"
                    name="app_password"
                    value={formData.app_password}
                    onChange={handleChange}
                    required={formData.provider === 'gmail'}
                    placeholder="16-character app password"
                    disabled={useSavedCredentials}
                  />
                  {useSavedCredentials && formData.app_password && (
                    <small className="form-help">Using saved Gmail App Password from settings</small>
                  )}
                </div>
              )}
            </div>

            <div className="form-section">
              <h3>Data Source *</h3>
              
              <div className="form-group">
                <label>Source Type *</label>
                <div className="radio-group">
                  <label>
                    <input
                      type="radio"
                      name="data_source"
                      value="csv"
                      checked={dataSource === 'csv'}
                      onChange={(e) => setDataSource(e.target.value)}
                    />
                    Upload CSV File
                  </label>
                  <label>
                    <input
                      type="radio"
                      name="data_source"
                      value="database"
                      checked={dataSource === 'database'}
                      onChange={(e) => setDataSource(e.target.value)}
                    />
                    Select from Database
                  </label>
                </div>
              </div>

              {dataSource === 'csv' && (
                <div className="form-group">
                  <label>CSV File *</label>
                  <CSVUploader
                    onUploadSuccess={handleCSVUpload}
                    onError={handleCSVError}
                  />
                </div>
              )}

              {dataSource === 'database' && (
                <DatabaseSelector
                  onSelect={handleDatabaseSelect}
                  onError={handleDatabaseError}
                />
              )}
            </div>

            <div className="form-section form-section-compact">
              <h3>Advanced Settings</h3>

              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="batch_size">Batch Size</label>
                  <input
                    type="number"
                    id="batch_size"
                    name="batch_size"
                    value={formData.batch_size}
                    onChange={handleChange}
                    min="1"
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="delay_between_batches">Delay (seconds)</label>
                  <input
                    type="number"
                    id="delay_between_batches"
                    name="delay_between_batches"
                    value={formData.delay_between_batches}
                    onChange={handleChange}
                    min="0"
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="daily_limit">Daily Limit</label>
                  <input
                    type="number"
                    id="daily_limit"
                    name="daily_limit"
                    value={formData.daily_limit}
                    onChange={handleChange}
                    min="1"
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="campaign-form-column campaign-form-column-right">
            <div className="form-section form-section-sticky">
              <h3>Email Content</h3>

              <div className="form-group">
                <label htmlFor="subject">Email Subject *</label>
                <input
                  type="text"
                  id="subject"
                  name="subject"
                  value={formData.subject}
                  onChange={handleChange}
                  required
                  placeholder="Job Opportunities"
                />
              </div>
              
              <div className="form-group">
                <TemplateSelector 
                  onSelectTemplate={handleTemplateSelect}
                  selectedTemplateId={selectedTemplateId}
                />
              </div>
              
              <div className="form-group">
                <div className="form-group-header">
                  <label htmlFor="vacancies_text">Vacancies Text (plain text, will be auto-wrapped)</label>
                  <button 
                    type="button" 
                    className="btn-preview" 
                    onClick={handlePreview}
                    disabled={!formData.vacancies_text}
                  >
                    👁️ Preview
                  </button>
                </div>
                <textarea
                  id="vacancies_text"
                  name="vacancies_text"
                  value={formData.vacancies_text}
                  onChange={handleChange}
                  rows="18"
                  placeholder="Paste your vacancy text here..."
                />
              </div>

              <div className="form-actions form-actions-inline">
                <button type="button" onClick={() => navigate('/')} className="btn-secondary">
                  Cancel
                </button>
                <button type="submit" className="btn-primary" disabled={submitting}>
                  {submitting ? 'Creating...' : 'Create Campaign'}
                </button>
              </div>
            </div>
          </div>
        </div>

        <EmailPreviewModal
          isOpen={previewOpen}
          onClose={() => setPreviewOpen(false)}
          htmlContent={previewHtml}
          loading={previewLoading}
        />
      </form>
    </div>
  );
}

export default CampaignForm;
