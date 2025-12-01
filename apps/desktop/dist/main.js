"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const electron_1 = require("electron");
const path_1 = __importDefault(require("path"));
const activity_monitor_1 = require("./activity-monitor");
const api_client_1 = require("./api-client");
const electron_store_1 = __importDefault(require("electron-store"));
const store = new electron_store_1.default();
let mainWindow = null;
let tray = null;
let activityMonitor = null;
let apiClient = null;
let isQuitting = false;
function createWindow() {
    mainWindow = new electron_1.BrowserWindow({
        width: 400,
        height: 600,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path_1.default.join(__dirname, 'preload.js'),
        },
        show: false,
        frame: true,
        resizable: false,
    });
    // Always try to load from Vite dev server in development
    const isDev = !electron_1.app.isPackaged;
    if (isDev) {
        mainWindow.loadURL('http://localhost:5175');
    }
    else {
        mainWindow.loadFile(path_1.default.join(__dirname, '../renderer/dist/index.html'));
    }
    mainWindow.on('close', (event) => {
        if (!isQuitting) {
            event.preventDefault();
            mainWindow?.hide();
        }
    });
    mainWindow.on('ready-to-show', () => {
        mainWindow?.show();
    });
}
function createTray() {
    // Create a simple icon (in production, use actual icon files)
    const icon = electron_1.nativeImage.createEmpty();
    tray = new electron_1.Tray(icon);
    const contextMenu = electron_1.Menu.buildFromTemplate([
        {
            label: 'Show App',
            click: () => {
                mainWindow?.show();
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
                isQuitting = true;
                electron_1.app.quit();
            },
        },
    ]);
    tray.setContextMenu(contextMenu);
    tray.setToolTip('Time Tracker');
    tray.on('click', () => {
        mainWindow?.show();
    });
}
electron_1.app.whenReady().then(() => {
    createWindow();
    createTray();
    apiClient = new api_client_1.ApiClient();
    activityMonitor = new activity_monitor_1.ActivityMonitor(apiClient);
    // Auto-launch on startup
    electron_1.app.setLoginItemSettings({
        openAtLogin: true,
    });
});
electron_1.app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        electron_1.app.quit();
    }
});
electron_1.app.on('activate', () => {
    if (electron_1.BrowserWindow.getAllWindows().length === 0) {
        createWindow();
    }
});
// IPC Handlers
electron_1.ipcMain.handle('login', async (_, { email, password }) => {
    try {
        const result = await apiClient?.login(email, password);
        if (result) {
            store.set('auth', result);
            return { success: true, data: result };
        }
        return { success: false, error: 'Login failed' };
    }
    catch (error) {
        return { success: false, error: error.message };
    }
});
electron_1.ipcMain.handle('logout', async () => {
    try {
        await apiClient?.logout();
        store.delete('auth');
        activityMonitor?.stop();
        return { success: true };
    }
    catch (error) {
        return { success: false, error: error.message };
    }
});
electron_1.ipcMain.handle('start-tracking', async () => {
    try {
        await activityMonitor?.start();
        return { success: true };
    }
    catch (error) {
        return { success: false, error: error.message };
    }
});
electron_1.ipcMain.handle('stop-tracking', async () => {
    try {
        await activityMonitor?.stop();
        return { success: true };
    }
    catch (error) {
        return { success: false, error: error.message };
    }
});
electron_1.ipcMain.handle('get-status', async () => {
    return {
        isTracking: activityMonitor?.isTracking() || false,
        lastSync: activityMonitor?.getLastSync(),
        isAuthenticated: !!store.get('auth'),
    };
});
electron_1.ipcMain.handle('get-auth', async () => {
    return store.get('auth');
});
// Update tray status periodically
setInterval(() => {
    if (tray && activityMonitor) {
        const isTracking = activityMonitor.isTracking();
        const menu = electron_1.Menu.buildFromTemplate([
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
                    isQuitting = true;
                    electron_1.app.quit();
                },
            },
        ]);
        tray.setContextMenu(menu);
    }
}, 5000);
