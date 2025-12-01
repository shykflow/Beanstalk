import { useState, useEffect } from 'react'

declare global {
  interface Window {
    electronAPI: {
      login: (credentials: { email: string; password: string }) => Promise<any>
      logout: () => Promise<any>
      startTracking: () => Promise<any>
      stopTracking: () => Promise<any>
      getStatus: () => Promise<any>
      getAuth: () => Promise<any>
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

  useEffect(() => {
    checkAuth()
    const interval = setInterval(updateStatus, 5000)
    return () => clearInterval(interval)
  }, [])

  const checkAuth = async () => {
    const auth = await window.electronAPI.getAuth()
    setIsAuthenticated(!!auth)
    if (auth) {
      updateStatus()
    }
  }

  const updateStatus = async () => {
    const status = await window.electronAPI.getStatus()
    setIsTracking(status.isTracking)
    setIsAuthenticated(status.isAuthenticated)
    if (status.lastSync) {
      setLastSync(new Date(status.lastSync))
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
    await window.electronAPI.logout()
    setIsAuthenticated(false)
    setIsTracking(false)
  }

  const handleStartTracking = async () => {
    try {
      await window.electronAPI.startTracking()
      setIsTracking(true)
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
          <h1>Time Tracker</h1>
          <p style={{ marginBottom: '20px' }}>Sign in to start tracking</p>

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

  return (
    <div className="container">
      <div className="card">
        <h1>Time Tracker</h1>

        <div className="status">
          <div className={`status-dot ${isTracking ? '' : 'inactive'}`} />
          <span>{isTracking ? 'Tracking Active' : 'Tracking Stopped'}</span>
        </div>

        {lastSync && (
          <p style={{ marginBottom: '16px', fontSize: '12px' }}>
            Last sync: {lastSync.toLocaleTimeString()}
          </p>
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
        >
          Logout
        </button>
      </div>

      <div className="card">
        <h2>Information</h2>
        <p style={{ marginBottom: '8px' }}>
          <strong>Working Hours:</strong> 16:50 - 02:00 (Asia/Karachi)
        </p>
        <p style={{ marginBottom: '8px' }}>
          <strong>Break Time:</strong> 22:00 - 23:00
        </p>
        <p>
          <strong>Idle Threshold:</strong> 5 minutes
        </p>
      </div>
    </div>
  )
}

export default App
