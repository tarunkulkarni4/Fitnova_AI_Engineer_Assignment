import React from 'react';
import { Loader2 } from 'lucide-react';

export default function PageLoader() {
  return (
    <div className="flex items-center justify-center min-h-[50vh]">
      <div className="flex flex-col items-center text-gray-500 dark:text-gray-400">
        <Loader2 className="h-8 w-8 animate-spin mb-4 text-indigo-500" />
        <p className="text-sm font-medium">Loading page...</p>
      </div>
    </div>
  );
}
