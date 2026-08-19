import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Shield, Mail, Lock, UserCheck } from 'lucide-react';
import axios from 'axios';

export default function AuthModal() {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('Store Manager');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const { login } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (isRegister) {
        await axios.post('http://127.0.0.1:8000/api/auth/register', {
          email,
          password,
          role
        });
        await login(email, password);
      } else {
        await login(email, password);
      }
    } catch (err) {
      // Direct catch fallback to prevent [object Object]
      let msg = err.message || 'An unexpected error occurred.';
      if (typeof err === 'string') msg = err;
      setError(String(msg));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md overflow-hidden shadow-2xl">
        <div className="bg-slate-800/80 p-6 text-center border-b border-slate-700/60">
          <div className="inline-flex p-3 bg-blue-600/20 border border-blue-500/30 rounded-xl text-blue-400 mb-2">
            <Shield className="w-8 h-8" />
          </div>
          <h2 className="text-xl font-bold text-white">Consumer Attention Mapping</h2>
          <p className="text-xs text-slate-400 mt-1">Enterprise Analytics Portal</p>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-rose-500/10 border-l-4 border-rose-500 text-rose-300 text-xs rounded break-words">
              {String(error)}
            </div>
          )}

          <div>
            <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">
              Email Address
            </label>
            <div className="relative">
              <Mail className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="analyst@retail.com"
                className="w-full bg-slate-800 border border-slate-700 rounded-xl pl-9 pr-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">
              Password
            </label>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full bg-slate-800 border border-slate-700 rounded-xl pl-9 pr-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
              />
            </div>
          </div>

          {isRegister && (
            <div>
              <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">
                Assigned Role
              </label>
              <div className="relative">
                <UserCheck className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl pl-9 pr-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500 cursor-pointer"
                >
                  <option value="Store Manager">Store Manager</option>
                  <option value="Retail Analyst">Retail Analyst</option>
                  <option value="Marketing Manager">Marketing Manager</option>
                </select>
              </div>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs py-2.5 rounded-xl transition-all shadow-lg shadow-blue-600/20 disabled:opacity-50 cursor-pointer"
          >
            {loading ? 'Processing...' : isRegister ? 'Register Account' : 'Sign In to Portal'}
          </button>

          <div className="text-center pt-2">
            <button
              type="button"
              onClick={() => {
                setIsRegister(!isRegister);
                setError('');
              }}
              className="text-xs text-blue-400 hover:underline cursor-pointer"
            >
              {isRegister ? 'Already have an account? Sign in' : 'Need an account? Register here'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}