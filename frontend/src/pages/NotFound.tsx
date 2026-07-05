import React from 'react';
import { Link } from 'react-router-dom';
import { FileQuestion, ArrowLeft } from 'lucide-react';

export default function NotFound() {
  return (
    <div className="min-h-screen bg-neutral-50 flex items-center justify-center p-6">
      <div className="max-w-md w-full bg-white rounded-lg border border-neutral-200 p-8 shadow-sm text-center">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-neutral-100 text-neutral-500 mb-4">
          <FileQuestion className="w-6 h-6" />
        </div>
        <h1 className="text-xl font-semibold text-neutral-900 mb-2">Page not found</h1>
        <p className="text-sm text-neutral-500 mb-6">
          The page you are looking for does not exist or has been moved.
        </p>
        <Link
          to="/"
          className="inline-flex items-center justify-center px-4 py-2 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 rounded-md shadow-sm transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-500 w-full"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Overview
        </Link>
      </div>
    </div>
  );
}
