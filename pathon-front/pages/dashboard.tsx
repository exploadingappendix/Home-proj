import { useState, useEffect } from 'react';
import { RefreshCw } from 'lucide-react';
import Navbar from "@/components/navbar";
import JobTable from "../components/JobTable";

interface Job {
  id: string;
  name: string;
  description: string;
  status: 'queued' | 'training' | 'completed' | 'failed';
  created_at: string;
  model_type: string;
  training_steps: number;
  learning_rate: number;
}

export default function DashboardPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchJobs = async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    try {
      const response = await fetch('/api/jobs');
      if (response.ok) {
        const data = await response.json();
        setJobs(data);
      } else {
        console.error('Failed to fetch jobs:', response.statusText);
      }
    } catch (error) {
      console.error('Failed to fetch jobs:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, []);

  const handleRefresh = () => {
    fetchJobs(true);
  };

  return (
    <main className="p-6">
      <Navbar />
      
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-white">Job Dashboard</h1>
          <p className="text-gray-400 mt-1">Monitor your training jobs in real-time</p>
        </div>
        <button 
          onClick={handleRefresh}
          disabled={refreshing}
          type="button"
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="w-8 h-8 animate-spin text-blue-500" />
          <span className="ml-2 text-lg text-gray-600">Loading jobs...</span>
        </div>
      ) : (
        <JobTable jobs={jobs} />
      )}
    </main>
  );
}