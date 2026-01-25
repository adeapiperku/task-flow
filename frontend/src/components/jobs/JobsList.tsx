import { useState, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Select, TextInput, Button, Group, Stack, Title, Text, Paper } from '@mantine/core';
import { useDebouncedValue } from '@mantine/hooks';
import { Search, Filter, RefreshCw } from 'lucide-react';
import { useJobs } from '../../hooks/queries/useJobs';
import { LoadingSpinner } from '../ui/LoadingSpinnerProps';
import { ErrorMessage } from '../ui/ErrorMessageProps';
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

const sortOptions = [
  { value: 'created_at:desc', label: 'Newest First' },
  { value: 'created_at:asc', label: 'Oldest First' },
  { value: 'name:asc', label: 'Name (A-Z)' },
  { value: 'name:desc', label: 'Name (Z-A)' },
];

export const JobsList = () => {
  const [searchParams] = useSearchParams();
  const [search, setSearch] = useState('');
  const [debouncedSearch] = useDebouncedValue(search, 300);
  const [stateFilter, setStateFilter] = useState('');
  const [sortBy, setSortBy] = useState('created_at:desc');

  const { 
    data: jobs = [], 
    isLoading, 
    error, 
    refetch, 
    isRefetching 
  } = useJobs({
    status: stateFilter || undefined,
    tenant_id: searchParams.get('tenant_id') || undefined,
  });

  const filteredJobs = useMemo(() => {
    if (!jobs) return [];
    
    let result = [...jobs];
    
    if (debouncedSearch) {
      const searchLower = debouncedSearch.toLowerCase();
      result = result.filter(
        job => 
          job.name?.toLowerCase().includes(searchLower) ||
          job.id.toLowerCase().includes(searchLower) ||
          job.queue?.toLowerCase().includes(searchLower)
      );
    }
    
    const [sortField, sortOrder] = sortBy.split(':');
    result.sort((a, b) => {
      let aValue = a[sortField as keyof typeof a];
      let bValue = b[sortField as keyof typeof b];
      
      if (sortField.includes('_at') && aValue && bValue) {
        aValue = new Date(aValue as string).getTime();
        bValue = new Date(bValue as string).getTime();
      }
      
      if (typeof aValue === 'string' && typeof bValue === 'string') {
        return sortOrder === 'asc' 
          ? aValue.localeCompare(bValue)
          : bValue.localeCompare(aValue);
      }
      
      return sortOrder === 'asc' 
        ? (aValue as number) - (bValue as number)
        : (bValue as number) - (aValue as number);
    });
    
    return result;
  }, [jobs, debouncedSearch, sortBy]);

  const handleRefresh = () => {
    refetch();
  };

  if (isLoading && !isRefetching) {
    return (
      <div className="flex items-center justify-center py-16">
        <LoadingSpinner size={24} />
      </div>
    );
  }

  if (error) {
    return (
      <ErrorMessage 
        message={`Failed to load jobs: ${error instanceof Error ? error.message : String(error)}`}
        className="my-8"
      />
    );
  }

  return (
    <Stack gap="lg">
      <Paper withBorder p="md" radius="md">
        <Group justify="space-between" mb="md">
          <div>
            <Title order={3} fw={600}>Job Queue</Title>
            <Text c="dimmed" size="sm" mt={4}>
              {filteredJobs.length} {filteredJobs.length === 1 ? 'job' : 'jobs'} found
            </Text>
          </div>
          <Button
            variant="outline"
            leftSection={<RefreshCw size={16} />}
            loading={isRefetching}
            onClick={handleRefresh}
          >
            Refresh
          </Button>
        </Group>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <TextInput
            placeholder="Search jobs..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            leftSection={<Search size={16} />}
            className="md:col-span-2"
          />
          <Select
            placeholder="Filter by state"
            data={stateOptions}
            value={stateFilter}
            onChange={(value) => setStateFilter(value || '')}
            leftSection={<Filter size={16} />}
          />
          <Select
            placeholder="Sort by"
            data={sortOptions}
            value={sortBy}
            onChange={(value) => setSortBy(value || 'created_at:desc')}
          />
        </div>

        {filteredJobs.length === 0 ? (
          <div className="text-center py-12">
            <Text c="dimmed" mb="sm">
              {search || stateFilter 
                ? 'No jobs match your search criteria'
                : 'No jobs found'}
            </Text>
            {(search || stateFilter) && (
              <Button
                variant="subtle"
                size="sm"
                onClick={() => {
                  setSearch('');
                  setStateFilter('');
                }}
              >
                Clear filters
              </Button>
            )}
          </div>
        ) : (
          <Stack gap="sm">
            {filteredJobs.map((job) => (
              <JobCard 
                key={job.id}
                job={job}
                onClick={() => {
                  console.log('Job clicked:', job.id);
                }}
              />
            ))}
          </Stack>
        )}
      </Paper>
    </Stack>
  );
};