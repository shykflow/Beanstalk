import { ApiClient, ActivityBatchItem } from './api-client'
import { uIOhook } from 'uiohook-napi'
import os from 'os'

// Real activity tracking using Electron APIs
export class ActivityMonitor {
  private tracking = false
  private samples: ActivityBatchItem[] = []
  private lastMousePos = { x: 0, y: 0 }
  private keyPressCount = 0
  private sampleInterval: NodeJS.Timeout | null = null
  private uploadInterval: NodeJS.Timeout | null = null
  private rollupInterval: NodeJS.Timeout | null = null
  private sessionId: string | null = null
  private lastSync: Date | null = null
  private sessionStartTime: Date | null = null
  private lastActivityTime: Date | null = null
  private activeSeconds = 0
  private idleSeconds = 0
  private breakSeconds = 0
  private timerInterval: NodeJS.Timeout | null = null
  private schedule: any = null
  private wasIdle = false

  constructor(private apiClient: ApiClient) {}

  async start() {
    if (this.tracking) return

    try {
      // Fetch schedule
      this.schedule = await this.apiClient.getSchedule()
      
      // Start session
      const session = await this.apiClient.startSession({
        deviceId: this.getDeviceId(),
        platform: os.platform(),
      })
      this.sessionId = session.id
      this.sessionStartTime = new Date()
      this.lastActivityTime = new Date()
      this.tracking = true
      this.activeSeconds = 0
      this.idleSeconds = 0
      this.breakSeconds = 0

      // Start native keyboard listener
      this.startKeyboardListener()

      // Sample every 5 seconds
      this.sampleInterval = setInterval(() => {
        this.captureSample()
      }, 5000)

      // Upload every 60 seconds
      this.uploadInterval = setInterval(() => {
        this.uploadSamples()
      }, 60000)

      // Trigger rollup every 1 minute for live admin updates
      this.rollupInterval = setInterval(() => {
        this.triggerRollup()
      }, 60 * 1000)

      // Timer update every second
      this.timerInterval = setInterval(() => {
        this.updateTimer()
      }, 1000)

      console.log('Activity tracking started')
    } catch (error) {
      console.error('Failed to start tracking:', error)
      throw error
    }
  }

  async stop() {
    if (!this.tracking) return

    console.log('Stopping activity tracking...')
    this.tracking = false

    if (this.sampleInterval) {
      clearInterval(this.sampleInterval)
      this.sampleInterval = null
    }

    if (this.uploadInterval) {
      clearInterval(this.uploadInterval)
      this.uploadInterval = null
    }

    if (this.rollupInterval) {
      clearInterval(this.rollupInterval)
      this.rollupInterval = null
    }

    if (this.timerInterval) {
      clearInterval(this.timerInterval)
      this.timerInterval = null
    }

    // Stop keyboard listener
    this.stopKeyboardListener()

    const sessionIdToStop = this.sessionId

    try {
      // Capture final sample before upload
      if (this.sessionId) {
        this.captureSample()
        console.log('Captured final sample')
      }

      // Upload remaining samples
      if (this.samples.length > 0) {
        await this.uploadSamples()
        console.log('Uploaded final samples')
      }

      // Trigger final rollup to process all samples
      if (sessionIdToStop) {
        await this.apiClient.triggerRollup()
        console.log('Triggered final rollup')
      }

      // End session (this also triggers backend rollup)
      if (sessionIdToStop) {
        await this.apiClient.stopSession(sessionIdToStop)
        console.log('Session ended on backend')
      }
    } catch (error) {
      console.error('Error during stop cleanup:', error)
      // Don't throw - ensure cleanup completes
    } finally {
      // Always clear session state
      this.sessionId = null
      this.sessionStartTime = null
      this.lastActivityTime = null
      this.samples = []
      this.lastSync = null
      this.activeSeconds = 0
      this.idleSeconds = 0
      this.breakSeconds = 0
      this.schedule = null
      this.wasIdle = false
    }

    console.log('Activity tracking stopped successfully')
  }

  private captureSample() {
    const mouseDelta = this.getMouseDelta()
    const keyCount = this.keyPressCount
    
    const sample: ActivityBatchItem = {
      capturedAt: new Date().toISOString(),
      mouseDelta,
      keyCount,
      deviceSessionId: this.sessionId || undefined,
    }

    this.samples.push(sample)
    
    // Update last activity time if there's activity
    if (mouseDelta > 0 || keyCount > 0) {
      this.lastActivityTime = new Date()
    }
    
    this.keyPressCount = 0 // Reset after capture
  }

