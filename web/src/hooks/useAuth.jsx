import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import {
  getToken, getUser, setUser, clearAuth,
  login as apiLogin, verifyOtp as apiVerifyOtp, logout as apiLogout,
} from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUserState] = useState(getUser);
  const [token, setTokenState] = useState(getToken);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const storedToken = getToken();
    const storedUser = getUser();
    if (storedToken && storedUser) {
      setTokenState(storedToken);
      setUserState(storedUser);
    }
    setLoading(false);
  }, []);

  const login = useCallback(async (username, password) => {
    const data = await apiLogin(username, password);
    // login now returns {status: "otp_required", user_id, role} —
    // NO token is stored here. OTP verification must follow.
    return data;
  }, []);

  const verifyOtp = useCallback(async (userId, otp) => {
    const data = await apiVerifyOtp(userId, otp);
    // verify-otp stores the token + user in localStorage
    // Now read them back into React state
    setTokenState(getToken());
    setUserState(getUser());
    return data;
  }, []);

  const logout = useCallback(async () => {
    await apiLogout();
    setTokenState(null);
    setUserState(null);
  }, []);

  const isAuthenticated = !!token && !!user;
  const isAdmin = user?.role === 'admin';
  const isStaff = user?.role === 'staff';
  const isStudent = user?.role === 'student';

  return (
    <AuthContext.Provider value={{
      user,
      token,
      loading,
      login,
      verifyOtp,
      logout,
      isAuthenticated,
      isAdmin,
      isStaff,
      isStudent,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
