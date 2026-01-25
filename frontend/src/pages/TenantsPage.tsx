import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { fetchTenants, fetchTenantById } from '../api/tenants';
import type { Tenant } from '../api/tenants';

const TenantList: React.FC<{ tenants: Tenant[]; onSelect: (id: string) => void }> = ({ tenants, onSelect }) => (
  <div className="w-1/3 pr-4 border-r">
    <h2 className="text-xl font-bold mb-4">Tenants</h2>
    <div className="space-y-2">
      {tenants.map((tenant) => (
        <div 
          key={tenant.id}
          onClick={() => onSelect(tenant.id)}
          className="p-3 border rounded hover:bg-gray-50 cursor-pointer"
        >
          <h3 className="font-medium">{tenant.name}</h3>
          <p className="text-sm text-gray-500">ID: {tenant.id}</p>
          <span className={`inline-block px-2 py-1 text-xs rounded-full ${
            tenant.active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
          }`}>
            {tenant.active ? 'Active' : 'Inactive'}
          </span>
        </div>
      ))}
    </div>
  </div>
);

const TenantDetails: React.FC<{ tenant: Tenant | null }> = ({ tenant }) => {
  if (!tenant) {
    return (
      <div className="flex-1 flex items-center justify-center text-gray-500">
        Select a tenant to view details
      </div>
    );
  }

  return (
    <div className="flex-1 pl-6">
      <h2 className="text-2xl font-bold mb-6">{tenant.name}</h2>
      <div className="space-y-4">
        <div>
          <h3 className="text-sm font-medium text-gray-500">Tenant ID</h3>
          <p className="mt-1">{tenant.id}</p>
        </div>
        <div>
          <h3 className="text-sm font-medium text-gray-500">Status</h3>
          <span className={`inline-block px-2 py-1 text-xs rounded-full ${
            tenant.active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
          }`}>
            {tenant.active ? 'Active' : 'Inactive'}
          </span>
        </div>
        <div>
          <h3 className="text-sm font-medium text-gray-500">Max Running Jobs</h3>
          <p>{tenant.max_running_jobs}</p>
        </div>
        <div>
          <h3 className="text-sm font-medium text-gray-500">Created At</h3>
          <p>{new Date(tenant.created_at).toLocaleString()}</p>
        </div>
        <div>
          <h3 className="text-sm font-medium text-gray-500">Last Updated</h3>
          <p>{new Date(tenant.updated_at).toLocaleString()}</p>
        </div>
      </div>
    </div>
  );
};

const TenantsPage: React.FC = () => {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [selectedTenant, setSelectedTenant] = useState<Tenant | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { id } = useParams<{ id?: string }>();

  useEffect(() => {
    const loadTenants = async () => {
      try {
        setLoading(true);
        const data = await fetchTenants();
        setTenants(data);
        
        // If there's an ID in the URL, load that tenant
        if (id) {
          const tenant = await fetchTenantById(id);
          setSelectedTenant(tenant);
        } else if (data.length > 0) {
          // Otherwise select the first tenant by default
          setSelectedTenant(data[0]);
        }
      } catch (err) {
        console.error('Error loading tenants:', err);
        setError('Failed to load tenants. Please try again later.');
      } finally {
        setLoading(false);
      }
    };

    loadTenants();
  }, [id]);

  const handleSelectTenant = (tenantId: string) => {
    const tenant = tenants.find(t => t.id === tenantId) || null;
    setSelectedTenant(tenant);
    // Update URL without page reload
    window.history.pushState({}, '', `/tenants/${tenantId}`);
  };

  if (loading) {
    return <div className="p-8">Loading tenants...</div>;
  }

  if (error) {
    return <div className="p-8 text-red-600">{error}</div>;
  }

  return (
    <div className="p-8">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">Tenant Management</h1>
        
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex">
            <TenantList 
              tenants={tenants} 
              onSelect={handleSelectTenant} 
            />
            <TenantDetails tenant={selectedTenant} />
          </div>
        </div>
      </div>
    </div>
  );
};

export default TenantsPage;
