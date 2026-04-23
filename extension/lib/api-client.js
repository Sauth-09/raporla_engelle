/**
 * API Client Module
 * Handles all communication with the Flask backend server.
 */

export class ApiClient {
    /**
     * Sunucu URL'sini ayarlardan getirir.
     * @returns {Promise<string>} API Base URL
     */
    static async getBaseUrl() {
        const { serverUrl } = await chrome.storage.local.get({ serverUrl: 'http://localhost:5000' });
        const url = serverUrl || 'http://localhost:5000';
        return `${url.replace(/\/+$/, '')}/api`;
    }

    /**
     * Send a batch of logs to the server.
     * @param {Array} logs - Array of log objects
     * @returns {Promise<boolean>} - Success status
     */
    static async sendLogs(logs) {
        if (!logs || logs.length === 0) return true;
        
        try {
            const baseUrl = await this.getBaseUrl();
            const response = await fetch(`${baseUrl}/logs`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ logs })
            });
            
            if (!response.ok) {
                console.error(`[NetKalkan] Server returned ${response.status} for logs`);
                return false;
            }
            return true;
        } catch (error) {
            console.error('[NetKalkan] Error sending logs:', error);
            return false;
        }
    }

    /**
     * Fetch the latest configuration from the server.
     * @returns {Promise<Object|null>} - Configuration object or null on error
     */
    static async fetchConfig() {
        try {
            const baseUrl = await this.getBaseUrl();
            const response = await fetch(`${baseUrl}/config`, {
                method: 'GET',
                cache: 'no-cache'
            });
            
            if (!response.ok) return null;
            return await response.json();
        } catch (error) {
            console.error('[NetKalkan] Error fetching config:', error);
            return null;
        }
    }

    /**
     * Fetch the latest blocklist and whitelist from the server.
     * @returns {Promise<Object|null>} - Lists object or null on error
     */
    static async fetchBlocklist() {
        try {
            const baseUrl = await this.getBaseUrl();
            const response = await fetch(`${baseUrl}/blocklist`, {
                method: 'GET',
                cache: 'no-cache'
            });
            
            if (!response.ok) return null;
            return await response.json();
        } catch (error) {
            console.error('[NetKalkan] Error fetching blocklist:', error);
            return null;
        }
    }

    /**
     * Send a heartbeat to register this device as online.
     * @returns {Promise<boolean>}
     */
    static async sendHeartbeat() {
        try {
            // Get machine hostname if possible via Chrome APIs or generate a random ID
            const { machineId } = await chrome.storage.local.get('machineId');
            let hostname = machineId;
            
            if (!hostname) {
                hostname = 'PC-' + Math.floor(Math.random() * 10000);
                await chrome.storage.local.set({ machineId: hostname });
            }
            
            const baseUrl = await this.getBaseUrl();
            const response = await fetch(`${baseUrl}/heartbeat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ hostname })
            });
            
            return response.ok;
        } catch (error) {
            // Heartbeat failure is non-critical
            return false;
        }
    }
}
