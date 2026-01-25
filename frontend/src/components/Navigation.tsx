// src/components/Navigation.tsx
import { NavLink } from 'react-router-dom';
import { Activity } from 'lucide-react';

export const Navigation = () => {
  return (
    <nav className="bg-gray-900 text-white p-4">
      <div className="container mx-auto flex items-center justify-between">
        <div className="flex items-center space-x-8">
          <NavLink 
            to="/" 
            className="text-xl font-bold flex items-center space-x-2"
          >
            <Activity className="w-6 h-6" />
            <span>TaskFlow</span>
          </NavLink>
          <div className="hidden md:flex space-x-6">
            <NavLink 
              to="/" 
              className={({ isActive }) => 
                `px-3 py-2 rounded-md text-sm font-medium ${
                  isActive ? 'bg-gray-800 text-white' : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                }`
              }
            >
              Monitoring
            </NavLink>
            <NavLink
              to="/analytics"
              className={({ isActive }) =>
                `px-3 py-2 rounded-md text-sm font-medium ${
                  isActive ? 'bg-gray-800 text-white' : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                }`
              }
            >
              Analytics
            </NavLink>
          </div>
        </div>
      </div>
    </nav>
  );
};