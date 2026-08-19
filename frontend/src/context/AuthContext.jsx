import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const savedUser = localStorage.getItem('user');
    if (savedUser) {
      try {
        setUser(JSON.parse(savedUser));
      } catch (e) {
        localStorage.removeItem('user');
      }
    }
    setLoading(false);
  }, []);

  const login = async (email, password) => {
    try {
      const response = await axios.post('http://127.0.0.1:8000/api/auth/login', {
        email: email,
        password: password
      });

      const userData = {
        email: response.data.email || email,
        role: response.data.role || 'Store Manager',
        token: response.data.access_token || response.data.token
      };

      setUser(userData);
      localStorage.setItem('user', JSON.stringify(userData));
      return userData;
    } catch (err) {
      let errorMessage = 'Login failed. Please check your credentials.';

      if (err.response?.data) {
        const detail = err.response.data.detail;
        if (typeof detail === 'string') {
          errorMessage = detail;
        } else if (Array.isArray(detail)) {
          errorMessage = detail.map(d => d.msg || JSON.stringify(d)).join(', ');
        } else if (typeof detail === 'object' && detail !== null) {
          errorMessage = detail.msg || detail.message || JSON.stringify(detail);
        } else if (err.response.data.message) {
          errorMessage = String(err.response.data.message);
        }
      } else if (err.message) {
        errorMessage = err.message;
      }

      throw new Error(errorMessage);
    }
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem('user');
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading }}>
      {!loading && children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);