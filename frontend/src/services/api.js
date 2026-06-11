import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const queryKnowledgeBase = async (query, topK = 5, filters = null) => {
  try {
    const response = await api.post('/query', {
      query,
      top_k: topK,
      filters,
      min_similarity: 0.0
    });
    return response.data;
  } catch (error) {
    console.error('Error querying knowledge base:', error);
    throw error;
  }
};

export const getDocuments = async (skip = 0, limit = 100) => {
  try {
    const response = await api.get('/documents', {
      params: { skip, limit }
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching documents:', error);
    throw error;
  }
};

export const getStatistics = async () => {
  try {
    const response = await api.get('/statistics');
    return response.data;
  } catch (error) {
    console.error('Error fetching statistics:', error);
    throw error;
  }
};

export const checkHealth = async () => {
  try {
    const response = await api.get('/health');
    return response.data;
  } catch (error) {
    console.error('Error checking health:', error);
    throw error;
  }
};

export default api;

// Made with Bob
