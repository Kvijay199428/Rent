import { useState, useCallback } from 'react';
import { encryptPayload } from '@/lib/encryption';

const API_BASE = '/rent'; // Relative to current host

export interface ApiResponse<T = any> {
  data?: T;
  error?: string;
  status: 'idle' | 'loading' | 'success' | 'error';
}

export function useApi() {
  const [response, setResponse] = useState<ApiResponse>({ status: 'idle' });

  const request = useCallback(async <T = any>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T | null> => {
    setResponse({ status: 'loading' });
    
    try {
      const res = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
        credentials: 'include',
      });

      const data = await res.json().catch(() => null);

      if (!res.ok) {
        const errorMsg = data?.detail || data?.message || `HTTP ${res.status}`;
        setResponse({ status: 'error', error: errorMsg });
        throw new Error(errorMsg);
      }

      setResponse({ status: 'success', data });
      return data as T;
    } catch (err: any) {
      const errorMsg = err.message || 'Network error';
      setResponse({ status: 'error', error: errorMsg });
      return null;
    }
  }, []);

  return { request, response };
}

export async function apiGet(endpoint: string) {
  const res = await fetch(`${API_BASE}${endpoint}`, { credentials: 'include' });
  if (!res.ok) throw new Error((await res.json()).detail || `HTTP ${res.status}`);
  return res.json();
}

export async function apiPost(endpoint: string, body: any) {
  let finalBody = body;
  
  if (body.password || body.totp_token || body.new_password || body.confirm_password) {
    try {
      const pubKeyRes = await fetch('/rent/admin/api/auth/public-key');
      if (pubKeyRes.ok) {
        const { publicKey } = await pubKeyRes.json();
        const encrypted = await encryptPayload(body, publicKey);
        finalBody = { ...encrypted, remember_me: body.remember_me || body.rememberMe };
      }
    } catch (e) {
      console.error('Encryption failed', e);
    }
  }

  const res = await fetch(`${API_BASE}${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(finalBody),
    credentials: 'include',
  });
  if (!res.ok) throw new Error((await res.json()).detail || `HTTP ${res.status}`);
  return res.json();
}
