/**
 * Service Worker (Background Script)
 * Manifest V3 entry point. Handles alarms, navigation events, and message routing.
 * 
 * Resilience notes:
 *  - Two independent alarms: 'netkalkan_sync' (config/heartbeat) and 'netkalkan_flush' (log delivery).
 *  - Each alarm handler is wrapped in try/catch to prevent silent failures.
 *  - webNavigation events log page visits even when the service worker was idle.
 */

import { ConfigManager } from './lib/config-manager.js';
import { LogBuffer } from './lib/log-buffer.js';
import { ApiClient } from './lib/api-client.js';

// Initialize on install or startup
chrome.runtime.onInstalled.addListener(() => {
    console.log('[NetKalkan] Extension installed/updated.');
    ConfigManager.init().catch(err => console.error('[NetKalkan] Init error on install:', err));
});

chrome.runtime.onStartup.addListener(() => {
    console.log('[NetKalkan] Browser started.');
    ConfigManager.init().catch(err => console.error('[NetKalkan] Init error on startup:', err));
});

// Handle alarms for periodic sync and flush
chrome.alarms.onAlarm.addListener(async (alarm) => {
    console.log(`[NetKalkan] Alarm fired: ${alarm.name}`);

    if (alarm.name === 'netkalkan_sync') {
        try {
            await ConfigManager.sync();
        } catch (error) {
            console.error('[NetKalkan] Sync alarm handler error:', error);
        }
    }

    if (alarm.name === 'netkalkan_flush') {
        try {
            await LogBuffer.flush();
        } catch (error) {
            console.error('[NetKalkan] Flush alarm handler error:', error);
        }
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
        }).catch(err => {
            console.error('[NetKalkan] Error getting config/lists:', err);
            sendResponse({ config: ConfigManager.DEFAULT_CONFIG, lists: { blocklist: {}, whitelist: {} } });
        });
        return true; // Keep message channel open
    }
    
    if (request.action === 'LOG_ACTIVITY') {
        const logData = request.data;
        // If sender provides a tab URL, use it if none provided
        if (!logData.url && sender.tab) {
            logData.url = sender.tab.url;
        }
        
        LogBuffer.addLog(logData).catch(err => {
            console.error('[NetKalkan] Error adding log from message:', err);
        });
        sendResponse({ success: true });
        return false;
    }

    if (request.action === 'GET_DIAGNOSTICS') {
        // Diagnostic endpoint for troubleshooting
        Promise.all([
            LogBuffer.getQueueSize(),
            ApiClient.getBaseUrl(),
            chrome.storage.local.get('machineId'),
        ]).then(([queueSize, baseUrl, { machineId }]) => {
            sendResponse({
                queueSize,
                baseUrl,
                machineId: machineId || '(not set)',
                timestamp: new Date().toISOString(),
            });
        }).catch(err => {
            sendResponse({ error: err.message });
        });
        return true;
    }
});

// Monitor general web navigation (outside YouTube)
chrome.webNavigation.onCompleted.addListener(async (details) => {
    // Only track main frame navigations, exclude youtube (handled by content script) and extension pages
    if (details.frameId === 0 && 
        !details.url.includes('youtube.com') && 
        !details.url.startsWith('chrome-extension://') &&
        !details.url.startsWith('chrome://') &&
        !details.url.startsWith('edge://') &&
        !details.url.startsWith('about:')) {
        
        // Wait briefly to allow page title to update
        setTimeout(async () => {
            try {
                const tab = await chrome.tabs.get(details.tabId);
                await LogBuffer.addLog({
                    url: tab.url,
                    title: tab.title || '',
                    log_type: 'page_visit',
                    timestamp: new Date().toISOString()
                });
            } catch (e) {
                // Tab might be closed already — this is expected
            }
        }, 2000);
    }
});
