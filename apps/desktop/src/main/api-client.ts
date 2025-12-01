import { ActivityBatchItem } from '@time-tracker/shared'

const API_URL = process.env.API_URL || 'http://localhost:3001/api'

export class ApiClient {
  private token: string | null = null

  setToken(token: string) {
    this.token = token
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`
    }

    const response = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      headers,
    })

    if (!response.ok) {
      const error: any = await response.json().catch(() => ({ message: 'Request failed' }))
      throw new Error(error.message || 'Request failed')
    }

    if (response.status === 204) {
      return {} as T
    }

    return response.json() as Promise<T>
  }

  async login(email: string, password: string) {
    const data = await this.request<{ accessToken: string; refreshToken: string }>(
      '/auth/login',
      {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      }
    )
    this.setToken(data.accessToken)
    return data
  }

  async logout() {
    await this.request('/auth/logout', { method: 'POST' })
    this.token = null
  }

  async startSession(data: { deviceId: string; platform: string }) {
    return this.request<{ id: string }>('/activity/sessions/start', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async stopSession(sessionId: string) {
    return this.request('/activity/sessions/stop', {
      method: 'POST',
      body: JSON.stringify({ sessionId }),
    })
  }

  async uploadActivity(samples: ActivityBatchItem[]) {
    return this.request('/activity/batch', {
      method: 'POST',
      body: JSON.stringify({ samples }),
    })
  }
}
