import { useState } from 'react';
import { Tabs } from '@mantine/core';
import { JobsList } from '../components/jobs/JobsList';

type TabValue = 'workers' | 'jobs';

export const MonitoringPage = () => {
  const [activeTab, setActiveTab] = useState<TabValue>('workers');

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-6">Monitoring Dashboard</h1>
      
      <Tabs 
        value={activeTab} 
        onChange={(value) => setActiveTab(value as TabValue)}
      >
        <Tabs.List>
          <Tabs.Tab value="jobs">Jobs</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="jobs" pt="md">
          <JobsList />
        </Tabs.Panel>
      </Tabs>
    </div>
  );
};