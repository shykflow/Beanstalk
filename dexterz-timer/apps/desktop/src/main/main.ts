import { app, BrowserWindow, Tray, Menu, ipcMain, nativeImage } from 'electron'
import path from 'path'
import { ActivityMonitor } from './activity-monitor'
import { ApiClient } from './api-client'
import Store from 'electron-store'

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

  mainWindow.on('close', (event) => {
    if (!isQuitting) {
      event.preventDefault()
      mainWindow?.hide()
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

app.whenReady().then(() => {
  createWindow()
  createTray()

  apiClient = new ApiClient()
  
  // Check for stored auth and restore session
  const storedAuth = store.get('auth') as any
  if (storedAuth?.accessToken) {
    apiClient.setToken(storedAuth.accessToken)
  }
  
  activityMonitor = new ActivityMonitor(apiClient)

  // Auto-launch on startup
  app.setLoginItemSettings({
    openAtLogin: true,
  })
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
    
    // Reset API client
    apiClient = new ApiClient()
    
    // Reset activity monitor
    activityMonitor = new ActivityMonitor(apiClient)
    
    return { success: true }
  } catch (error: any) {
    console.error('Logout error:', error)
    // Force clear even on error
    store.delete('auth')
    apiClient = new ApiClient()
    activityMonitor = new ActivityMonitor(apiClient)
    return { success: true }
  }
})

ipcMain.handle('start-tracking', async () => {
  try {
    await activityMonitor?.start()
    return { success: true }
  } catch (error: any) {
    return { success: false, error: error.message }
  }
})

ipcMain.handle('stop-tracking', async () => {
  try {
    await activityMonitor?.stop()
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
