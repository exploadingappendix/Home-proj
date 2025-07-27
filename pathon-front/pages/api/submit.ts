import { NextApiRequest, NextApiResponse } from 'next';
import { createClient } from '@supabase/supabase-js';
import { v4 as uuidv4 } from 'uuid';
import { SQSClient, SendMessageCommand } from '@aws-sdk/client-sqs';
import { fromEnv } from '@aws-sdk/credential-provider-env';


const supabase = createClient(
  process.env.SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_KEY!
);

const sqsClient = new SQSClient({
  region: process.env.AWS_REGION!,
  credentials: fromEnv(),
});

const queueUrl = process.env.SQS_QUEUE_URL!;

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { jobName, modelType, trainingSteps, learningRate, description } = req.body;

  if (!jobName || !modelType || !trainingSteps) {
    return res.status(400).json({ error: 'Missing required fields' });
  }

  const jobId = uuidv4();

  // 1. Insert job into Supabase
  const { error } = await supabase.from('jobs').insert([
    {
      id: jobId,
      name: jobName,
      model_type: modelType,
      training_steps: trainingSteps,
      learning_rate: learningRate,
      description,
      status: 'queued',
    }
  ]);

  if (error) {
    console.error('Supabase insert error:', error);
    return res.status(500).json({ error: 'Failed to submit job' });
  }

  // 2. Send message to SQS
  const payload = {
    jobId,
    jobName,
    modelType,
    trainingSteps,
    learningRate,
    description,
  };

  const params = new SendMessageCommand({
    MessageBody: JSON.stringify(payload),
    QueueUrl: queueUrl,
  });

   try {
    await sqsClient.send(params);
    return res.status(200).json({ message: 'Job submitted to queue successfully', jobId });
  } catch (err) {
    console.error('Failed to send message to SQS:', err);
    return res.status(500).json({ error: 'Failed to queue job' });
  }
}