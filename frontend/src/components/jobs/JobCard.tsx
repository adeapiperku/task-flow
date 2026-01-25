// src/components/jobs/JobCard.tsx
import { useMemo } from 'react';
import { Clock, AlertCircle, CheckCircle2, Loader2, Timer } from 'lucide-react';
import type { Job } from '../../types';
import { format } from 'date-fns';

const statusIcons = {
  PENDING: <Loader2 className="text-blue-500 animate-spin" />,
  RUNNING: <Loader2 className="text-green-500 animate-spin" />,
  COMPLETED: <CheckCircle2 className="text-green-500" />,
  FAILED: <AlertCircle className="text-red-500" />,
  DEAD: <AlertCircle className="text-red-700" />,
  RETRY: <Loader2 className="text-yellow-500 animate-spin" />,
};

const statusColors = {
  PENDING: 'bg-blue-100 text-blue-800',
  RUNNING: 'bg-green-100 text-green-800',
  COMPLETED: 'bg-green-100 text-green-800',
  FAILED: 'bg-red-100 text-red-800',
  DEAD: 'bg-red-200 text-red-900',
  RETRY: 'bg-yellow-100 text-yellow-800',
};

interface JobCardProps {
  job: Job;
  onClick?: () => void;
}

export const JobCard = ({ job, onClick }: JobCardProps) => {
  const formattedCreatedAt = useMemo(
    () => format(new Date(job.created_at), 'MMM d, yyyy HH:mm:ss'),
    [job.created_at]
  );

  const formattedScheduledAt = useMemo(
    () => (job.scheduled_at ? format(new Date(job.scheduled_at), 'MMM d, yyyy HH:mm:ss') : 'N/A'),
    [job.scheduled_at]
  );

  const duration = useMemo(() => {
    if (job.started_at && job.completed_at) {
      const start = new Date(job.started_at).getTime();
      const end = new Date(job.completed_at).getTime();
      return ((end - start) / 1000).toFixed(2) + 's';
    }
    return null;
  }, [job.started_at, job.completed_at]);

  return (
    <div 
      onClick={onClick}
      className="p-4 border rounded-lg shadow-sm hover:shadow-md transition-shadow cursor-pointer bg-white"
    >
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-medium text-lg">{job.name}</h3>
        <div className={`px-2 py-1 rounded-full text-xs font-medium ${statusColors[job.state]}`}>
          {job.state}
        </div>
      </div>
      
      <div className="mt-3 space-y-2 text-sm text-gray-600">
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-gray-400 flex-shrink-0" />
          <span>Created: {formattedCreatedAt}</span>
        </div>
        
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-gray-400 flex-shrink-0" />
          <span>Scheduled: {formattedScheduledAt}</span>
        </div>
        
        {duration && (
          <div className="flex items-center gap-2">
            <Timer className="w-4 h-4 text-gray-400 flex-shrink-0" />
            <span>Duration: {duration}</span>
          </div>
        )}
        
        <div className="text-sm text-gray-500">
          Queue: <span className="font-mono text-xs bg-gray-100 px-2 py-0.5 rounded">{job.queue}</span>
        </div>
        
        {job.error && (
          <div className="mt-2 text-sm text-red-600 bg-red-50 p-2 rounded">
            <div className="font-medium">Error:</div>
            <div className="font-mono text-xs">{job.error}</div>
          </div>
        )}
      </div>
    </div>
  );
};