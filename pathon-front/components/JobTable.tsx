import { Clock, RefreshCw, CheckCircle, XCircle, AlertCircle } from 'lucide-react';

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

interface JobTableProps {
  jobs: Job[];
}

export default function JobTable({ jobs }: JobTableProps) {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'queued':
        return <Clock className="w-4 h-4 text-yellow-600" />;
      case 'training':
        return <RefreshCw className="w-4 h-4 animate-spin text-blue-600" />;
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-600" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-600" />;
      default:
        return <AlertCircle className="w-4 h-4 text-gray-600" />;
    }
  };

  const getStatusBadge = (status: string) => {
    const variants = {
      queued: 'bg-yellow-100 text-yellow-800 border-yellow-300',
      training: 'bg-blue-100 text-blue-800 border-blue-300',
      completed: 'bg-green-100 text-green-800 border-green-300',
      failed: 'bg-red-100 text-red-800 border-red-300'
    };
    
    return (
      <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium border ${variants[status as keyof typeof variants]}`}>
        {getStatusIcon(status)}
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    );
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (jobs.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-sm border p-8 text-center">
        <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">No training jobs found</h3>
        <p className="text-gray-600">Create your first training job to get started.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {jobs.map((job) => (
        <div key={job.id} className="bg-white rounded-lg shadow-sm border hover:shadow-md transition-shadow">
          <div className="p-6">
            {/* Header */}
            <div className="flex items-start justify-between mb-4">
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-gray-900 mb-1">
                  {job.name}
                </h3>
                <div className="flex items-center gap-4 text-sm text-gray-600">
                  <span>
                    <span className="font-medium">Model:</span> {job.model_type.toUpperCase()}
                  </span>
                  <span>
                    <span className="font-medium">Steps:</span> {job.training_steps.toLocaleString()}
                  </span>
                  <span>
                    <span className="font-medium">Learning Rate:</span> {job.learning_rate}
                  </span>
                </div>
              </div>
              <div className="flex-shrink-0 ml-4">
                {getStatusBadge(job.status)}
              </div>
            </div>

            {/* Description */}
            {job.description && (
              <div className="mb-4">
                <p className="text-gray-700 text-sm leading-relaxed">
                  {job.description}
                </p>
              </div>
            )}

            {/* Footer */}
            <div className="flex items-center justify-between text-sm text-gray-500 pt-3 border-t border-gray-100">
              <span>
                Created: {formatDate(job.created_at)}
              </span>
              <span className="text-xs text-gray-400">
                ID: {job.id.slice(0, 8)}...
              </span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}