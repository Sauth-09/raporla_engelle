/**
 * API Client Module
 * Handles all communication with the Flask backend server.
 * 
 * Resilience features:
 *  - Configurable request timeout to avoid hanging connections.
 *  - Detailed error logging for debugging network issues.
 */

export class ApiClient {
    static REQUEST_TIMEOUT_MS = 15000; // 15 seconds timeout

    /**
     * Get the server base URL from settings.
     * @returns {Promise<string>} API Base URL
     */
    static async getBaseUrl() {
        const { serverUrl } = await chrome.storage.local.get({ serverUrl: 'http://localhost:8080' });
        const url = serverUrl || 'http://localhost:8080';
        return `${url.replace(/\/+$/, '')}/api`;
    }

    /**
     * Perform a fetch with a timeout.
     * @param {string} url 
     * @param {RequestInit} options 
     * @returns {Promise<Response>}
     */
    static async _fetchWithTimeout(url, options = {}) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.REQUEST_TIMEOUT_MS);

        try {
            const response = await fetch(url, {
                ...options,
                signal: controller.signal,
            });
            return response;
        } finally {
            clearTimeout(timeoutId);
        }
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
            const response = await this._fetchWithTimeout(`${baseUrl}/logs`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ logs })
            });

            if (!response.ok) {
                const body = await response.text().catch(() => '');
                console.error(`[NetKalkan] Server returned ${response.status} for logs: ${body}`);
                return false;
            }
            return true;
        } catch (error) {
            if (error.name === 'AbortError') {
                console.error('[NetKalkan] Log send timed out after', this.REQUEST_TIMEOUT_MS, 'ms');
            } else {
                console.error('[NetKalkan] Error sending logs:', error.message || error);
            }
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
            const response = await this._fetchWithTimeout(`${baseUrl}/config`, {
                method: 'GET',
                cache: 'no-cache'
            });

            if (!response.ok) return null;
            return await response.json();
        } catch (error) {
            if (error.name === 'AbortError') {
                console.error('[NetKalkan] Config fetch timed out');
            } else {
                console.error('[NetKalkan] Error fetching config:', error.message || error);
            }
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
            const response = await this._fetchWithTimeout(`${baseUrl}/blocklist`, {
                method: 'GET',
                cache: 'no-cache'
            });

            if (!response.ok) return null;
            return await response.json();
        } catch (error) {
            if (error.name === 'AbortError') {
                console.error('[NetKalkan] Blocklist fetch timed out');
            } else {
                console.error('[NetKalkan] Error fetching blocklist:', error.message || error);
            }
            return null;
        }
    }

    /**
     * Send a heartbeat to register this device as online.
     * @returns {Promise<boolean>}
     */
    static async sendHeartbeat() {
        try {
            // Get machine hostname
            const { machineId } = await chrome.storage.local.get('machineId');
            let hostname = machineId;

            if (!hostname) {
                hostname = 'PC-' + Math.floor(Math.random() * 10000);
                await chrome.storage.local.set({ machineId: hostname });
            }

            const baseUrl = await this.getBaseUrl();
            const response = await this._fetchWithTimeout(`${baseUrl}/heartbeat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ hostname })
            });

            if (response.ok) {
                console.log(`[NetKalkan] Heartbeat sent successfully for ${hostname}`);
            }
            return response.ok;
        } catch (error) {
            // Heartbeat failure is non-critical but we log it for debugging
            console.warn('[NetKalkan] Heartbeat failed:', error.message || error);
            return false;
        }
    }
}
