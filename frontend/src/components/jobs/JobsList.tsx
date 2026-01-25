// src/components/jobs/JobsList.tsx
import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Select, TextInput } from '@mantine/core';
import { useJobs } from '../../hooks/queries/useJobs';
import { LoadingSpinner } from '../ui/LoadingSpinner';
import { ErrorMessage } from '../ui/ErrorMessage';
import { JobCard } from './JobCard';

const stateOptions = [
  { value: '', label: 'All States' },
  { value: 'PENDING', label: 'Pending' },
  { value: 'RUNNING', label: 'Running' },
  { value: 'COMPLETED', label: 'Completed' },
  { value: 'FAILED', label: 'Failed' },
  { value: 'DEAD', label: 'Dead' },
  { value: 'RETRY', label: 'Retry' },
];

export const JobsList = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [search, setSearch] = useState('');
  const [stateFilter, setStateFilter] = useState('');

  const { data: jobs, isLoading, error } = useJobs({
    status: stateFilter || undefined,
    tenant_id: searchParams.get('tenant_id') || undefined,
  });

  const filteredJobs = jobs?.filter(job => 
    job.name?.toLowerCase().includes(search.toLowerCase()) ||
    job.id.toLowerCase().includes(search.toLowerCase())
  );

  if (isLoading) {
    return <LoadingSpinner className="my-8" />;
  }

  if (error) {
    return (
      <ErrorMessage 
        message={`Failed to load jobs: ${error.message}`} 
        className="my-4" 
      />
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row gap-4 mb-6">
        <TextInput
          placeholder="Search jobs..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1"
        />
        <Select
          placeholder="Filter by state"
          data={stateOptions}
          value={stateFilter}
          onChange={(value) => setStateFilter(value || '')}
          className="w-full sm:w-48"
        />
      </div>

      {filteredJobs?.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          No jobs found
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {filteredJobs?.map((job) => (
            <JobCard 
              key={job.id}
              job={job}
              onClick={() => {
                console.log('Job clicked:', job.id);
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
};