import React, { createContext, useContext, useState } from 'react';
import axios from 'axios';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);

  const login = async (email, password) => {
    try {
      const response = await axios.post('http://127.0.0.1:8000/api/auth/login', {
        email,
        password,
      });

      setUser(response.data.user);
      return response.data.user;
    } catch (err) {
      // Extract FastAPI detail arrays gracefully
      const detail = err.response?.data?.detail;
      let errorMsg = 'Authentication failed';

      if (Array.isArray(detail)) {
        errorMsg = detail.map((e) => `${e.loc[1]}: ${e.msg}`).join(', ');
      } else if (typeof detail === 'string') {
        errorMsg = detail;
      } else if (err.message) {
        errorMsg = err.message;
      }

      throw new Error(errorMsg);
    }
  };

  const logout = () => setUser(null);

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);