import React, { useState, useEffect, useRef } from 'react';
import io from 'socket.io-client';
import { getCampaignLogs } from '../services/api';

function LogPanel({ campaignId }) {
  const [logs, setLogs] = useState([]);
  const [socket, setSocket] = useState(null);
  const [connected, setConnected] = useState(false);
  const [filterLevel, setFilterLevel] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [autoScroll, setAutoScroll] = useState(true);
  const logContainerRef = useRef(null);

  // Load existing logs from database on mount
  useEffect(() => {
    if (!campaignId) return;
    
    const loadInitialLogs = async () => {
      try {
        const existingLogs = await getCampaignLogs(campaignId);
        setLogs(existingLogs.map(log => ({
          level: log.level,
          message: log.message,
          timestamp: log.ts,
        })));
      } catch (err) {
        console.error('Failed to load initial logs:', err);
      }
    };
    
    loadInitialLogs();
  }, [campaignId]);

  useEffect(() => {
    if (!campaignId) return;

    // Connect to WebSocket
    // In development, Vite proxies /socket.io to http://localhost:5000
    // In production, use the full URL or configure accordingly
    const socketUrl = import.meta.env.VITE_SOCKET_URL || window.location.origin;
    const newSocket = io(socketUrl, {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      reconnectionAttempts: Infinity,
      timeout: 20000,
    });

    newSocket.on('connect', () => {
      setConnected(true);
      // Join campaign room
      newSocket.emit('join_campaign', { campaign_id: campaignId });
    });

    newSocket.on('disconnect', (reason) => {
      setConnected(false);
      // Log disconnect reason (helpful for debugging)
      if (reason === 'io server disconnect') {
        // Server disconnected, need to manually reconnect
        newSocket.connect();
      }
    });

    newSocket.on('connect_error', (error) => {
      setConnected(false);
      console.log('Socket connection error:', error.message);
    });

    newSocket.on('reconnect', (attemptNumber) => {
      setConnected(true);
      // Rejoin campaign room after reconnection
      newSocket.emit('join_campaign', { campaign_id: campaignId });
      console.log('Socket reconnected after', attemptNumber, 'attempts');
    });

    newSocket.on('reconnect_attempt', () => {
      console.log('Attempting to reconnect...');
    });

    newSocket.on('reconnect_error', (error) => {
      console.log('Reconnection error:', error.message);
    });

    newSocket.on('campaign_log', (data) => {
      if (data.campaign_id === campaignId) {
        setLogs(prev => [...prev, {
          level: data.level,
          message: data.message,
          timestamp: data.timestamp,
        }]);
      }
    });

    setSocket(newSocket);

    return () => {
      newSocket.close();
    };
  }, [campaignId]);

  // Auto-scroll to bottom (only if autoScroll is enabled and user is near bottom)
  useEffect(() => {
    if (autoScroll && logContainerRef.current) {
      const container = logContainerRef.current;
      const isNearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 100;
      if (isNearBottom) {
        container.scrollTop = container.scrollHeight;
      }
    }
  }, [logs, autoScroll]);

  // Filter logs based on level and search query
  const filteredLogs = logs.filter(log => {
    // Filter by level
    if (filterLevel !== 'ALL' && log.level?.toUpperCase() !== filterLevel) {
      return false;
    }
    
    // Filter by search query
    if (searchQuery && !log.message.toLowerCase().includes(searchQuery.toLowerCase())) {
      return false;
    }
    
    return true;
  });

  const handleScroll = () => {
    if (logContainerRef.current) {
      const container = logContainerRef.current;
      const isAtBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 50;
      setAutoScroll(isAtBottom);
    }
  };

  const getLogLevelClass = (level) => {
    switch (level?.toUpperCase()) {
      case 'SUCCESS':
        return 'log-success';
      case 'WARNING':
        return 'log-warning';
      case 'ERROR':
        return 'log-error';
      case 'INFO':
      default:
        return 'log-info';
    }
  };

  const formatTimestamp = (timestamp) => {
    if (!timestamp) return '';
    try {
      return new Date(timestamp).toLocaleTimeString();
    } catch {
      return timestamp;
    }
  };

  return (
    <div className="log-panel">
      <div className="log-panel-header">
        <h3>Campaign Logs ({filteredLogs.length} / {logs.length})</h3>
        <span className={`connection-status ${connected ? 'connected' : 'disconnected'}`}>
          {connected ? '● Connected' : '○ Disconnected'}
        </span>
      </div>
      
      <div className="log-filters">
        <div className="log-filter-group">
          <label>Filter by Level:</label>
          <select 
            value={filterLevel} 
            onChange={(e) => setFilterLevel(e.target.value)}
            className="log-filter-select"
          >
            <option value="ALL">All Levels</option>
            <option value="SUCCESS">Success</option>
            <option value="INFO">Info</option>
            <option value="WARNING">Warning</option>
            <option value="ERROR">Error</option>
          </select>
        </div>
        
        <div className="log-filter-group">
          <label>Search:</label>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search in logs..."
            className="log-search-input"
          />
          {searchQuery && (
            <button 
              onClick={() => setSearchQuery('')}
              className="log-clear-search"
              title="Clear search"
            >
              ×
            </button>
          )}
        </div>
        
        <div className="log-filter-group">
          <label>
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
            />
            {' '}Auto-scroll
          </label>
        </div>
      </div>
      
      <div 
        className="log-container" 
        ref={logContainerRef}
        onScroll={handleScroll}
      >
        {logs.length === 0 ? (
          <div className="log-empty">No logs yet. Campaign will stream logs here in real-time.</div>
        ) : filteredLogs.length === 0 ? (
          <div className="log-empty">No logs match the current filters.</div>
        ) : (
          filteredLogs.map((log, index) => (
            <div key={index} className={`log-entry ${getLogLevelClass(log.level)}`}>
              <span className="log-timestamp">[{formatTimestamp(log.timestamp)}]</span>
              <span className="log-level">[{log.level}]</span>
              <span className="log-message">{log.message}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default LogPanel;
