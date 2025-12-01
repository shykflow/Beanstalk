"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const electron_1 = require("electron");
electron_1.contextBridge.exposeInMainWorld('electronAPI', {
    login: (credentials) => electron_1.ipcRenderer.invoke('login', credentials),
    logout: () => electron_1.ipcRenderer.invoke('logout'),
    startTracking: () => electron_1.ipcRenderer.invoke('start-tracking'),
    stopTracking: () => electron_1.ipcRenderer.invoke('stop-tracking'),
    getStatus: () => electron_1.ipcRenderer.invoke('get-status'),
    getAuth: () => electron_1.ipcRenderer.invoke('get-auth'),
});
