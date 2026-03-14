import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  getCampaign, 
  restartCampaign, 
  deleteCampaign, 
  startCampaign,
  pauseCampaign,
  resumeCampaign,
  exportCampaignLogs,
  exportCampaignSent,
  exportCampaignFailed,
  exportCampaignAll,
  exportCampaignStatistics
} from '../services/api';
import CampaignLogAccess from './CampaignLogAccess';

function CampaignDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [campaign, setCampaign] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionLoading, setActionLoading] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  useEffect(() => {
    loadCampaign();
    
    // Refresh campaign details in background without full-page loading state.
    const interval = setInterval(() => loadCampaign({ silent: true }), 3000);
    
    return () => clearInterval(interval);
  }, [id]);

  const loadCampaign = async ({ silent = false } = {}) => {
    try {
      const data = await getCampaign(id);
      setCampaign(data);
      setError('');
    } catch (err) {
      setError('Failed to load campaign: ' + (err.message || 'Unknown error'));
      console.error('Failed to load campaign:', err);
    } finally {
      if (!silent) {
        setLoading(false);
      }
    }
  };

  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'running':
        return 'status-running';
      case 'completed':
        return 'status-completed';
      case 'failed':
        return 'status-failed';
      case 'paused':
        return 'status-paused';
      default:
        return 'status-pending';
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    try {
      return new Date(dateString).toLocaleString();
    } catch {
      return dateString;
    }
  };

  const canRestart = () => {
    if (!campaign) return false;
    const status = campaign.status?.toLowerCase();
    return status === 'completed' || status === 'failed' || status === 'paused' || status === 'running';
  };

  const canDelete = () => {
    if (!campaign) return false;
    return true;
  };

  const canStart = () => {
    if (!campaign) return false;
    const status = campaign.status?.toLowerCase();
    return status === 'pending';
  };

  const canPause = () => {
    if (!campaign) return false;
    const status = campaign.status?.toLowerCase();
    return status === 'running';
  };

  const canResume = () => {
    if (!campaign) return false;
    const status = campaign.status?.toLowerCase();
    return status === 'paused';
  };

  const handleRestart = async () => {
    if (!canRestart()) return;
    
    if (!window.confirm('Are you sure you want to restart this campaign? This will reset the statistics and start from the beginning.')) {
      return;
    }

    setActionLoading(true);
    setError('');
    
    try {
      const result = await restartCampaign(id);
      if (result.success) {
        // Reload campaign to show updated status
        await loadCampaign();
        // Show message or warning if present
        if (result.warning) {
          alert(result.warning);
        } else if (result.message) {
          alert(result.message);
        } else {
          alert('Campaign reset successfully!');
        }
      } else {
        setError(result.error || 'Failed to restart campaign');
      }
    } catch (err) {
      setError('Failed to restart campaign: ' + (err.response?.data?.error || err.message));
    } finally {
      setActionLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!canDelete()) return;
    
    if (!window.confirm(`Are you sure you want to delete campaign "${campaign.name}"? This action cannot be undone and will delete all associated logs.`)) {
      return;
    }

    setActionLoading(true);
    setError('');
    
    try {
      const result = await deleteCampaign(id);
      if (result.success) {
        // Redirect to dashboard after successful deletion
        navigate('/');
      } else {
        setError(result.error || 'Failed to delete campaign');
        setActionLoading(false);
      }
    } catch (err) {
      setError('Failed to delete campaign: ' + (err.response?.data?.error || err.message));
      setActionLoading(false);
    }
  };

  const handleStart = async () => {
    if (!canStart()) return;
    
    if (!window.confirm('Are you sure you want to start this campaign? It will begin sending emails immediately.')) {
      return;
    }

    setActionLoading(true);
    setError('');
    
    try {
      // Start campaign (will use saved credentials from settings if available)
      const result = await startCampaign(id);
      if (result.success) {
        // Reload campaign to show updated status
        await loadCampaign();
        alert(result.message || 'Campaign started successfully!');
      } else {
        setError(result.error || 'Failed to start campaign');
      }
    } catch (err) {
      setError('Failed to start campaign: ' + (err.response?.data?.error || err.message));
    } finally {
      setActionLoading(false);
    }
  };

  const handlePause = async () => {
    if (!canPause()) return;
    
    if (!window.confirm('Are you sure you want to pause this campaign? It will stop sending emails after the current batch completes.')) {
      return;
    }

    setActionLoading(true);
    setError('');
    
    try {
      const result = await pauseCampaign(id);
      if (result.success) {
        await loadCampaign();
        alert(result.message || 'Campaign paused successfully!');
      } else {
        setError(result.error || 'Failed to pause campaign');
      }
    } catch (err) {
      setError('Failed to pause campaign: ' + (err.response?.data?.error || err.message));
    } finally {
      setActionLoading(false);
    }
  };

  const handleResume = async () => {
    if (!canResume()) return;
    
    if (!window.confirm('Are you sure you want to resume this campaign? It will continue sending from where it left off.')) {
      return;
    }

    setActionLoading(true);
    setError('');
    
    try {
      // Resume campaign (will use saved credentials from settings if available)
      const result = await resumeCampaign(id);
      if (result.success) {
        await loadCampaign();
        alert(result.message || 'Campaign resumed successfully!');
      } else {
        setError(result.error || 'Failed to resume campaign');
      }
    } catch (err) {
      setError('Failed to resume campaign: ' + (err.response?.data?.error || err.message));
    } finally {
      setActionLoading(false);
    }
  };

  const handleExport = async (exportType) => {
    try {
      let blob;
      let filename;
      
      switch (exportType) {
        case 'logs':
          blob = await exportCampaignLogs(id);
          filename = `campaign_${id}_logs.csv`;
          break;
        case 'sent':
          blob = await exportCampaignSent(id);
          filename = `campaign_${id}_sent.csv`;
          break;
        case 'failed':
          blob = await exportCampaignFailed(id);
          filename = `campaign_${id}_failed.csv`;
          break;
        case 'all':
          blob = await exportCampaignAll(id);
          filename = `campaign_${id}_all_emails.csv`;
          break;
        case 'statistics':
          blob = await exportCampaignStatistics(id);
          filename = `campaign_${id}_statistics.csv`;
          break;
        default:
          return;
      }
      
      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError('Failed to export: ' + (err.response?.data?.error || err.message));
      console.error('Export error:', err);
    }
  };

  if (loading && !campaign) {
    return (
      <div className="campaign-detail">
        <div className="loading">Loading campaign...</div>
      </div>
    );
  }

  if (error && !campaign) {
    return (
      <div className="campaign-detail">
        <div className="error-message">{error}</div>
        <button onClick={() => navigate('/')} className="btn-secondary">
          Back to Dashboard
        </button>
      </div>
    );
  }

  if (!campaign) {
    return (
      <div className="campaign-detail">
        <div className="error-message">Campaign not found</div>
        <button onClick={() => navigate('/')} className="btn-secondary">
          Back to Dashboard
        </button>
      </div>
    );
  }

  return (
    <div className="campaign-detail">
      <div className="campaign-detail-header">
        <button onClick={() => navigate('/')} className="btn-secondary">
          ← Back to Dashboard
        </button>
        <div className="header-title-section">
          <h1>{campaign.name}</h1>
          <span className={`status-badge ${getStatusColor(campaign.status)}`}>
            {campaign.status || 'pending'}
          </span>
        </div>
        <div className="header-actions">
          {canStart() && (
            <button
              onClick={handleStart}
              disabled={actionLoading}
              className="btn-start"
              title="Start Campaign"
            >
              ▶️ {actionLoading ? 'Starting...' : 'Start'}
            </button>
          )}
          {canPause() && (
            <button
              onClick={handlePause}
              disabled={actionLoading}
              className="btn-pause"
              title="Pause Campaign"
            >
              ⏸️ {actionLoading ? 'Pausing...' : 'Pause'}
            </button>
          )}
          {canResume() && (
            <button
              onClick={handleResume}
              disabled={actionLoading}
              className="btn-resume"
              title="Resume Campaign"
            >
              ▶️ {actionLoading ? 'Resuming...' : 'Resume'}
            </button>
          )}
          {canRestart() && (
            <button
              onClick={handleRestart}
              disabled={actionLoading}
              className="btn-restart"
              title="Restart Campaign"
            >
              🔄 {actionLoading ? 'Restarting...' : 'Restart'}
            </button>
          )}
          {canDelete() && (
            <button
              onClick={handleDelete}
              disabled={actionLoading}
              className="btn-delete"
              title="Delete Campaign"
            >
              🗑️ {actionLoading ? 'Deleting...' : 'Delete'}
            </button>
          )}
        </div>
      </div>

      <div className="campaign-detail-content">
        <div className="campaign-info-section">
          <h2>Campaign Information</h2>
          
          <div className="info-grid">
            <div className="info-item">
              <label>Provider:</label>
              <span>{campaign.provider || 'N/A'}</span>
            </div>
            
            <div className="info-item">
              <label>Subject:</label>
              <span>{campaign.subject || 'N/A'}</span>
            </div>
            
            <div className="info-item">
              <label>Sender Email:</label>
              <span>{campaign.sender_email || 'N/A'}</span>
            </div>
            
            <div className="info-item">
              <label>Data Source:</label>
              <span>
                {campaign.database_table ? (
                  <>Database Table: <strong>{campaign.database_table}</strong></>
                ) : campaign.csv_path ? (
                  <>CSV File: <strong>{campaign.csv_path.split('/').pop()}</strong></>
                ) : (
                  'N/A'
                )}
              </span>
            </div>
            
            <div className="info-item">
              <label>Email Column:</label>
              <span>{campaign.email_column || 'N/A'}</span>
            </div>
            
            <div className="info-item">
              <label>Batch Size:</label>
              <span>{campaign.batch_size || 'N/A'}</span>
            </div>
            
            <div className="info-item">
              <label>Delay Between Batches:</label>
              <span>{campaign.delay_between_batches || 'N/A'} seconds</span>
            </div>
            
            <div className="info-item">
              <label>Daily Limit:</label>
              <span>{campaign.daily_limit || 'N/A'}</span>
            </div>
            
            <div className="info-item">
              <label>Started:</label>
              <span>{formatDate(campaign.start_ts)}</span>
            </div>
            
            <div className="info-item">
              <label>Ended:</label>
              <span>{formatDate(campaign.end_ts)}</span>
            </div>
          </div>

          <div className="campaign-stats-section">
            <h3>Statistics</h3>
            <div className="stats-grid">
              <div className="stat-card success">
                <div className="stat-label">Successfully Sent</div>
                <div className="stat-value">{campaign.success_cnt || 0}</div>
              </div>
              <div className="stat-card error">
                <div className="stat-label">Errors</div>
                <div className="stat-value">{campaign.error_cnt || 0}</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">Total</div>
                <div className="stat-value">
                  {(campaign.success_cnt || 0) + (campaign.error_cnt || 0)}
                </div>
              </div>
            </div>
          </div>

          <div className="campaign-export-section">
            <h3>Export Data</h3>
            <div className="export-buttons">
              <button 
                onClick={() => handleExport('logs')} 
                className="btn-export"
                title="Export all campaign logs"
              >
                📋 Export Logs
              </button>
              <button 
                onClick={() => handleExport('sent')} 
                className="btn-export"
                title="Export successfully sent emails"
              >
                ✅ Export Sent
              </button>
              <button 
                onClick={() => handleExport('failed')} 
                className="btn-export"
                title="Export failed emails"
              >
                ❌ Export Failed
              </button>
              <button 
                onClick={() => handleExport('all')} 
                className="btn-export"
                title="Export all emails with status"
              >
                📊 Export All Emails
              </button>
              <button 
                onClick={() => handleExport('statistics')} 
                className="btn-export"
                title="Export campaign statistics"
              >
                📈 Export Statistics
              </button>
            </div>
          </div>
        </div>

        <div className="campaign-logs-section">
          <CampaignLogAccess campaignId={parseInt(id, 10)} />
        </div>
      </div>
    </div>
  );
}

export default CampaignDetail;
