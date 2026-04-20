/**
 * Log Buffer Module
 * Queues logs locally and sends them in batches to reduce server load.
 */

import { ApiClient } from './api-client.js';

export class LogBuffer {
    static STORAGE_KEY = 'netkalkan_log_queue';
    static MAX_QUEUE_SIZE = 500;
    static BATCH_SEND_THRESHOLD = 1;

    /**
     * Add a single log to the queue.
     * @param {Object} logEntry 
     */
    static async addLog(logEntry) {
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
        
        // Send immediately if threshold reached
        if (queue.length >= this.BATCH_SEND_THRESHOLD) {
            await this.flush();
        }
    }

    /**
     * Send all queued logs to the server.
     */
    static async flush() {
        const data = await chrome.storage.local.get(this.STORAGE_KEY);
        const queue = data[this.STORAGE_KEY] || [];
        
        if (queue.length === 0) return;
        
        const success = await ApiClient.sendLogs(queue);
        
        if (success) {
            // Clear sent logs from queue. We read again just in case new logs
            // were added while we were sending.
            const freshData = await chrome.storage.local.get(this.STORAGE_KEY);
            const freshQueue = freshData[this.STORAGE_KEY] || [];
            const remainingQueue = freshQueue.slice(queue.length);
            
            await chrome.storage.local.set({ [this.STORAGE_KEY]: remainingQueue });
            console.log(`[NetKalkan] Successfully flushed ${queue.length} logs.`);
        }
    }
}
