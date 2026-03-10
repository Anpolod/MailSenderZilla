import axios from 'axios';

// In development, use /api which is proxied to http://localhost:5000/api by Vite
// In production, use the full URL
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Campaign API
export const getCampaigns = async () => {
  const response = await api.get('/campaigns');
  return response.data;
};

export const getCampaign = async (id) => {
  const response = await api.get(`/campaigns/${id}`);
  return response.data;
};

export const createCampaign = async (campaignData) => {
  const response = await api.post('/campaigns', campaignData);
  return response.data;
};

export const getCampaignLogs = async (id) => {
  const response = await api.get(`/campaigns/${id}/logs`);
  return response.data;
};

export const restartCampaign = async (id) => {
  const response = await api.post(`/campaigns/${id}/restart`);
  return response.data;
};

export const deleteCampaign = async (id) => {
  const response = await api.delete(`/campaigns/${id}`);
  return response.data;
};

export const startCampaign = async (id, providerConfig = null, htmlBody = null, vacanciesText = null) => {
  const response = await api.post(`/campaigns/${id}/start`, {
    provider_config: providerConfig,
    html_body: htmlBody,
    vacancies_text: vacanciesText
  });
  return response.data;
};

export const pauseCampaign = async (id) => {
  const response = await api.post(`/campaigns/${id}/pause`);
  return response.data;
};

export const resumeCampaign = async (id, providerConfig = null) => {
  const response = await api.post(`/campaigns/${id}/resume`, {
    provider_config: providerConfig
  });
  return response.data;
};

export const cloneCampaign = async (id, newName = null) => {
  const response = await api.post(`/campaigns/${id}/clone`, {
    name: newName
  });
  return response.data;
};

// Upload API
export const uploadCSV = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await api.post('/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

// Settings API
export const getSettings = async () => {
  const response = await api.get('/settings');
  return response.data;
};

export const updateSettings = async (settings) => {
  const response = await api.put('/settings', settings);
  return response.data;
};

// Blacklist API
export const getBlacklist = async () => {
  const response = await api.get('/blacklist');
  return response.data;
};

export const addToBlacklist = async (email, reason = 'manual') => {
  const response = await api.post('/blacklist', { email, reason });
  return response.data;
};

// Database API
export const getDatabaseTables = async () => {
  const response = await api.get('/database/tables');
  return response.data;
};

export const getTableColumns = async (tableName) => {
  const response = await api.get(`/database/tables/${encodeURIComponent(tableName)}/columns`);
  return response.data;
};

export const previewTable = async (tableName, emailColumn, limit = 10) => {
  const params = new URLSearchParams();
  if (emailColumn) params.append('email_column', emailColumn);
  params.append('limit', limit.toString());
  const response = await api.get(`/database/tables/${encodeURIComponent(tableName)}/preview?${params}`);
  return response.data;
};


// Preview API
export const previewEmail = async (vacanciesText, subject, htmlBody = null) => {
  const response = await api.post('/preview/email', {
    vacancies_text: vacanciesText,
    subject: subject,
    html_body: htmlBody
  });
  return response.data;
};

// Export API
export const exportCampaignLogs = async (campaignId) => {
  const response = await api.get(`/campaigns/${campaignId}/export/logs`, {
    responseType: 'blob'
  });
  return response.data;
};

export const exportCampaignSent = async (campaignId) => {
  const response = await api.get(`/campaigns/${campaignId}/export/sent`, {
    responseType: 'blob'
  });
  return response.data;
};

export const exportCampaignFailed = async (campaignId) => {
  const response = await api.get(`/campaigns/${campaignId}/export/failed`, {
    responseType: 'blob'
  });
  return response.data;
};

export const exportCampaignAll = async (campaignId) => {
  const response = await api.get(`/campaigns/${campaignId}/export/all`, {
    responseType: 'blob'
  });
  return response.data;
};

export const exportCampaignStatistics = async (campaignId) => {
  const response = await api.get(`/campaigns/${campaignId}/export/statistics`, {
    responseType: 'blob'
  });
  return response.data;
};

// Templates API
export const getTemplates = async () => {
  const response = await api.get('/templates');
  return response.data;
};

export const getTemplate = async (id) => {
  const response = await api.get(`/templates/${id}`);
  return response.data;
};

export const createTemplate = async (templateData) => {
  const response = await api.post('/templates', templateData);
  return response.data;
};

export const updateTemplate = async (id, templateData) => {
  const response = await api.put(`/templates/${id}`, templateData);
  return response.data;
};

export const deleteTemplate = async (id) => {
  const response = await api.delete(`/templates/${id}`);
  return response.data;
};

// Backup API
export const createBackup = async () => {
  const response = await api.post('/backup');
  return response.data;
};

export const listBackups = async () => {
  const response = await api.get('/backup');
  return response.data;
};

export const restoreBackup = async (backupPath) => {
  const response = await api.post('/backup/restore', { path: backupPath });
  return response.data;
};

export const deleteBackup = async (backupPath) => {
  const response = await api.delete(`/backup/${encodeURIComponent(backupPath)}`);
  return response.data;
};

export default api;
