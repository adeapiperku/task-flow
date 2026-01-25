import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

export interface Tenant {
  id: string;
  name: string;
  max_running_jobs: number;
  active: boolean;
  created_at: string;
  updated_at: string;
}

export const fetchTenants = async (): Promise<Tenant[]> => {
  const response = await axios.get(`${API_BASE_URL}/tenants`);
  return response.data;
};

export const fetchTenantById = async (id: string): Promise<Tenant> => {
  const response = await axios.get(`${API_BASE_URL}/tenants/${id}/`);
  return response.data;
};
