"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ApiClient = void 0;
const API_URL = process.env.API_URL || 'http://localhost:3001/api';
class ApiClient {
    constructor() {
        this.token = null;
    }
    setToken(token) {
        this.token = token;
    }
    async request(endpoint, options = {}) {
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers,
        };
        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }
        const response = await fetch(`${API_URL}${endpoint}`, {
            ...options,
            headers,
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({ message: 'Request failed' }));
            throw new Error(error.message || 'Request failed');
        }
        if (response.status === 204) {
            return {};
        }
        return response.json();
    }
    async login(email, password) {
        const data = await this.request('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password }),
        });
        this.setToken(data.accessToken);
        return data;
    }
    async logout() {
        await this.request('/auth/logout', { method: 'POST' });
        this.token = null;
    }
    async startSession(data) {
        return this.request('/activity/sessions/start', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }
    async stopSession(sessionId) {
        return this.request('/activity/sessions/stop', {
            method: 'POST',
            body: JSON.stringify({ sessionId }),
        });
    }
    async uploadActivity(samples) {
        return this.request('/activity/batch', {
            method: 'POST',
            body: JSON.stringify({ samples }),
        });
    }
}
exports.ApiClient = ApiClient;
