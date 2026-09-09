import React from 'react';
import PropTypes from 'prop-types';
import Button from './Button';

const Modal = ({ isOpen, title, onClose, children, footer, maxWidth = '560px', className = '' }) => {
  if (!isOpen) return null;

  return (
    <div 
      className={`modal-backdrop ${className}`}
      style={{
        position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
        backgroundColor: 'rgba(15, 23, 42, 0.55)', backdropFilter: 'blur(4px)', display: 'flex',
        alignItems: 'center', justifyContent: 'center', zIndex: 100, padding: '1rem'
      }}
    >
      <div 
        className="modal-box"
        style={{
          backgroundColor: '#fff', borderRadius: '0.625rem', width: '100%',
          maxWidth: maxWidth, padding: '1.5rem', boxShadow: '0 20px 25px -5px rgba(0,0,0,0.15)',
          maxHeight: '90vh', display: 'flex', flexDirection: 'column'
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', paddingBottom: '0.75rem', borderBottom: '1px solid #e2e8f0' }}>
          <h2 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 700, color: '#0f172a' }}>{title}</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: '1.5rem', cursor: 'pointer', color: '#64748b', lineHeight: 1 }}>&times;</button>
        </div>
        <div style={{ marginBottom: '1.25rem', overflowY: 'auto', flex: 1, paddingRight: '0.25rem' }}>
          {children}
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', paddingTop: '0.75rem', borderTop: '1px solid #e2e8f0' }}>
          {footer !== undefined ? footer : <Button variant="secondary" onClick={onClose}>Close</Button>}
        </div>
      </div>
    </div>
  );
};

Modal.propTypes = {
  isOpen: PropTypes.bool.isRequired,
  title: PropTypes.string.isRequired,
  onClose: PropTypes.func.isRequired,
  children: PropTypes.node.isRequired,
  footer: PropTypes.node,
  maxWidth: PropTypes.string,
  className: PropTypes.string,
};

export default Modal;
