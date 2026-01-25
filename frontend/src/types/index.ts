export type JobStatus = 'queued' | 'running' | 'finished' | 'failed';

export interface Job {
  id: string;
  name: string;
  queue: string;
  tenant_id: string;
  state: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'DEAD' | 'RETRY';
  priority: number;
  created_at: string;
  scheduled_at: string;
  started_at?: string;
  completed_at?: string;
  failed_at?: string;
  error?: string;
  result?: any;
  payload?: Record<string, any>;
}

export interface TimelineEvent {
  id: string;
  type: 'job';
  status: JobStatus;
  title: string;
  timestamp: string;
  duration?: number;
  metadata?: Record<string, any>;
}

export interface Metrics {
  workerCount: number;
  activeWorkers: number;
  jobStats: {
    total: number;
    success: number;
    failed: number;
    avgDuration: number;
  };
  uptime: number;
  lastUpdated: string;
}

export type TimeRange = '24h' | '7d' | '30d' | 'custom';

export interface TimeRangeOption {
  value: TimeRange;
  label: string;
  days: number;
}