  private getMouseDelta(): number {
    // Mouse movement is tracked by uiohook listener
    // Return accumulated distance and reset
    const delta = Math.floor(Math.sqrt(
      Math.pow(this.lastMousePos.x, 2) + Math.pow(this.lastMousePos.y, 2)
    ))
    this.lastMousePos = { x: 0, y: 0 }
    return delta
  }

  private async uploadSamples() {
    if (this.samples.length === 0) return

    const samplesToUpload = [...this.samples]
    this.samples = []

    try {
      await this.apiClient.uploadActivity(samplesToUpload)
      this.lastSync = new Date()
      console.log(`Uploaded ${samplesToUpload.length} samples`)
    } catch (error) {
      console.error('Failed to upload samples:', error)
      // Re-add samples for retry only if still tracking
      if (this.tracking) {
        this.samples.unshift(...samplesToUpload)
      }
    }
  }

  private getDeviceId(): string {
    // Generate a unique device ID based on hostname and platform
    return `${os.hostname()}-${os.platform()}-${os.arch()}`
  }

  isTracking(): boolean {
    return this.tracking
  }

  getLastSync(): Date | null {
    return this.lastSync
  }

  getSessionStartTime(): Date | null {
    return this.sessionStartTime
  }

  getElapsedSeconds(): number {
    if (!this.sessionStartTime) return 0
    return Math.floor((Date.now() - this.sessionStartTime.getTime()) / 1000)
  }

  private updateTimer() {
    if (!this.tracking || !this.schedule) return

    const now = new Date()
    
    // Check if in break time
    if (this.isInBreakTime(now)) {
      this.breakSeconds++
      return
    }

    // Check if idle (no activity for threshold seconds)
    const idleThreshold = this.schedule.idleThresholdSeconds || 300
    const secondsSinceActivity = this.lastActivityTime 
      ? Math.floor((now.getTime() - this.lastActivityTime.getTime()) / 1000)
      : 0

    const isCurrentlyIdle = secondsSinceActivity >= idleThreshold

    if (isCurrentlyIdle) {
      // Just became idle - convert previous threshold seconds from active to idle
      if (!this.wasIdle) {
        const secondsToConvert = Math.min(idleThreshold, this.activeSeconds)
        this.activeSeconds -= secondsToConvert
        this.idleSeconds += secondsToConvert
        this.wasIdle = true
      }
      this.idleSeconds++
    } else {
      // Below threshold - count as active (like backend)
      if (this.wasIdle) {
        this.wasIdle = false
      }
      this.activeSeconds++
    }
  }

  private isInBreakTime(date: Date): boolean {
    if (!this.schedule) return false

    const tz = this.schedule.tz || 'Asia/Karachi'
    
    // Get time in organization timezone
    const timeStr = new Intl.DateTimeFormat('en-US', {
      timeZone: tz,
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    }).format(date)

    const { breakStart, breakEnd } = this.schedule
    
    if (breakEnd < breakStart) {
      return timeStr >= breakStart || timeStr < breakEnd
    }
    
    return timeStr >= breakStart && timeStr < breakEnd
  }

  getTimerStats() {
    return {
      activeSeconds: this.activeSeconds,
      idleSeconds: this.idleSeconds,
      breakSeconds: this.breakSeconds,
      totalSeconds: this.activeSeconds + this.idleSeconds + this.breakSeconds,
    }
  }

  private startKeyboardListener() {
    // Listen to keyboard events globally
    uIOhook.on('keydown', () => {
      this.keyPressCount++
    })

    // Listen to mouse movement globally
    uIOhook.on('mousemove', (event) => {
      // Accumulate mouse movement delta
      this.lastMousePos.x += Math.abs(event.x)
      this.lastMousePos.y += Math.abs(event.y)
    })

    // Start the native hook
    uIOhook.start()
  }

  private stopKeyboardListener() {
    // Stop the native hook
    uIOhook.stop()
  }

  private async triggerRollup() {
    if (!this.tracking) {
      console.log('⏭️  Skipping rollup - not tracking')
      return
    }
    
    console.log('🔄 Triggering rollup...')
    
    try {
      // Upload any pending samples first
      if (this.samples.length > 0) {
        console.log(`  📤 Uploading ${this.samples.length} pending samples first`)
        await this.uploadSamples()
      }
      
      // Trigger rollup on backend
      console.log('  📡 Calling backend rollup API...')
      const result = await this.apiClient.triggerRollup()
      console.log('  ✅ Rollup triggered successfully:', result)
    } catch (error) {
      console.error('  ❌ Failed to trigger rollup:', error)
    }
  }
}
