export const getAuthHeaders = (headers = {}) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    return {
      ...headers,
      'Authorization': `Bearer ${token}`
    };
  }
  return headers;
};
