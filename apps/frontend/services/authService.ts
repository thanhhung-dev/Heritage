/** Auth API entry points and optional toast feedback for existing callers. */
import { message } from 'antd';
import { decodeGoogleIdToken } from '@/lib/googleAuth';
import { setAuthTokens, type User } from '@/lib/auth';
import { createAuthApi, type RegisterData, type LoginData } from './auth-api';
export type { RegisterData, LoginData, RegisterResponse, LoginResponse } from './auth-api';

const api = createAuthApi();
export const registerUser = (data: RegisterData) => api.register(data);
export const loginUser = (data: LoginData) => api.login(data);
export const loginWithGoogle = (idToken: string) => api.google(idToken);

export async function handleRegister(data: RegisterData, onSuccess?: () => void): Promise<void> {
  try {
    await registerUser(data);
    message.success('Registration successful. Please sign in.');
    onSuccess?.();
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Registration failed.');
    throw error;
  }
}

export async function handleLogin(data: LoginData, onSuccess?: () => void): Promise<void> {
  try {
    setAuthTokens(await loginUser(data));
    message.success('Signed in successfully.');
    onSuccess?.();
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Could not sign in.');
    throw error;
  }
}

function getSafeAvatarUrl(value?: string): string | undefined {
  if (!value) return undefined;
  try { const url = new URL(value); return url.protocol === 'https:' ? url.toString() : undefined; }
  catch { return undefined; }
}

export async function handleGoogleLogin(idToken: string, onSuccess?: () => void): Promise<void> {
  try {
    const response = await loginWithGoogle(idToken);
    const claims = decodeGoogleIdToken(idToken);
    const user: User = { ...response.user,
      display_name: claims.name?.trim() || response.user.display_name || response.user.username,
      avatar_url: getSafeAvatarUrl(claims.picture) ?? response.user.avatar_url };
    setAuthTokens({ ...response, user });
    message.success('Signed in with Google.');
    onSuccess?.();
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Google sign-in failed.');
    throw error;
  }
}

export async function forgotPassword(email: string): Promise<{ message: string }> {
  return api.forgot(email);
}

export async function resetPassword(token: string, newPassword: string): Promise<{ message: string }> {
  return api.reset(token, newPassword);
}
