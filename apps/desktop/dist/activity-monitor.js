"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.ActivityMonitor = void 0;
const os_1 = __importDefault(require("os"));
// Simple activity tracking without native dependencies for cross-platform compatibility
class ActivityMonitor {
    constructor(apiClient) {
        this.apiClient = apiClient;
        this.tracking = false;
        this.samples = [];
        this.lastMousePos = { x: 0, y: 0 };
        this.keyPressCount = 0;
        this.sampleInterval = null;
        this.uploadInterval = null;
        this.sessionId = null;
        this.lastSync = null;
    }
    async start() {
        if (this.tracking)
            return;
        try {
            // Start session
            const session = await this.apiClient.startSession({
                deviceId: this.getDeviceId(),
                platform: os_1.default.platform(),
            });
            this.sessionId = session.id;
            this.tracking = true;
            // Sample every 5 seconds
            this.sampleInterval = setInterval(() => {
                this.captureSample();
            }, 5000);
            // Upload every 60 seconds
            this.uploadInterval = setInterval(() => {
                this.uploadSamples();
            }, 60000);
            console.log('Activity tracking started');
        }
        catch (error) {
            console.error('Failed to start tracking:', error);
            throw error;
        }
    }
    async stop() {
        if (!this.tracking)
            return;
        this.tracking = false;
        if (this.sampleInterval) {
            clearInterval(this.sampleInterval);
            this.sampleInterval = null;
        }
        if (this.uploadInterval) {
            clearInterval(this.uploadInterval);
            this.uploadInterval = null;
        }
        // Upload remaining samples
        await this.uploadSamples();
        // End session
        if (this.sessionId) {
            await this.apiClient.stopSession(this.sessionId);
            this.sessionId = null;
        }
        console.log('Activity tracking stopped');
    }
    captureSample() {
        // In a real implementation, you would use native modules to track mouse/keyboard
        // For cross-platform compatibility, we're using a simplified approach
        // You can integrate robotjs or similar libraries for actual tracking
        const sample = {
            capturedAt: new Date().toISOString(),
            mouseDelta: this.getMouseDelta(),
            keyCount: this.keyPressCount,
            deviceSessionId: this.sessionId || undefined,
        };
        this.samples.push(sample);
        this.keyPressCount = 0; // Reset after capture
    }
    getMouseDelta() {
        // Simplified: In production, use actual mouse position tracking
        // This is a placeholder that simulates activity
        const randomActivity = Math.random() > 0.3 ? Math.floor(Math.random() * 100) : 0;
        return randomActivity;
    }
    async uploadSamples() {
        if (this.samples.length === 0)
            return;
        try {
            const samplesToUpload = [...this.samples];
            this.samples = [];
            await this.apiClient.uploadActivity(samplesToUpload);
            this.lastSync = new Date();
            console.log(`Uploaded ${samplesToUpload.length} samples`);
        }
        catch (error) {
            console.error('Failed to upload samples:', error);
            // Re-add samples for retry
            this.samples.unshift(...this.samples);
        }
    }
    getDeviceId() {
        // Generate a unique device ID based on hostname and platform
        return `${os_1.default.hostname()}-${os_1.default.platform()}-${os_1.default.arch()}`;
    }
    isTracking() {
        return this.tracking;
    }
    getLastSync() {
        return this.lastSync;
    }
}
exports.ActivityMonitor = ActivityMonitor;
