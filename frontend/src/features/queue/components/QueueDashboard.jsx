import React, { useState, useEffect } from 'react';
import TokenGeneration from '../../appointments/components/TokenGeneration';
import QueueList from './QueueList';
import { queueService } from '../services/queueService';

const QueueDashboard = () => {
  const [queue, setQueue] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchQueue = async () => {
    try {
      const data = await queueService.getLiveQueue();
      setQueue(data);
    } catch (error) {
      console.error("Failed to fetch queue", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueue();
    const interval = setInterval(fetchQueue, 10000); // refresh every 10s
    return () => clearInterval(interval);
  }, []);

  if (loading && queue.length === 0) {
    return <div>Loading Queue Data...</div>;
  }

  const waitingQueue = queue.filter(q => q.status === 'Waiting');
  const calledQueue = queue.filter(q => q.status === 'Called');
  const inConsultationQueue = queue.filter(q => q.status === 'In Consultation');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 style={{ fontSize: '1.25rem', color: 'var(--text-main)', margin: 0 }}>Real-time Queue Management</h2>
        <button className="btn btn-secondary" onClick={fetchQueue}>Refresh</button>
      </div>
      
      <TokenGeneration onGenerate={fetchQueue} />
      
      <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap' }}>
        <QueueList 
          title="Waiting Queue" 
          items={waitingQueue} 
          onRefresh={fetchQueue} 
        />
        <QueueList 
          title="Called Queue" 
          items={calledQueue} 
          onRefresh={fetchQueue} 
        />
        <QueueList 
          title="In Consultation" 
          items={inConsultationQueue} 
          onRefresh={fetchQueue} 
        />
      </div>
    </div>
  );
};

export default QueueDashboard;
