import axios from 'axios';

const SWAYAM_API_BASE_URL =
  (import.meta.env.VITE_SWAYAM_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');

const api = axios.create({
  baseURL: SWAYAM_API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Admin / Batch Management Endpoints
export const addBatchCredential = async (data, token) => {
  const response = await api.post('/api/credentials/batch/add', data, {
    headers: { Authorization: `Bearer ${token}` }
  });
  return response.data;
};

export const uploadBatchCSV = async (batchId, file, token) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post(`/api/credentials/batch/upload-csv?batch_id=${batchId}`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
      Authorization: `Bearer ${token}`
    }
  });
  return response.data;
};

export const commitBatch = async (batchId, token) => {
  const response = await api.post('/api/credentials/batch/commit', { batch_id: batchId }, {
    headers: { Authorization: `Bearer ${token}` }
  });
  return response.data;
};

export const getBatchStatus = async (batchId) => {
  const response = await api.get(`/api/credentials/batch/${batchId}/status`);
  return response.data;
};

// System Health Endpoints
export const checkHealth = async () => {
  const response = await api.get('/health');
  return response.data;
};

export const checkClusterStatus = async () => {
  const response = await api.get('/api/ipfs/cluster/status');
  return response.data;
};

// Student & Verification Endpoints
export const getStudentCredentials = async (studentDid) => {
  const response = await api.get(`/api/credentials/student/${encodeURIComponent(studentDid)}`);
  return response.data;
};

export const getStudentQRCodes = async (studentDid) => {
  const response = await api.get(`/api/credentials/student/${encodeURIComponent(studentDid)}/qrs`);
  return response.data;
};

export const verifyCredential = async (data) => {
  const response = await api.post('/api/credentials/verify-with-proof', data);
  return response.data;
};

export const getShareLink = async (batchId, leafIndex) => {
  const response = await api.get(`/api/credentials/${batchId}/${leafIndex}/share-link`);
  return response.data;
};

// IPFS Data
export const getIPFSData = async (cid) => {
  const response = await api.get(`/api/ipfs/${cid}`);
  return response.data;
};

// Admin Revoke
export const revokeCredential = async (data, token) => {
  const response = await api.post('/api/credentials/revoke', data, {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
  return response.data;
};

export default api;
