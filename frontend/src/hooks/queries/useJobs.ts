import { useQuery } from '@tanstack/react-query';
import type { Job } from '../../types';
import api from '../services/api';

interface JobsQueryParams {
  status?: string;
  state?: string;
  workerId?: string;
  startDate?: string;
  endDate?: string;
  tenant_id?: string;
}

export const useJobs = (params?: JobsQueryParams) => {
  return useQuery<Job[]>({
    queryKey: ['jobs', params],
    queryFn: () => api.fetchJobs(),
    refetchInterval: 10000, // Poll every 10 seconds
  });
};

export const useJob = (jobId: string) => {
  return useQuery<Job>({
    queryKey: ['job', jobId],
    queryFn: () => api.fetchJob(jobId),
    enabled: !!jobId,
  });
};

export const useJobTimeline = (jobId: string) => {
  return useQuery({
    queryKey: ['jobTimeline', jobId],
    queryFn: () => api.fetchJobTimeline(jobId),
    enabled: !!jobId,
  });
};
