import React, { useState, useEffect } from 'react';
import { getDatabaseTables, getTableColumns, previewTable } from '../services/api';

function DatabaseSelector({ onSelect, onError }) {
  const [tables, setTables] = useState([]);
  const [selectedTables, setSelectedTables] = useState([]);
  const [tableConfigs, setTableConfigs] = useState({}); // {tableName: {emailColumn: string, totalCount: number}}
  const [previews, setPreviews] = useState({});
  const [loading, setLoading] = useState(false);
  const [loadingPreviews, setLoadingPreviews] = useState({});

  useEffect(() => {
    loadTables();
  }, []);

  useEffect(() => {
    // Notify parent of selection changes
    if (selectedTables.length > 0) {
      const configs = selectedTables.map(table => ({
        table: table,
        emailColumn: tableConfigs[table]?.emailColumn || null
      }));
      if (onSelect) {
        onSelect(selectedTables, configs);
      }
    } else {
      if (onSelect) {
        onSelect(null, null);
      }
    }
  }, [selectedTables, tableConfigs]);

  const loadTables = async () => {
    try {
      setLoading(true);
      const result = await getDatabaseTables();
      if (result.success) {
        const tablesList = result.tables || [];
        setTables(tablesList);
        if (tablesList.length === 0) {
          if (onError) onError('No tables found in the database. Please check if your database file exists and contains tables.');
        }
      } else {
        if (onError) onError(result.error || 'Failed to load database tables');
      }
    } catch (error) {
      if (onError) onError('Failed to load database tables: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleTableToggle = async (tableName) => {
    if (selectedTables.includes(tableName)) {
      // Remove table
      setSelectedTables(prev => prev.filter(t => t !== tableName));
      const newConfigs = { ...tableConfigs };
      delete newConfigs[tableName];
      setTableConfigs(newConfigs);
      const newPreviews = { ...previews };
      delete newPreviews[tableName];
      setPreviews(newPreviews);
    } else {
      // Add table
      setSelectedTables(prev => [...prev, tableName]);
      
      // Load columns and auto-detect email column
      try {
        const result = await getTableColumns(tableName);
        if (result.success) {
          const detectedEmailColumn = result.email_column;
          const tableColumns = result.columns || [];
          
          setTableConfigs(prev => ({
            ...prev,
            [tableName]: { 
              emailColumn: detectedEmailColumn || '',
              columns: tableColumns
            }
          }));
          
          if (detectedEmailColumn) {
            await loadPreview(tableName, detectedEmailColumn);
          }
        } else {
          if (onError) onError(result.error || 'Failed to load table columns');
        }
      } catch (error) {
        if (onError) onError('Failed to load table columns: ' + error.message);
      }
    }
  };

  const handleEmailColumnChange = async (tableName, columnName) => {
    setTableConfigs(prev => ({
      ...prev,
      [tableName]: { ...prev[tableName], emailColumn: columnName }
    }));
    if (columnName) {
      await loadPreview(tableName, columnName);
    }
  };

  const loadPreview = async (tableName, emailColumn) => {
    try {
      setLoadingPreviews(prev => ({ ...prev, [tableName]: true }));
      const result = await previewTable(tableName, emailColumn, 5);
      if (result.success) {
        setPreviews(prev => ({
          ...prev,
          [tableName]: result
        }));
        // Update total count in config
        setTableConfigs(prev => ({
          ...prev,
          [tableName]: {
            ...prev[tableName],
            totalCount: result.total_count || 0
          }
        }));
      }
    } catch (error) {
      console.error(`Failed to load preview for ${tableName}:`, error);
    } finally {
      setLoadingPreviews(prev => ({ ...prev, [tableName]: false }));
    }
  };

  // Calculate total email count
  const totalEmailCount = selectedTables.reduce((total, tableName) => {
    const count = tableConfigs[tableName]?.totalCount || 0;
    return total + count;
  }, 0);

  return (
    <div className="database-selector">
      <div className="form-group">
        <label>Select Database Tables *</label>
        
        {loading ? (
          <div className="loading">Loading tables...</div>
        ) : tables.length === 0 ? (
          <div className="empty-state">
            <p>No tables found in the database. Please make sure your database file exists and contains tables.</p>
          </div>
        ) : (
          <>
            <div className="db-tree">
              <div className="tree-root">
                <span className="tree-node-icon">▾</span>
                <span className="tree-node-title">Main_DataBase.db</span>
                <span className="tree-root-meta">{tables.length} tables</span>
              </div>

              <div className="tree-children">
                {tables.map(table => {
                  const isSelected = selectedTables.includes(table);
                  const config = tableConfigs[table];
                  const preview = previews[table];
                  const columns = config?.columns || [];
                  
                  return (
                    <div key={table} className={`tree-node ${isSelected ? 'selected' : ''}`}>
                      <div className="tree-node-content">
                        <label className="tree-checkbox-label">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => handleTableToggle(table)}
                          />
                          <span className="tree-table-name">{table}</span>
                        </label>

                        {isSelected && config?.totalCount !== undefined && (
                          <span className="tree-count-badge">
                            {config.totalCount.toLocaleString()} emails
                          </span>
                        )}
                      </div>
                      
                      {isSelected && (
                        <div className="tree-node-children">
                          <div className="form-group">
                            <label htmlFor={`email_column_${table}`}>Email Column *</label>
                            <select
                              id={`email_column_${table}`}
                              value={config?.emailColumn || ''}
                              onChange={(e) => handleEmailColumnChange(table, e.target.value)}
                              required
                            >
                              <option value="">-- Select email column --</option>
                              {columns.length > 0 ? (
                                columns.map(column => (
                                  <option key={column} value={column}>{column}</option>
                                ))
                              ) : (
                                <option value={config?.emailColumn || ''}>
                                  {config?.emailColumn || 'Loading...'}
                                </option>
                              )}
                            </select>
                          </div>
                          
                          {preview && (
                            <div className="tree-preview">
                              <div className="preview-info-small">
                                <span><strong>Total Records:</strong> {preview.total_count}</span>
                              </div>
                              {loadingPreviews[table] ? (
                                <div className="loading">Loading preview...</div>
                              ) : (
                                <div className="preview-emails-small">
                                  <strong>Sample emails:</strong>
                                  {preview.preview.slice(0, 3).map((email, index) => (
                                    <div key={index} className="preview-email-item">{email}</div>
                                  ))}
                                  {preview.preview.length > 3 && (
                                    <div className="preview-email-more">...</div>
                                  )}
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
            
            {selectedTables.length > 0 && (
              <div className="tree-summary">
                <span>Selected: <strong>{selectedTables.length}</strong> tables</span>
                <span>Total emails: <strong>{totalEmailCount.toLocaleString()}</strong></span>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default DatabaseSelector;
