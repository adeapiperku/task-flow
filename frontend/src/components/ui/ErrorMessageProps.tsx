import { AlertCircle } from 'lucide-react';

interface ErrorMessageProps {
  message: string;
  className?: string;
}

export const ErrorMessage = ({ message, className = '' }: ErrorMessageProps) => (
  <div className={`flex items-center gap-2 p-4 text-red-600 bg-red-50 rounded-md ${className}`}>
    <AlertCircle className="flex-shrink-0" />
    <span>{message}</span>
  </div>
);