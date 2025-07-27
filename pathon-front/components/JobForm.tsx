'use client';

import { useState } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

// Get the API URL from environment variables
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export function JobForm() {
  const [jobName, setJobName] = useState('');
  const [modelType, setModelType] = useState('');
  const [trainingSteps, setTrainingSteps] = useState('');
  const [learningRate, setLearningRate] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');

    const payload = {
      jobName,
      modelType,
      trainingSteps: Number(trainingSteps),
      learningRate: Number(learningRate),
      description
    };

    try {
      // Call FastAPI directly
      const res = await fetch(`${API_URL}/jobs`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${res.status}: ${res.statusText}`);
      }

      const result = await res.json();
      console.log('Job created:', result);
      
      setMessage(`Training job "${jobName}" submitted successfully! Job ID: ${result.id}`);
      
      // Clear form
      setJobName('');
      setModelType('');
      setTrainingSteps('');
      setLearningRate('');
      setDescription('');
      
    } catch (err) {
      console.error('Submission error:', err);
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      setMessage(`Submission failed: ${errorMessage}`);
    } finally {
      setLoading(false);
    }
  };


  return (
    <form onSubmit={handleSubmit} className="space-y-6 max-w-xl">
      <div>
        <Label htmlFor="jobName">Job Name</Label>
        <Input id="jobName" value={jobName} onChange={(e) => setJobName(e.target.value)} required />
      </div>

      <div>
        <Label htmlFor="modelType">Model Type</Label>
        <Select value={modelType} onValueChange={setModelType}>
          <SelectTrigger id="modelType">
            <SelectValue placeholder="Select a model" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="ppo">PPO</SelectItem>
            <SelectItem value="sac">SAC</SelectItem>
            <SelectItem value="a2c">A2C</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div>
        <Label htmlFor="trainingSteps">Training Steps</Label>
        <Input id="trainingSteps" type="number" value={trainingSteps} onChange={(e) => setTrainingSteps(e.target.value)} required />
      </div>

      <div>
        <Label htmlFor="learningRate">Learning Rate</Label>
        <Input id="learningRate" type="number" step="0.0001" value={learningRate} onChange={(e) => setLearningRate(e.target.value)} />
      </div>

      <div>
        <Label htmlFor="description">Description</Label>
        <Textarea id="description" value={description} onChange={(e) => setDescription(e.target.value)} />
      </div>

      <Button type="submit" disabled={loading}>
        {loading ? 'Submitting...' : 'Submit Job'}
      </Button>

      {message && <p className="text-sm mt-2">{message}</p>}
    </form>
  );
}