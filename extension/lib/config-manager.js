/**
 * Configuration Manager Module
 * Polls the server for configuration and list updates.
 * 
 * Resilience features:
 *  - Heartbeat is sent independently of config/list fetch success.
 *  - Log flush is triggered independently (also by its own alarm).
 *  - Each operation (config, lists, heartbeat, flush) is isolated — 
 *    one failing does NOT prevent the others from running.
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

        // Initialize the independent flush alarm
        await LogBuffer.initFlushAlarm();

        await this.sync();
    }

    /**
     * Synchronize config and lists with the server.
     * Each step is isolated with its own try/catch so that
     * one failure does not block the others.
     */
    static async sync() {
        console.log('[NetKalkan] Syncing with server...');

        // 1. Fetch Config (isolated)
        let configFetched = false;
        try {
            const remoteConfig = await ApiClient.fetchConfig();
            if (remoteConfig) {
                await chrome.storage.local.set({ [this.CONFIG_KEY]: remoteConfig });
                this._updateAlarm(remoteConfig.sync_interval_minutes);
                configFetched = true;
                console.log('[NetKalkan] Config synced successfully.');
            } else {
                console.warn('[NetKalkan] Config fetch returned null — using cached config.');
            }
        } catch (error) {
            console.error('[NetKalkan] Config sync error:', error.message || error);
        }

        // 2. Fetch Lists (isolated, skip if kill switch)
        try {
            const currentConfig = await this.getConfig();
            if (!currentConfig.kill_switch_enabled) {
                const remoteLists = await ApiClient.fetchBlocklist();
                if (remoteLists) {
                    await chrome.storage.local.set({ [this.LISTS_KEY]: remoteLists });
                    console.log('[NetKalkan] Blocklists synced successfully.');
                }
            } else {
                console.log('[NetKalkan] Kill-Switch is ACTIVE. Skipping blocklist fetch.');
            }
        } catch (error) {
            console.error('[NetKalkan] Blocklist sync error:', error.message || error);
        }

        // 3. Heartbeat (isolated — this is the critical one for "online" status)
        try {
            await ApiClient.sendHeartbeat();
        } catch (error) {
            console.error('[NetKalkan] Heartbeat error:', error.message || error);
        }

        // 4. Flush Logs (isolated — also handled by its own alarm)
        try {
            await LogBuffer.flush();
        } catch (error) {
            console.error('[NetKalkan] Log flush error during sync:', error.message || error);
        }

        // Log queue status for diagnostics
        try {
            const queueSize = await LogBuffer.getQueueSize();
            if (queueSize > 0) {
                console.warn(`[NetKalkan] ${queueSize} logs still in queue after sync.`);
            }
        } catch (_) {}
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
