import React, { useState, useEffect } from 'react';
import { getSettings, updateSettings, createBackup, listBackups, restoreBackup, deleteBackup } from '../services/api';

function SettingsModal({ isOpen, onClose, onSave }) {
  const [settings, setSettings] = useState({
    mailersend_api_token: '',
    gmail_app_password: '',
    telegram_bot_token: '',
    telegram_chat_id: '',
  });
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [activeTab, setActiveTab] = useState('credentials');
  const [backups, setBackups] = useState([]);
  const [backupLoading, setBackupLoading] = useState(false);
  const [backupError, setBackupError] = useState('');

  useEffect(() => {
    if (isOpen) {
      loadSettings();
      if (activeTab === 'backup') {
        loadBackups();
      }
    }
  }, [isOpen, activeTab]);

  const loadSettings = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await getSettings();
      setSettings({
        mailersend_api_token: data.mailersend_api_token || '',
        gmail_app_password: data.gmail_app_password || '',
        telegram_bot_token: data.telegram_bot_token || '',
        telegram_chat_id: data.telegram_chat_id || '',
      });
    } catch (err) {
      setError('Failed to load settings: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setSettings(prev => ({
      ...prev,
      [name]: value,
    }));
  };

  const loadBackups = async () => {
    setBackupLoading(true);
    setBackupError('');
    try {
      const result = await listBackups();
      if (result.success) {
        setBackups(result.backups || []);
      }
    } catch (err) {
      setBackupError('Failed to load backups: ' + err.message);
    } finally {
      setBackupLoading(false);
    }
  };

  const handleCreateBackup = async () => {
    setBackupLoading(true);
    setBackupError('');
    try {
      const result = await createBackup();
      if (result.success) {
        alert('Backup created successfully!');
        await loadBackups();
      } else {
        setBackupError(result.error || 'Failed to create backup');
      }
    } catch (err) {
      setBackupError('Failed to create backup: ' + err.message);
    } finally {
      setBackupLoading(false);
    }
  };

  const handleRestoreBackup = async (backupPath) => {
    if (!window.confirm('Are you sure you want to restore this backup? This will replace the current database. A safety backup will be created first.')) {
      return;
    }

    setBackupLoading(true);
    setBackupError('');
    try {
      const result = await restoreBackup(backupPath);
      if (result.success) {
        alert('Database restored successfully! Please refresh the page.');
        window.location.reload();
      } else {
        setBackupError(result.error || 'Failed to restore backup');
      }
    } catch (err) {
      setBackupError('Failed to restore backup: ' + err.message);
    } finally {
      setBackupLoading(false);
    }
  };

  const handleDeleteBackup = async (backupPath) => {
    if (!window.confirm('Are you sure you want to delete this backup?')) {
      return;
    }

    try {
      const result = await deleteBackup(backupPath);
      if (result.success) {
        await loadBackups();
      } else {
        setBackupError(result.error || 'Failed to delete backup');
      }
    } catch (err) {
      setBackupError('Failed to delete backup: ' + err.message);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    setSuccess('');

    try {
      const result = await updateSettings(settings);
      if (result.success) {
        setSuccess('Settings saved successfully!');
        if (onSave) {
          onSave(settings);
        }
        setTimeout(() => {
          onClose();
        }, 1000);
      } else {
        setError(result.error || 'Failed to save settings');
      }
    } catch (err) {
      setError('Failed to save settings: ' + err.message);
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content settings-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Settings</h2>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>
        
        <div className="settings-tabs">
          <button
            className={`settings-tab ${activeTab === 'credentials' ? 'active' : ''}`}
            onClick={() => setActiveTab('credentials')}
          >
            Credentials
          </button>
          <button
            className={`settings-tab ${activeTab === 'backup' ? 'active' : ''}`}
            onClick={() => setActiveTab('backup')}
          >
            Database Backup
          </button>
        </div>
        
        {activeTab === 'credentials' && loading ? (
          <div className="loading">Loading settings...</div>
        ) : (
          <form onSubmit={handleSubmit}>
            <div className="modal-body">
              {error && <div className="error-message">{error}</div>}
              {success && <div className="success-message">{success}</div>}

              <div className="form-section">
                <h3>Email Provider Credentials</h3>
                
                <div className="form-group">
                  <label htmlFor="mailersend_api_token">MailerSend API Token</label>
                  <input
                    type="password"
                    id="mailersend_api_token"
                    name="mailersend_api_token"
                    value={settings.mailersend_api_token}
                    onChange={handleChange}
                    placeholder="mlsn.xxxxx"
                  />
                  <small className="form-help">Your MailerSend API token. Will be used when creating campaigns with MailerSend provider.</small>
                </div>

                <div className="form-group">
                  <label htmlFor="gmail_app_password">Gmail App Password</label>
                  <input
                    type="password"
                    id="gmail_app_password"
                    name="gmail_app_password"
                    value={settings.gmail_app_password}
                    onChange={handleChange}
                    placeholder="16-character app password"
                  />
                  <small className="form-help">Your Gmail App Password. Will be used when creating campaigns with Gmail provider.</small>
                </div>
              </div>

              <div className="form-section">
                <h3>Telegram Notifications (Optional)</h3>
                
                <div className="form-group">
                  <label htmlFor="telegram_bot_token">Telegram Bot Token</label>
                  <input
                    type="text"
                    id="telegram_bot_token"
                    name="telegram_bot_token"
                    value={settings.telegram_bot_token}
                    onChange={handleChange}
                    placeholder="123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="telegram_chat_id">Telegram Chat ID</label>
                  <input
                    type="text"
                    id="telegram_chat_id"
                    name="telegram_chat_id"
                    value={settings.telegram_chat_id}
                    onChange={handleChange}
                    placeholder="123456789"
                  />
                </div>
              </div>
            </div>

            <div className="modal-footer">
              <button type="button" className="btn-secondary" onClick={onClose}>
                Cancel
              </button>
              <button type="submit" className="btn-primary" disabled={saving}>
                {saving ? 'Saving...' : 'Save Settings'}
              </button>
            </div>
          </form>
        )}
        
        {activeTab === 'backup' && (
          <div className="modal-body">
            {backupError && <div className="error-message">{backupError}</div>}
            
            <div className="backup-section">
              <div className="backup-toolbar">
                <button
                  onClick={handleCreateBackup}
                  disabled={backupLoading}
                  className="btn-primary"
                >
                  {backupLoading ? 'Creating...' : '💾 Create Backup'}
                </button>
                <button
                  onClick={loadBackups}
                  disabled={backupLoading}
                  className="btn-secondary"
                >
                  🔄 Refresh List
                </button>
              </div>
              
              <h3>Available Backups ({backups.length})</h3>
              
              {backupLoading ? (
                <div className="loading">Loading backups...</div>
              ) : backups.length === 0 ? (
                <div className="empty-state">No backups found. Create your first backup!</div>
              ) : (
                <div className="backups-list">
                  {backups.map((backup, index) => (
                    <div key={index} className="backup-item">
                      <div className="backup-info">
                        <div className="backup-name">{backup.filename}</div>
                        <div className="backup-meta">
                          Created: {new Date(backup.created_at || backup.created).toLocaleString()} | 
                          Size: {backup.size_mb || (backup.size_bytes / 1024 / 1024).toFixed(2)} MB
                        </div>
                      </div>
                      <div className="backup-item-actions">
                        <button
                          onClick={() => handleRestoreBackup(backup.filename || backup.path)}
                          className="btn-restore-backup"
                          title="Restore this backup"
                        >
                          🔄 Restore
                        </button>
                        <button
                          onClick={() => handleDeleteBackup(backup.filename || backup.path)}
                          className="btn-delete-backup"
                          title="Delete this backup"
                        >
                          🗑️ Delete
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
            
            <div className="modal-footer">
              <button type="button" className="btn-secondary" onClick={onClose}>
                Close
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default SettingsModal;
