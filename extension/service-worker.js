/**
 * Service Worker (Background Script)
 * Manifest V3 entry point. Handles alarms, navigation events, and message routing.
 */

import { ConfigManager } from './lib/config-manager.js';
import { LogBuffer } from './lib/log-buffer.js';
import { ApiClient } from './lib/api-client.js';

// Initialize on install or startup
chrome.runtime.onInstalled.addListener(() => {
    console.log('[NetKalkan] Extension installed/updated.');
    ConfigManager.init();
});

chrome.runtime.onStartup.addListener(() => {
    console.log('[NetKalkan] Browser started.');
    ConfigManager.init();
});

// Handle alarms for periodic sync
chrome.alarms.onAlarm.addListener((alarm) => {
    if (alarm.name === 'netkalkan_sync') {
        ConfigManager.sync();
    }
});

// Handle messages from content scripts
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'GET_CONFIG_AND_LISTS') {
        // Return config and lists asynchronously
        Promise.all([
            ConfigManager.getConfig(),
            ConfigManager.getLists()
        ]).then(([config, lists]) => {
            sendResponse({ config, lists });
        });
        return true; // Keep message channel open
    }
    
    if (request.action === 'LOG_ACTIVITY') {
        const logData = request.data;
        // If sender provides a tab URL, use it if none provided
        if (!logData.url && sender.tab) {
            logData.url = sender.tab.url;
        }
        
        LogBuffer.addLog(logData);
        sendResponse({ success: true });
        return false;
    }
});

// Monitor general web navigation (outside YouTube)
chrome.webNavigation.onCompleted.addListener(async (details) => {
    // Only track main frame navigations, exclude youtube (handled by content script) and extension pages
    if (details.frameId === 0 && 
        !details.url.includes('youtube.com') && 
        !details.url.startsWith('chrome-extension://') &&
        !details.url.startsWith('chrome://')) {
        
        // Wait briefly to allow page title to update
        setTimeout(async () => {
            try {
                const tab = await chrome.tabs.get(details.tabId);
                LogBuffer.addLog({
                    url: tab.url,
                    title: tab.title || '',
                    log_type: 'page_visit',
                    timestamp: new Date().toISOString()
                });
            } catch (e) {
                // Tab might be closed already
            }
        }, 2000);
    }
});
