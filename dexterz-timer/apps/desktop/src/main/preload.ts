import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('electronAPI', {
  login: (credentials: { email: string; password: string }) =>
    ipcRenderer.invoke('login', credentials),
  logout: () => ipcRenderer.invoke('logout'),
  startTracking: () => ipcRenderer.invoke('start-tracking'),
  stopTracking: () => ipcRenderer.invoke('stop-tracking'),
  getStatus: () => ipcRenderer.invoke('get-status'),
  getAuth: () => ipcRenderer.invoke('get-auth'),
  getOrganization: () => ipcRenderer.invoke('get-organization'),
  getSchedule: () => ipcRenderer.invoke('get-schedule'),
})
