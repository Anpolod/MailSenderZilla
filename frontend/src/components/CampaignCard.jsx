import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { cloneCampaign } from '../services/api';

function CampaignCard({ campaign, onClone }) {
  const navigate = useNavigate();
  const [cloning, setCloning] = useState(false);

  const handleClone = async (e) => {
    e.stopPropagation(); // Prevent navigation
    
    if (!window.confirm(`Clone campaign "${campaign.name}"?`)) {
      return;
    }

    setCloning(true);
    try {
      const newName = prompt('Enter name for cloned campaign (or leave empty for default):', `${campaign.name} (Copy)`);
      const result = await cloneCampaign(campaign.id, newName || null);
      if (result.success) {
        alert('Campaign cloned successfully!');
        if (onClone) {
          onClone();
        }
      } else {
        alert('Failed to clone campaign: ' + (result.error || 'Unknown error'));
      }
    } catch (err) {
      alert('Failed to clone campaign: ' + (err.message || 'Unknown error'));
    } finally {
      setCloning(false);
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

  const handleClick = () => {
    navigate(`/campaign/${campaign.id}`);
  };

  return (
    <div className="campaign-card" onClick={handleClick}>
      <div className="campaign-card-header">
        <h3>{campaign.name}</h3>
        <div className="campaign-card-header-actions">
          <button
            onClick={handleClone}
            disabled={cloning}
            className="btn-clone-card"
            title="Clone Campaign"
          >
            {cloning ? '...' : '📋'}
          </button>
          <span className={`status-badge ${getStatusColor(campaign.status)}`}>
            {campaign.status || 'pending'}
          </span>
        </div>
      </div>
      
      <div className="campaign-card-body">
        <div className="campaign-info">
          <span className="info-label">Provider:</span>
          <span className={`provider-badge ${
            campaign.provider?.toLowerCase() === 'mailersend' 
              ? 'provider-mailersend' 
              : 'provider-gmail'
          }`}>
            {campaign.provider || 'N/A'}
          </span>
        </div>
        
        <div className="campaign-info">
          <span className="info-label">Subject:</span>
          <span className="info-value">{campaign.subject || 'N/A'}</span>
        </div>

        <div className="campaign-stats">
          <div className="stat">
            <span className="stat-label">Sent:</span>
            <span className="stat-value success">{campaign.success_cnt || 0}</span>
          </div>
          <div className="stat">
            <span className="stat-label">Errors:</span>
            <span className="stat-value error">{campaign.error_cnt || 0}</span>
          </div>
        </div>

        <div className="campaign-info">
          <span className="info-label">Started:</span>
          <span className="info-value">{formatDate(campaign.start_ts)}</span>
        </div>
      </div>
    </div>
  );
}

export default CampaignCard;
