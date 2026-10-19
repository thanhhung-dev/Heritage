/** Authentication service for API calls. */

import { message } from 'antd';
import { API_BASE_URL } from '@/config/api';
import { setAuthTokens, type AuthTokens, type User } from '@/lib/auth';

export interface RegisterData {
  email: string;
  username: string;
  password: string;
}

export interface LoginData {
  username_or_email: string;
  password: string;
}

export interface RegisterResponse {
  account_id: string;
  email: string;
  username: string;
  message: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface ErrorResponse {
  detail: string;
}

/**
 * Register a new user account
 */
export async function registerUser(data: RegisterData): Promise<RegisterResponse> {
  const response = await fetch(`${API_BASE_URL}/auth/register`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });

  const json = await response.json();

  if (!response.ok) {
    const error = json as ErrorResponse;
    throw new Error(error.detail || 'Đăng ký thất bại');
  }

  return json as RegisterResponse;
}

/**
 * Login with username/email and password
 */
export async function loginUser(data: LoginData): Promise<LoginResponse> {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });

  const json = await response.json();

  if (!response.ok) {
    const error = json as ErrorResponse;
    throw new Error(error.detail || 'Đăng nhập thất bại');
  }

  return json as LoginResponse;
}

/**
 * Handle registration with UI feedback
 */
export async function handleRegister(
  data: RegisterData,
  onSuccess?: () => void,
): Promise<void> {
  try {
    const response = await registerUser(data);
    message.success(response.message || 'Đăng ký thành công!');
    if (onSuccess) onSuccess();
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Đăng ký thất bại';
    message.error(errorMessage);
    throw error;
  }
}

/**
 * Handle login with UI feedback and token storage
 */
export async function handleLogin(
  data: LoginData,
  onSuccess?: () => void,
): Promise<void> {
  try {
    const response = await loginUser(data);
    
    // Store tokens and user info
    setAuthTokens(response);
    
    message.success('Đăng nhập thành công!');
    if (onSuccess) onSuccess();
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Đăng nhập thất bại';
    message.error(errorMessage);
    throw error;
  }
}

/**
 * Login with Google OAuth 2.0
 */
export async function loginWithGoogle(idToken: string): Promise<LoginResponse> {
  const response = await fetch(`${API_BASE_URL}/auth/google`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ id_token: idToken }),
  });

  const json = await response.json();

  if (!response.ok) {
    const error = json as ErrorResponse;
    throw new Error(error.detail || 'Đăng nhập Google thất bại');
  }

  return json as LoginResponse;
}

/**
 * Handle Google login with UI feedback and token storage
 */
export async function handleGoogleLogin(
  idToken: string,
  onSuccess?: () => void,
): Promise<void> {
  try {
    const response = await loginWithGoogle(idToken);
    
    // Store tokens and user info
    setAuthTokens(response);
    
    message.success('Đăng nhập bằng Google thành công!');
    if (onSuccess) onSuccess();
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Đăng nhập Google thất bại';
    message.error(errorMessage);
    throw error;
  }
}

/**
 * Request password reset link
 */
export async function forgotPassword(email: string): Promise<{ message: string }> {
  const response = await fetch(`${API_BASE_URL}/auth/forgot-password`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email }),
  });

  const json = await response.json();

  if (!response.ok) {
    const error = json as ErrorResponse;
    throw new Error(error.detail || 'Gửi yêu cầu thất bại');
  }

  return json as { message: string };
}

/**
 * Reset password with token
 */
export async function resetPassword(
  token: string,
  newPassword: string,
): Promise<{ message: string }> {
  const response = await fetch(`${API_BASE_URL}/auth/reset-password`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ token, new_password: newPassword }),
  });

  const json = await response.json();

  if (!response.ok) {
    const error = json as ErrorResponse;
    throw new Error(error.detail || 'Đặt lại mật khẩu thất bại');
  }

  return json as { message: string };
}
