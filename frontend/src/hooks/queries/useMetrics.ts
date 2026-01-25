import { useQuery } from '@tanstack/react-query';
import type { Metrics, TimeRange } from '../../types';
import api from '../services/api';

export const useMetrics = (timeRange: TimeRange = '24h') => {
  return useQuery<Metrics>({
    queryKey: ['metrics', timeRange],
    queryFn: () => api.fetchMetrics(timeRange),
    refetchInterval: 60000, // Poll every minute
  });
};