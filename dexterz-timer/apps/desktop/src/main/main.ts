import { app, BrowserWindow, Tray, Menu, ipcMain, nativeImage } from 'electron'
import path from 'path'
import { ActivityMonitor } from './activity-monitor'
import { ApiClient } from './api-client'
import Store from 'electron-store'
import dotenv from 'dotenv'

// Load environment variables
dotenv.config({ path: path.join(__dirname, '../../.env') })

const store = new Store()
let mainWindow: BrowserWindow | null = null
let tray: Tray | null = null
let activityMonitor: ActivityMonitor | null = null
let apiClient: ApiClient | null = null
let isQuitting = false

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 400,
    height: 600,
    title: 'Dexterz Time Tracker',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
    show: false,
    frame: true,
    resizable: false,
  })

  // Remove menu bar completely
  Menu.setApplicationMenu(null)

  // Always try to load from Vite dev server in development
  const isDev = !app.isPackaged
  if (isDev) {
    mainWindow.loadURL('http://localhost:5175')
  } else {
    mainWindow.loadFile(path.join(__dirname, '../renderer/dist/index.html'))
  }

  mainWindow.on('close', async (event) => {
    if (!isQuitting) {
      event.preventDefault()
      mainWindow?.hide()
      // Don't stop tracking when just hiding window
      return
    }
    
    // Only stop tracking when actually quitting
    event.preventDefault()
    
    const wasTracking = activityMonitor?.isTracking() || false
    if (wasTracking) {
      store.set('wasTracking', true)
      console.log('Saving tracking state before quit...')
    }
    
    try {
      await activityMonitor?.stop()
      console.log('Tracking stopped, closing window')
    } catch (error) {
      console.error('Error stopping tracking:', error)
    } finally {
      mainWindow?.destroy()
    }
  })

  mainWindow.on('ready-to-show', () => {
    mainWindow?.show()
  })
}

function createTray() {
  // Create a simple icon (in production, use actual icon files)
  const icon = nativeImage.createEmpty()
  tray = new Tray(icon)

  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'Show App',
      click: () => {
        mainWindow?.show()
      },
    },
    {
      label: 'Status',
      enabled: false,
    },
    { type: 'separator' },
    {
      label: 'Quit',
      click: () => {
        isQuitting = true
        app.quit()
      },
    },
  ])

  tray.setContextMenu(contextMenu)
  tray.setToolTip('Time Tracker')

  tray.on('click', () => {
    mainWindow?.show()
  })
}

app.whenReady().then(async () => {
  createWindow()
  createTray()

  apiClient = new ApiClient()
  
  // Check for stored auth and restore session
  const storedAuth = store.get('auth') as any
  if (storedAuth?.accessToken) {
    apiClient.setToken(storedAuth.accessToken)
  }
  
  activityMonitor = new ActivityMonitor(apiClient)

  // Restore tracking state if app was tracking before close
  const wasTracking = store.get('wasTracking') as boolean
  if (wasTracking && storedAuth?.accessToken) {
    console.log('Restoring previous tracking session...')
    try {
      await activityMonitor.start()
      console.log('Tracking session restored')
    } catch (error) {
      console.error('Failed to restore tracking:', error)
      store.delete('wasTracking')
    }
  }

  // Auto-launch on startup
  app.setLoginItemSettings({
    openAtLogin: true,
  })
})

app.on('before-quit', async (event) => {
  if (!isQuitting) {
    event.preventDefault()
    isQuitting = true
    
    console.log('App closing - stopping tracking...')
    
    // Save tracking state before stopping
    const wasTracking = activityMonitor?.isTracking() || false
    if (wasTracking) {
      store.set('wasTracking', true)
    }
    
    try {
      await activityMonitor?.stop()
      console.log('Tracking stopped successfully')
    } catch (error) {
      console.error('Failed to stop tracking on app close:', error)
    } finally {
      app.quit()
    }
  }
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow()
  }
})

// IPC Handlers
ipcMain.handle('login', async (_, { email, password }) => {
  try {
    // Ensure clean state before login
    await activityMonitor?.stop()
    
    const result = await apiClient?.login(email, password)
    if (result) {
      store.set('auth', result)
      // Reinitialize activity monitor with authenticated client
      activityMonitor = new ActivityMonitor(apiClient!)
      return { success: true, data: result }
    }
    return { success: false, error: 'Login failed' }
  } catch (error: any) {
    return { success: false, error: error.message }
  }
})

ipcMain.handle('logout', async () => {
  try {
    // Stop tracking first
    await activityMonitor?.stop()
    
    // Logout from API (if possible)
    try {
      await apiClient?.logout()
    } catch (apiError) {
      console.error('API logout failed:', apiError)
    }
    
    // Always clear local state regardless of API response
    store.delete('auth')
    store.delete('wasTracking')
    
    // Reset API client
    apiClient = new ApiClient()
    
    // Reset activity monitor
    activityMonitor = new ActivityMonitor(apiClient)
    
    return { success: true }
  } catch (error: any) {
    console.error('Logout error:', error)
    // Force clear even on error
    store.delete('auth')
    store.delete('wasTracking')
    apiClient = new ApiClient()
    activityMonitor = new ActivityMonitor(apiClient)
    return { success: true }
  }
})

ipcMain.handle('start-tracking', async () => {
  try {
    await activityMonitor?.start()
    store.set('wasTracking', true)
    return { success: true }
  } catch (error: any) {
    return { success: false, error: error.message }
  }
})

ipcMain.handle('stop-tracking', async () => {
  try {
    await activityMonitor?.stop()
    store.delete('wasTracking')
    return { success: true }
  } catch (error: any) {
    return { success: false, error: error.message }
  }
})

ipcMain.handle('get-status', async () => {
  const auth = store.get('auth')
  const isAuth = !!auth && !!apiClient?.tokenValue
  
  const timerStats = isAuth && activityMonitor ? activityMonitor.getTimerStats() : null
  
  return {
    isTracking: isAuth ? (activityMonitor?.isTracking() || false) : false,
    lastSync: isAuth ? activityMonitor?.getLastSync() : null,
    isAuthenticated: isAuth,
    timerStats,
  }
})

ipcMain.handle('get-auth', async () => {
  return store.get('auth')
})

ipcMain.handle('get-organization', async () => {
  try {
    return await apiClient?.getOrganization()
  } catch (error: any) {
    return { error: error.message }
  }
})

ipcMain.handle('get-schedule', async () => {
  try {
    const schedule = await apiClient?.getSchedule()
    return schedule
  } catch (error: any) {
    return { error: error.message }
  }
})

// Update tray status periodically
setInterval(() => {
  if (tray && activityMonitor) {
    const isTracking = activityMonitor.isTracking()
    const menu = Menu.buildFromTemplate([
      {
        label: 'Show App',
        click: () => mainWindow?.show(),
      },
      {
        label: `Status: ${isTracking ? 'Tracking' : 'Stopped'}`,
        enabled: false,
      },
      { type: 'separator' },
      {
        label: 'Quit',
        click: () => {
          isQuitting = true
          app.quit()
        },
      },
    ])
    tray.setContextMenu(menu)
  }
}, 5000)
