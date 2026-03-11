import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getCampaigns } from '../services/api';
import CampaignCard from './CampaignCard';
import SettingsModal from './SettingsModal';
import TemplateManager from './TemplateManager';

function Dashboard() {
  const navigate = useNavigate();
  const [campaigns, setCampaigns] = useState([]);
  const [filteredCampaigns, setFilteredCampaigns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [templatesOpen, setTemplatesOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState('ALL');
  const [filterProvider, setFilterProvider] = useState('ALL');

  const loadCampaigns = async ({ silent = false } = {}) => {
    try {
      if (!silent) {
        setLoading(true);
      }
      const data = await getCampaigns();
      setCampaigns(data);
      setError('');
      applyFilters(data);
    } catch (err) {
      setError('Failed to load campaigns: ' + (err.message || 'Unknown error'));
      console.error('Failed to load campaigns:', err);
    } finally {
      if (!silent) {
        setLoading(false);
      }
    }
  };

  const applyFilters = (campaignList) => {
    let filtered = campaignList || campaigns;

    // Filter by search query
    if (searchQuery) {
      filtered = filtered.filter(campaign =>
        campaign.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        campaign.subject?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        campaign.sender_email?.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }

    // Filter by status
    if (filterStatus !== 'ALL') {
      filtered = filtered.filter(campaign =>
        campaign.status?.toLowerCase() === filterStatus.toLowerCase()
      );
    }

    // Filter by provider
    if (filterProvider !== 'ALL') {
      filtered = filtered.filter(campaign =>
        campaign.provider?.toLowerCase() === filterProvider.toLowerCase()
      );
    }

    setFilteredCampaigns(filtered);
  };

  useEffect(() => {
    applyFilters(campaigns);
  }, [searchQuery, filterStatus, filterProvider, campaigns]);

  useEffect(() => {
    loadCampaigns();
    
    // Refresh campaigns in background without showing full-page loading state.
    const interval = setInterval(() => loadCampaigns({ silent: true }), 5000);
    
    return () => clearInterval(interval);
  }, []);

  if (loading && campaigns.length === 0) {
    return (
      <div className="dashboard">
        <div className="loading">Loading campaigns...</div>
      </div>
    );
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <div>
          <h1>MailSenderZilla</h1>
          <p>Bulk Email Campaign Manager</p>
        </div>
        <div className="header-actions">
          <button
            className="btn-secondary"
            onClick={() => setTemplatesOpen(true)}
            title="Manage Templates"
          >
            📝 Templates
          </button>
          <button
            className="btn-secondary"
            onClick={() => setSettingsOpen(true)}
            title="Settings"
          >
            ⚙️ Settings
          </button>
          <button
            className="btn-primary"
            onClick={() => navigate('/campaign/new')}
          >
            + Create Campaign
          </button>
        </div>
      </div>

      <SettingsModal
        isOpen={settingsOpen}
        onClose={() => setSettingsOpen(false)}
      />

      <TemplateManager
        isOpen={templatesOpen}
        onClose={() => setTemplatesOpen(false)}
      />

      {error && <div className="error-message">{error}</div>}

      <div className="campaigns-section">
        <div className="campaigns-header">
          <h2>Campaigns ({filteredCampaigns.length} / {campaigns.length})</h2>
          
          <div className="campaigns-filters">
            <div className="filter-group">
              <label>Search:</label>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search campaigns..."
                className="filter-input"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="filter-clear"
                  title="Clear search"
                >
                  ×
                </button>
              )}
            </div>
            
            <div className="filter-group">
              <label>Status:</label>
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="filter-select"
              >
                <option value="ALL">All Status</option>
                <option value="pending">Pending</option>
                <option value="running">Running</option>
                <option value="paused">Paused</option>
                <option value="completed">Completed</option>
                <option value="failed">Failed</option>
              </select>
            </div>
            
            <div className="filter-group">
              <label>Provider:</label>
              <select
                value={filterProvider}
                onChange={(e) => setFilterProvider(e.target.value)}
                className="filter-select"
              >
                <option value="ALL">All Providers</option>
                <option value="mailersend">MailerSend</option>
                <option value="gmail">Gmail</option>
              </select>
            </div>
          </div>
        </div>
        
        {campaigns.length === 0 ? (
          <div className="empty-state">
            <p>No campaigns yet. Create one to get started.</p>
            <button
              className="btn-primary"
              onClick={() => navigate('/campaign/new')}
            >
              Create Your First Campaign
            </button>
          </div>
        ) : filteredCampaigns.length === 0 ? (
          <div className="empty-state">
            <p>No campaigns match the current filters.</p>
            <button
              className="btn-secondary"
              onClick={() => {
                setSearchQuery('');
                setFilterStatus('ALL');
                setFilterProvider('ALL');
              }}
            >
              Clear Filters
            </button>
          </div>
        ) : (
          <div className="campaigns-grid">
            {filteredCampaigns.map(campaign => (
              <CampaignCard
                key={campaign.id}
                campaign={campaign}
                onClone={loadCampaigns}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default Dashboard;
