const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001/api'

class ApiClient {
  private token: string | null = null

  setToken(token: string) {
    this.token = token
    if (typeof window !== 'undefined') {
      localStorage.setItem('token', token)
    }
  }

  getToken(): string | null {
    if (!this.token && typeof window !== 'undefined') {
      this.token = localStorage.getItem('token')
    }
    return this.token
  }

  clearToken() {
    this.token = null
    if (typeof window !== 'undefined') {
      localStorage.removeItem('token')
    }
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const token = this.getToken()
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    }

    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    const response = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      headers,
    })

    if (!response.ok) {
      if (response.status === 401) {
        this.clearToken()
        if (typeof window !== 'undefined') {
          window.location.href = '/login'
        }
      }
      const error = await response.json().catch(() => ({ message: 'Request failed' }))
      throw new Error(error.message || 'Request failed')
    }

    if (response.status === 204) {
      return {} as T
    }

    return response.json()
  }

  // Auth
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

  async register(data: {
    email: string
    password: string
    fullName: string
    orgName: string
  }) {
    const response = await this.request<{ accessToken: string; refreshToken: string }>(
      '/auth/register',
      {
        method: 'POST',
        body: JSON.stringify(data),
      }
    )
    this.setToken(response.accessToken)
    return response
  }

  async logout() {
    await this.request('/auth/logout', { method: 'POST' })
    this.clearToken()
  }

  // Users
  async getUsers() {
    return this.request<any[]>('/users')
  }

  async getUser(id: string) {
    return this.request<any>(`/users/${id}`)
  }

  async createUser(data: any) {
    return this.request<any>('/users', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async updateUser(id: string, data: any) {
    return this.request<any>(`/users/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  async deleteUser(id: string) {
    return this.request<void>(`/users/${id}`, { method: 'DELETE' })
  }

  // Reports
  async getDailyReport(date?: string) {
    const query = date ? `?date=${date}` : ''
    return this.request<any>(`/reports/daily${query}`)
  }

  async getWeeklyReport(week?: string) {
    const query = week ? `?week=${week}` : ''
    return this.request<any>(`/reports/weekly${query}`)
  }

  async getMonthlyReport(month?: string) {
    const query = month ? `?month=${month}` : ''
    return this.request<any>(`/reports/monthly${query}`)
  }

  async getUserTimesheet(userId: string, from: string, to: string) {
    return this.request<any>(`/reports/timesheet?userId=${userId}&from=${from}&to=${to}`)
  }

  // Organization
  async getOrganization() {
    return this.request<any>('/organizations/me')
  }

  async updateOrganization(data: any) {
    return this.request<any>('/organizations/me', {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  async getSchedule() {
    return this.request<any>('/organizations/schedule')
  }

  async updateSchedule(data: any) {
    return this.request<any>('/organizations/schedule', {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  async createAdjustment(data: any) {
    return this.request<any>('/organizations/adjustments', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async getAdjustments(userId: string, from?: string, to?: string) {
    let query = `?userId=${userId}`
    if (from) query += `&from=${from}`
    if (to) query += `&to=${to}`
    return this.request<any[]>(`/organizations/adjustments${query}`)
  }
}

export const api = new ApiClient()
