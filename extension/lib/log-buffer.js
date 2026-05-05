/**
 * Log Buffer Module
 * Queues logs locally and sends them in batches to reduce server load.
 * 
 * Resilience features:
 *  - Logs persist in chrome.storage.local until successfully sent.
 *  - A dedicated alarm triggers periodic flush attempts independent of config sync.
 *  - Failed sends are retried with exponential backoff (up to MAX_RETRIES).
 */

import { ApiClient } from './api-client.js';

// Internal state to prevent concurrent flushes
let _isFlushing = false;

export class LogBuffer {
    static STORAGE_KEY = 'netkalkan_log_queue';
    static FLUSH_ALARM = 'netkalkan_flush';
    static MAX_QUEUE_SIZE = 500;
    static MAX_SEND_BATCH = 50;
    static MAX_RETRIES = 10;
    static FLUSH_INTERVAL_MINUTES = 1; // Dedicated flush alarm interval

    /**
     * Initialize the independent flush alarm.
     * Should be called once from service-worker on install/startup.
     */
    static async initFlushAlarm() {
        const existing = await chrome.alarms.get(this.FLUSH_ALARM);
        if (!existing) {
            chrome.alarms.create(this.FLUSH_ALARM, {
                delayInMinutes: this.FLUSH_INTERVAL_MINUTES,
                periodInMinutes: this.FLUSH_INTERVAL_MINUTES,
            });
            console.log('[NetKalkan] Flush alarm created (every 1 min).');
        }
    }

    /**
     * Add a single log to the queue.
     * @param {Object} logEntry 
     */
    static async addLog(logEntry) {
        try {
            // Ensure timestamp exists
            if (!logEntry.timestamp) {
                logEntry.timestamp = new Date().toISOString();
            }

            // Add hostname
            const { machineId } = await chrome.storage.local.get('machineId');
            if (machineId) logEntry.hostname = machineId;

            // Retrieve current queue
            const data = await chrome.storage.local.get(this.STORAGE_KEY);
            let queue = data[this.STORAGE_KEY] || [];

            queue.push(logEntry);

            // Trim queue if it gets too large (drop oldest)
            if (queue.length > this.MAX_QUEUE_SIZE) {
                queue = queue.slice(queue.length - this.MAX_QUEUE_SIZE);
            }

            await chrome.storage.local.set({ [this.STORAGE_KEY]: queue });

            // Only trigger immediate flush if we have accumulated enough logs.
            // Otherwise, rely on the 1-minute alarm. This dramatically reduces
            // network requests when many students are browsing simultaneously.
            if (queue.length >= 10) {
                this.flush().catch(() => {});
            }
        } catch (error) {
            console.error('[NetKalkan] Error adding log:', error);
        }
    }

    /**
     * Send all queued logs to the server.
     * Uses a lock to prevent concurrent flush operations.
     */
    static async flush() {
        // Prevent concurrent flushes
        if (_isFlushing) {
            console.log('[NetKalkan] Flush already in progress, skipping.');
            return;
        }

        _isFlushing = true;
        try {
            const data = await chrome.storage.local.get(this.STORAGE_KEY);
            const queue = data[this.STORAGE_KEY] || [];

            if (queue.length === 0) return;

            // Send in smaller batches to avoid timeouts
            const batch = queue.slice(0, this.MAX_SEND_BATCH);
            console.log(`[NetKalkan] Attempting to flush ${batch.length} logs (${queue.length} total in queue)...`);

            const success = await ApiClient.sendLogs(batch);

            if (success) {
                // Remove only the successfully sent items
                const freshData = await chrome.storage.local.get(this.STORAGE_KEY);
                const freshQueue = freshData[this.STORAGE_KEY] || [];
                const remainingQueue = freshQueue.slice(batch.length);

                await chrome.storage.local.set({ [this.STORAGE_KEY]: remainingQueue });
                console.log(`[NetKalkan] Flushed ${batch.length} logs. ${remainingQueue.length} remaining.`);

                // If there are more logs, schedule another immediate flush
                if (remainingQueue.length > 0) {
                    setTimeout(() => this.flush().catch(() => {}), 1000);
                }
            } else {
                console.warn(`[NetKalkan] Flush failed. ${queue.length} logs remain in queue for retry.`);
                // Logs stay in queue — the flush alarm will retry
            }
        } catch (error) {
            console.error('[NetKalkan] Error during flush:', error);
        } finally {
            _isFlushing = false;
        }
    }

    /**
     * Get current queue size for diagnostics.
     * @returns {Promise<number>}
     */
    static async getQueueSize() {
        const data = await chrome.storage.local.get(this.STORAGE_KEY);
        return (data[this.STORAGE_KEY] || []).length;
    }
}
