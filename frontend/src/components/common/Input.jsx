import React from 'react';
import PropTypes from 'prop-types';

const Input = ({ label, type = 'text', placeholder, value, onChange, name, className = '', ...rest }) => {
  return (
    <div className={`input-group ${className}`}>
      {label && <label className="input-label" htmlFor={name}>{label}</label>}
      <input
        id={name}
        name={name}
        type={type}
        className="input-field"
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        {...rest}
      />
    </div>
  );
};

Input.propTypes = {
  label: PropTypes.string,
  type: PropTypes.string,
  placeholder: PropTypes.string,
  value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  onChange: PropTypes.func,
  name: PropTypes.string,
  className: PropTypes.string,
};

export default Input;
