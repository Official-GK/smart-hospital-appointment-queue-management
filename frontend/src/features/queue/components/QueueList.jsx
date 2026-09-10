import React from 'react';
import QueueItem from './QueueItem';

const QueueList = ({ title, items, onRefresh }) => {
  return (
    <div className="card" style={{ flex: 1, minWidth: '300px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h3 className="card-title" style={{ margin: 0 }}>{title}</h3>
        <span className="badge badge-default">{items.length}</span>
      </div>
      <div style={{ maxHeight: '500px', overflowY: 'auto', paddingRight: '0.5rem' }}>
        {items.length === 0 ? (
          <p className="placeholder-text">No patients in this queue.</p>
        ) : (
          items.map(item => (
            <QueueItem key={item.token_id} item={item} onRefresh={onRefresh} />
          ))
        )}
      </div>
    </div>
  );
};

export default QueueList;
