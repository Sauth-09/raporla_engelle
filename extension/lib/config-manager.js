/**
 * Configuration Manager Module
 * Polls the server for configuration and list updates.
 */

import { ApiClient } from './api-client.js';
import { LogBuffer } from './log-buffer.js';

export class ConfigManager {
    static CONFIG_KEY = 'netkalkan_config';
    static LISTS_KEY = 'netkalkan_lists';
    
    // Default config fallback
    static DEFAULT_CONFIG = {
        sync_interval_minutes: 5,
        kill_switch_enabled: false,
        block_message: "Bu video kullanılamıyor."
    };

    /**
     * Initialize the configuration manager and perform first sync.
     */
    static async init() {
        // Ensure default config exists
        const data = await chrome.storage.local.get(this.CONFIG_KEY);
        if (!data[this.CONFIG_KEY]) {
            await chrome.storage.local.set({ [this.CONFIG_KEY]: this.DEFAULT_CONFIG });
        }
        
        await this.sync();
    }

    /**
     * Synchronize config and lists with the server.
     */
    static async sync() {
        console.log('[NetKalkan] Syncing with server...');
        
        // 1. Fetch Config
        const remoteConfig = await ApiClient.fetchConfig();
        if (remoteConfig) {
            await chrome.storage.local.set({ [this.CONFIG_KEY]: remoteConfig });
            this._updateAlarm(remoteConfig.sync_interval_minutes);
            
            // If kill switch is enabled, we don't need to fetch lists
            if (remoteConfig.kill_switch_enabled) {
                console.log('[NetKalkan] Kill-Switch is ACTIVE. Suspending blocking.');
                return;
            }
        }
        
        // 2. Fetch Lists
        const currentConfig = await this.getConfig();
        if (!currentConfig.kill_switch_enabled) {
            const remoteLists = await ApiClient.fetchBlocklist();
            if (remoteLists) {
                await chrome.storage.local.set({ [this.LISTS_KEY]: remoteLists });
            }
        }
        
        // 3. Heartbeat & Flush Logs
        await ApiClient.sendHeartbeat();
        await LogBuffer.flush();
    }

    /**
     * Get the current active configuration.
     */
    static async getConfig() {
        const data = await chrome.storage.local.get(this.CONFIG_KEY);
        return data[this.CONFIG_KEY] || this.DEFAULT_CONFIG;
    }

    /**
     * Get the current active blocklist/whitelist.
     */
    static async getLists() {
        const data = await chrome.storage.local.get(this.LISTS_KEY);
        return data[this.LISTS_KEY] || { blocklist: {}, whitelist: {} };
    }

    /**
     * Update the background sync alarm.
     */
    static async _updateAlarm(minutes) {
        const ALARM_NAME = 'netkalkan_sync';
        const interval = Math.max(1, minutes || 5); // Minimum 1 minute
        
        const alarm = await chrome.alarms.get(ALARM_NAME);
        if (!alarm || alarm.periodInMinutes !== interval) {
            chrome.alarms.create(ALARM_NAME, { periodInMinutes: interval });
            console.log(`[NetKalkan] Sync alarm set to ${interval} minutes.`);
        }
    }
}
