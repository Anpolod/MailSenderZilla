import React, { useEffect, useState } from 'react';
import {
  downloadCampaignLogFile,
  getCampaignLogFileInfo,
  getCampaignLogs,
} from '../services/api';

function CampaignLogAccess({ campaignId }) {
  const [logInfo, setLogInfo] = useState(null);
  const [lines, setLines] = useState([]);
  const [monitorOpen, setMonitorOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!campaignId) return;
    loadLogInfo();
  }, [campaignId]);

  useEffect(() => {
    if (!campaignId || !monitorOpen) return;

    loadTail();
    const interval = setInterval(() => {
      loadLogInfo({ silent: true });
      loadTail({ silent: true });
    }, 3000);

    return () => clearInterval(interval);
  }, [campaignId, monitorOpen]);

  const loadLogInfo = async ({ silent = false } = {}) => {
    if (!silent) {
      setLoading(true);
    }
    try {
      const result = await getCampaignLogFileInfo(campaignId);
      setLogInfo(result);
      setError('');
    } catch (err) {
      setError('Failed to load log file info: ' + (err.message || 'Unknown error'));
    } finally {
      if (!silent) {
        setLoading(false);
      }
    }
  };

  const loadTail = async ({ silent = false } = {}) => {
    if (!silent) {
      setLoading(true);
    }
    try {
      const result = await getCampaignLogs(campaignId, 200);
      setLines(result);
      setError('');
    } catch (err) {
      setError('Failed to read log file: ' + (err.message || 'Unknown error'));
    } finally {
      if (!silent) {
        setLoading(false);
      }
    }
  };

  const handleDownload = async () => {
    try {
      const blob = await downloadCampaignLogFile(campaignId);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `campaign_${campaignId}.log`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError('Failed to download log file: ' + (err.response?.data?.error || err.message));
    }
  };

  const formatUpdatedAt = (value) => {
    if (!value) return 'N/A';
    try {
      return new Date(value).toLocaleString();
    } catch {
      return value;
    }
  };

  return (
    <div className="log-access-panel">
      <div className="log-access-header">
        <div>
          <h3>Campaign Log File</h3>
          <p>Logs are written only to a server file and are not streamed into the page.</p>
        </div>
        <div className="log-access-actions">
          <button onClick={loadLogInfo} className="btn-export" disabled={loading}>
            Refresh Info
          </button>
          <button onClick={handleDownload} className="btn-export" disabled={loading}>
            Download Log
          </button>
          <button
            onClick={() => setMonitorOpen((prev) => !prev)}
            className="btn-export"
            disabled={loading}
          >
            {monitorOpen ? 'Hide Monitor' : 'Open Monitor'}
          </button>
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}

      <div className="log-access-meta">
        <div><strong>Path:</strong> {logInfo?.path || 'N/A'}</div>
        <div><strong>Status:</strong> {logInfo?.exists ? 'Available' : 'Not created yet'}</div>
        <div><strong>Size:</strong> {logInfo?.size_bytes ?? 0} bytes</div>
        <div><strong>Updated:</strong> {formatUpdatedAt(logInfo?.updated_at)}</div>
      </div>

      {monitorOpen && (
        <div className="log-monitor">
          {lines.length === 0 ? (
            <div className="log-empty">Log file is empty right now.</div>
          ) : (
            <pre className="log-monitor-output">
              {lines.map((line, index) => (
                <div key={`${line.timestamp || 'log'}-${index}`}>{line.raw}</div>
              ))}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}

export default CampaignLogAccess;
