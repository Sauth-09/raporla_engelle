/**
 * Content Script (content.js)
 * Injected into YouTube pages at document_start.
 * Bridges communication between the page context (inject.js) and the background service worker.
 */

// 1. Fetch config and lists from background script
chrome.runtime.sendMessage({ action: 'GET_CONFIG_AND_LISTS' }, (response) => {
    if (!response) return;
    
    const { config, lists } = response;
    
    // 2. Pass data to page context securely
    // We create a hidden script tag with the data as JSON, which inject.js will read and then delete
    const dataNode = document.createElement('script');
    dataNode.id = 'netkalkan-data';
    dataNode.type = 'application/json';
    dataNode.textContent = JSON.stringify({ config, lists });
    (document.head || document.documentElement).appendChild(dataNode);
    
    // 3. Inject the actual filtering engine (inject.js)
    const scriptNode = document.createElement('script');
    scriptNode.src = chrome.runtime.getURL('scripts/inject.js');
    scriptNode.onload = function() {
        this.remove(); // Clean up script tag after execution
    };
    (document.head || document.documentElement).appendChild(scriptNode);
});

const recentlyLogged = new Set();

// 4. Listen for logging events from inject.js
window.addEventListener('NetKalkanLogActivity', (event) => {
    const raw = event.detail;
    
    // Map camelCase keys from inject.js → snake_case keys expected by the server API
    const logData = {
        url: window.location.href,
        title: raw.title,
        video_id: raw.videoId,
        channel_name: raw.channelName,
        channel_id: raw.channelId,
        log_type: 'youtube_video'
    };
    
    if (logData.video_id) {
        recentlyLogged.add(logData.video_id);
        if (recentlyLogged.size > 50) recentlyLogged.clear();
    }
    
    // Send to background for batching
    chrome.runtime.sendMessage({ 
        action: 'LOG_ACTIVITY', 
        data: logData 
    });
});

// 5. Track SPA Navigations on YouTube (yt-navigate-finish)
// YouTube doesn't reload the page, so we need to track URL changes
document.addEventListener('yt-navigate-finish', () => {
    const isWatch = window.location.pathname.startsWith('/watch');
    
    if (!isWatch) {
        chrome.runtime.sendMessage({ 
            action: 'LOG_ACTIVITY', 
            data: {
                url: window.location.href,
                title: document.title || 'YouTube',
                log_type: 'page_visit'
            }
        });
        return;
    }

    const urlParams = new URLSearchParams(window.location.search);
    const videoId = urlParams.get('v');
    
    if (recentlyLogged.has(videoId)) return; // Already logged by inject.js
    
    // For videos, wait a bit for the player data to load to get accurate channel name
    let attempts = 0;
    const checkPlayer = setInterval(() => {
        attempts++;
        const player = document.querySelector('#movie_player');
        
        if (player && typeof player.getVideoData === 'function') {
            const data = player.getVideoData();
            // Ensure we are logging the correct video
            if (data && data.video_id === videoId) {
                clearInterval(checkPlayer);
                
                if (!recentlyLogged.has(videoId)) {
                    recentlyLogged.add(videoId);
                    if (recentlyLogged.size > 50) recentlyLogged.clear();
                    
                    chrome.runtime.sendMessage({ 
                        action: 'LOG_ACTIVITY', 
                        data: {
                            url: window.location.href,
                            title: data.title || document.title,
                            video_id: data.video_id,
                            channel_name: data.author,
                            log_type: 'youtube_video'
                        }
                    });
                }
                return;
            }
        }
        
        // Fallback if player data not found after 10 attempts (5 seconds)
        if (attempts > 10) {
            clearInterval(checkPlayer);
            if (!recentlyLogged.has(videoId)) {
                recentlyLogged.add(videoId);
                if (recentlyLogged.size > 50) recentlyLogged.clear();
                
                chrome.runtime.sendMessage({ 
                    action: 'LOG_ACTIVITY', 
                    data: {
                        url: window.location.href,
                        title: document.title || 'YouTube Video',
                        video_id: videoId,
                        log_type: 'youtube_video'
                    }
                });
            }
        }
    }, 500);
});
