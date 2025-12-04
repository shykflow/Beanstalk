import { useState, useEffect } from 'react'

interface TimerStats {
  activeSeconds: number
  idleSeconds: number
  breakSeconds: number
  totalSeconds: number
}

declare global {
  interface Window {
    electronAPI: {
      login: (credentials: { email: string; password: string }) => Promise<any>
      logout: () => Promise<any>
      startTracking: () => Promise<any>
      stopTracking: () => Promise<any>
      getStatus: () => Promise<any>
      getAuth: () => Promise<any>
      getOrganization: () => Promise<any>
      getSchedule: () => Promise<any>
    }
  }
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isTracking, setIsTracking] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [lastSync, setLastSync] = useState<Date | null>(null)
  const [statusInterval, setStatusInterval] = useState<NodeJS.Timeout | null>(null)
  const [organization, setOrganization] = useState<any>(null)
  const [schedule, setSchedule] = useState<any>(null)
  const [loadingOrgData, setLoadingOrgData] = useState(false)
  const [timerStats, setTimerStats] = useState<TimerStats | null>(null)

  useEffect(() => {
    checkAuth()
  }, [])

  useEffect(() => {
    if (statusInterval) {
      clearInterval(statusInterval)
    }
    
    if (isAuthenticated) {
      const interval = setInterval(updateStatus, 1000)
      setStatusInterval(interval)
      return () => clearInterval(interval)
    }
  }, [isAuthenticated])

  const checkAuth = async () => {
    const auth = await window.electronAPI.getAuth()
    setIsAuthenticated(!!auth)
    if (auth) {
      updateStatus()
      loadOrganizationData()
    }
  }

  const loadOrganizationData = async () => {
    setLoadingOrgData(true)
    try {
      const org = await window.electronAPI.getOrganization()
      if (org && !org.error) {
        setOrganization(org)
      }

      const sched = await window.electronAPI.getSchedule()
      if (sched && !sched.error) {
        setSchedule(sched)
      } else {
        // Set default schedule as fallback
        setSchedule({
          tz: 'Asia/Karachi',
          checkinStart: '16:50',
          checkinEnd: '02:00',
          breakStart: '22:00',
          breakEnd: '23:00',
          idleThresholdSeconds: 300
        })
      }
    } catch (err) {
      // Set default schedule on error
      setSchedule({
        tz: 'Asia/Karachi',
        checkinStart: '16:50',
        checkinEnd: '02:00',
        breakStart: '22:00',
        breakEnd: '23:00',
        idleThresholdSeconds: 300
      })
    } finally {
      setLoadingOrgData(false)
    }
  }

  const updateStatus = async () => {
    try {
      const status = await window.electronAPI.getStatus()
      setIsTracking(status.isTracking)
      setIsAuthenticated(status.isAuthenticated)
      
      if (status.lastSync) {
        setLastSync(new Date(status.lastSync))
      } else {
        setLastSync(null)
      }
      
      if (status.timerStats) {
        setTimerStats(status.timerStats)
      } else {
        setTimerStats(null)
      }
    } catch (err) {
      console.error('Status update failed:', err)
    }
  }

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const result = await window.electronAPI.login({ email, password })
      if (result.success) {
        setIsAuthenticated(true)
        setEmail('')
        setPassword('')
        await loadOrganizationData()
      } else {
        setError(result.error || 'Login failed')
      }
    } catch (err: any) {
      setError(err.message || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  const handleLogout = async () => {
    setLoading(true)
    
    // Stop status updates immediately
    if (statusInterval) {
      clearInterval(statusInterval)
      setStatusInterval(null)
    }
    
    // Force immediate logout state
    setIsAuthenticated(false)
    setIsTracking(false)
    setLastSync(null)
    setError('')
    setOrganization(null)
    setSchedule(null)
    setTimerStats(null)
    
    try {
      await window.electronAPI.logout()
    } catch (err: any) {
      // Silently handle logout error
    } finally {
      setLoading(false)
    }
  }

  const handleStartTracking = async () => {
    try {
      await window.electronAPI.startTracking()
      setIsTracking(true)
      await updateStatus()
    } catch (err: any) {
      setError(err.message)
    }
  }

  const handleStopTracking = async () => {
    try {
      await window.electronAPI.stopTracking()
      setIsTracking(false)
    } catch (err: any) {
      setError(err.message)
    }
  }

  if (!isAuthenticated) {
    return (
      <div className="container">
        <div className="card">
          <div className="brand-header">
            <h1>{organization?.name || 'Time Tracker'}</h1>
            <p className="brand-subtitle">Professional Time Tracking</p>
          </div>
          <p style={{ marginBottom: '24px', textAlign: 'center' }}>Sign in to start tracking your time</p>

          {error && <div className="error">{error}</div>}

          <form onSubmit={handleLogin}>
            <label className="label">Email</label>
            <input
              type="email"
              className="input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />

            <label className="label">Password</label>
            <input
              type="password"
              className="input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />

            <button type="submit" className="button" disabled={loading}>
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>
        </div>
      </div>
    )
  }

  const formatTime = (seconds: number) => {
    const h = Math.floor(seconds / 3600)
    const m = Math.floor((seconds % 3600) / 60)
    const s = seconds % 60
    return `${h}h ${m}m ${s}s`
  }

  return (
    <div className="container">
      <div className="card">
        <div className="brand-header">
          <h1>{organization?.name || 'Time Tracker'}</h1>
          <p className="brand-subtitle">Professional Time Tracking</p>
        </div>

        <div className="status">
          <div className={`status-dot ${isTracking ? '' : 'inactive'}`} />
          <span>{isTracking ? 'Tracking Active' : 'Tracking Stopped'}</span>
        </div>

        {isTracking && (
          <div className="timer-stats">
            <div className="timer-row">
              <span className="timer-label">⚡ Active Time</span>
              <span className="timer-value active">{formatTime(timerStats?.activeSeconds || 0)}</span>
            </div>
            <div className="timer-row">
              <span className="timer-label">⏸️ Idle Time</span>
              <span className="timer-value idle">{formatTime(timerStats?.idleSeconds || 0)}</span>
            </div>
            <div className="timer-row">
              <span className="timer-label">☕ Break Time</span>
              <span className="timer-value break">{formatTime(timerStats?.breakSeconds || 0)}</span>
            </div>
            <div className="timer-divider"></div>
            <div className="timer-row total">
              <span className="timer-label">✓ Total Productive</span>
              <span className="timer-value">{formatTime(timerStats?.activeSeconds || 0)}</span>
            </div>
          </div>
        )}

        {lastSync && (
          <div className="sync-info">
            <span className="sync-label">Last sync:</span>
            <span className="sync-time">{lastSync.toLocaleTimeString()}</span>
          </div>
        )}

        {error && <div className="error">{error}</div>}

        {isTracking ? (
          <button onClick={handleStopTracking} className="button button-secondary">
            Stop Tracking
          </button>
        ) : (
          <button onClick={handleStartTracking} className="button">
            Start Tracking
          </button>
        )}

        <button
          onClick={handleLogout}
          className="button button-secondary"
          style={{ marginTop: '12px' }}
          disabled={loading}
        >
          {loading ? 'Logging out...' : 'Logout'}
        </button>
      </div>

      {loadingOrgData ? (
        <div className="card info-card">
          <p style={{ textAlign: 'center', color: '#64748b' }}>Loading organization data...</p>
        </div>
      ) : schedule ? (
        <div className="card info-card">
          <h2>📋 Tracking Rules</h2>
          <div className="info-item">
            <span className="info-label">🕐 Working Hours:</span>
            <span className="info-value">
              {schedule.checkinStart} - {schedule.checkinEnd} ({schedule.tz})
            </span>
          </div>
          <div className="info-item">
            <span className="info-label">☕ Break Time:</span>
            <span className="info-value">
              {schedule.breakStart} - {schedule.breakEnd}
            </span>
          </div>
          <div className="info-item">
            <span className="info-label">⏱️ Idle Threshold:</span>
            <span className="info-value">
              {Math.floor(schedule.idleThresholdSeconds / 60)} minutes
            </span>
          </div>
        </div>
      ) : (
        <div className="card info-card">
          <p style={{ textAlign: 'center', color: '#ef4444' }}>Failed to load tracking rules. Please check your connection.</p>
        </div>
      )}
    </div>
  )
}

export default App
