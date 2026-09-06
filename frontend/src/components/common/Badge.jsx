import React from 'react';
import PropTypes from 'prop-types';

const Badge = ({ text, variant = 'default', className = '' }) => {
  return (
    <span className={`badge badge-${variant} ${className}`}>
      {text}
    </span>
  );
};

Badge.propTypes = {
  text: PropTypes.string.isRequired,
  variant: PropTypes.oneOf(['success', 'warning', 'danger', 'default']),
  className: PropTypes.string,
};

export default Badge;
