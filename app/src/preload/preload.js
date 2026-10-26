// Безопасный мост между renderer и main (contextIsolation)
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('gameAPI', {
  toggleFullscreen: () => ipcRenderer.send('toggle-fullscreen'),
  platform: process.platform,
  version: '0.1.0'
});
