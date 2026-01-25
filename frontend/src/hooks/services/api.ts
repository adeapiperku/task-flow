// src/hooks/services/api.ts
import type { Job, Metrics } from '../../types';

const API_BASE_URL = import.meta.env.VITE_API_URL;

const api = {

  async fetchJobs(): Promise<Job[]> {
    const jobsListUrl = `${API_BASE_URL}/jobs`;
    console.log('Fetching jobs list from:', jobsListUrl);
    
    try {
      const response = await fetch(jobsListUrl);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Failed to fetch jobs list:', {
          status: response.status,
          statusText: response.statusText,
          error: errorText
        });
        throw new Error(`Failed to fetch jobs: ${response.status} ${response.statusText}`);
      }
      
      const jobs = await response.json();
      return Array.isArray(jobs) ? jobs : [jobs];
    } catch (error) {
      console.error('Error fetching jobs:', error);
      throw error;
    }
  },

  async fetchJob(jobId: string): Promise<Job> {
    const response = await fetch(`${API_BASE_URL}/jobs/${jobId}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch job ${jobId}`);
    }
    return response.json();
  },

  async fetchJobTimeline(jobId: string): Promise<any[]> {
    const response = await fetch(`${API_BASE_URL}/jobs/${jobId}/timeline`);
    if (!response.ok) {
      throw new Error(`Failed to fetch timeline for job ${jobId}`);
    }
    return response.json();
  },

  async fetchMetrics(timeRange: string): Promise<Metrics> {
    const response = await fetch(`${API_BASE_URL}/metrics?range=${timeRange}`);
    if (!response.ok) {
      throw new Error('Failed to fetch metrics');
    }
    return response.json();
  },
};

export default api;
