import React from 'react';
import PropTypes from 'prop-types';

const Loading = ({ text = 'Loading...' }) => {
  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
      <span>{text}</span>
    </div>
  );
};

Loading.propTypes = {
  text: PropTypes.string,
};

export default Loading;
