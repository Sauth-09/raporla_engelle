/**
 * Page Context Inject Script (inject.js)
 * Based on BlockTube's property interception pattern.
 * Intercepts YouTube's initial data to filter out blocked content.
 */

(function netKalkanInject() {
    'use strict';

    // 1. Read configuration passed from content.js
    const dataNode = document.getElementById('netkalkan-data');
    if (!dataNode) return; // Should not happen

    let configData = {};
    try {
        configData = JSON.parse(dataNode.textContent);
    } catch (e) {
        console.error('[NetKalkan] Error parsing config data');
        return;
    }
    
    // Clean up the node
    dataNode.remove();

    const config = configData.config || {};
    const lists = configData.lists || { blocklist: {}, whitelist: {} };

    // If kill switch is active, abort interception entirely
    if (config.kill_switch_enabled) {
        console.log('[NetKalkan] Kill-Switch ACTIVE. Engine suspended.');
        return;
    }

    console.log('[NetKalkan] Engine active. Blocklists loaded.');

    // Track recently logged videos to avoid duplicate logging in SPAs
    const recentlyLoggedVideos = new Set();

    // 2. Engine Core: Object Property Interception
    // Adapted from BlockTube / uBlock Origin
    const defineProperty = function(chain, cValue, middleware) {
        let aborted = false;
        
        const trapProp = function(owner, prop, configurable, handler) {
            if (handler.init(owner[prop]) === false) return;
            const odesc = Object.getOwnPropertyDescriptor(owner, prop);
            let prevGetter, prevSetter;
            if (odesc instanceof Object) {
                if (odesc.configurable === false) return;
                if (odesc.get instanceof Function) prevGetter = odesc.get;
                if (odesc.set instanceof Function) prevSetter = odesc.set;
            }
            Object.defineProperty(owner, prop, {
                configurable,
                get() {
                    if (prevGetter !== undefined) prevGetter();
                    return handler.getter();
                },
                set(a) {
                    if (prevSetter !== undefined) prevSetter(a);
                    handler.setter(a);
                }
            });
        };

        const trapChain = function(owner, chain) {
            const pos = chain.indexOf('.');
            if (pos === -1) {
                trapProp(owner, chain, true, {
                    v: undefined,
                    init: function(v) { this.v = v; return true; },
                    getter: function() { return cValue; },
                    setter: function(a) {
                        if (middleware instanceof Function) {
                            cValue = a;
                            middleware(a);
                        } else {
                            cValue = a;
                        }
                    }
                });
                return;
            }
            const prop = chain.slice(0, pos);
            const v = owner[prop];
            chain = chain.slice(pos + 1);
            if (v instanceof Object || typeof v === 'object' && v !== null) {
                trapChain(v, chain);
                return;
            }
            trapProp(owner, prop, true, {
                v: undefined,
                init: function(v) { this.v = v; return true; },
                getter: function() { return this.v; },
                setter: function(a) {
                    this.v = a;
                    if (a instanceof Object) trapChain(a, chain);
                }
            });
        };
        trapChain(window, chain);
    };

    // 3. Filtering Logic
    const isWhitelisted = (ytData) => {
        const wl = lists.whitelist;
        if (!wl) return false;

        // Channel ID Whitelist
        if (wl.channel_id && ytData.channelId) {
            if (wl.channel_id.some(w => w.pattern === ytData.channelId)) return true;
        }
        
        return false;
    };

    const isBlocked = (ytData) => {
        const bl = lists.blocklist;
        if (!bl) return false;

        // 1. Channel ID
        if (bl.channel_id && ytData.channelId) {
            if (bl.channel_id.some(b => b.pattern === ytData.channelId)) return true;
        }

        // 2. Video ID
        if (bl.video_id && ytData.videoId) {
            if (bl.video_id.some(b => b.pattern === ytData.videoId)) return true;
        }

        // 3. Keywords & Regex (Title and Channel Name)
        const checkText = (text, ruleList) => {
            if (!text || !ruleList) return false;
            const t = text.toLowerCase();
            return ruleList.some(b => {
                if (b.is_regex) {
                    try { return new RegExp(b.pattern, 'i').test(text); } catch(e) { return false; }
                }
                return t.includes(b.pattern.toLowerCase());
            });
        };

        if (checkText(ytData.title, bl.keyword)) return true;
        if (checkText(ytData.channelName, bl.channel_name)) return true;
        if (checkText(ytData.channelName, bl.keyword)) return true;

        return false;
    };

    // 4. Intercept Player Response (Video Playback)
    const handlePlayerResponse = (playerResponse) => {
        if (!playerResponse || !playerResponse.videoDetails) return;

        const details = playerResponse.videoDetails;
        const ytData = {
            videoId: details.videoId,
            channelId: details.channelId,
            channelName: details.author,
            title: details.title
        };

        // Telemetry Logging
        if (ytData.videoId && !recentlyLoggedVideos.has(ytData.videoId)) {
            recentlyLoggedVideos.add(ytData.videoId);
            if (recentlyLoggedVideos.size > 50) recentlyLoggedVideos.clear(); // Cleanup

            window.dispatchEvent(new CustomEvent('NetKalkanLogActivity', {
                detail: ytData
            }));
        }

        // Blocking
        if (isWhitelisted(ytData)) return; // Pass

        if (isBlocked(ytData)) {
            console.log(`[NetKalkan] Blocked video: ${ytData.title} (${ytData.videoId})`);
            
            // Mutate the player response to show a generic YouTube error state
            const msg = config.block_message || "Bu video kullanılamıyor.";
            
            playerResponse.playabilityStatus = {
                status: 'ERROR',
                reason: msg,
                errorScreen: {
                    playerErrorMessageRenderer: {
                        reason: { simpleText: msg },
                        icon: { iconType: 'ERROR_OUTLINE' }
                    }
                }
            };
            
            // Delete video details to prevent playback
            delete playerResponse.videoDetails;
            if (playerResponse.streamingData) delete playerResponse.streamingData;
        }
    };

    // 5. Deep UI Filtering (Search, Home, Recommendations)
    const RENDERER_KEYS = [
        'videoRenderer', 'gridVideoRenderer', 'compactVideoRenderer',
        'playlistVideoRenderer', 'richItemRenderer', 'channelRenderer',
        'gridChannelRenderer', 'reelItemRenderer'
    ];

    const extractYtData = (rendererData) => {
        const ytData = { videoId: '', title: '', channelName: '', channelId: '' };
        
        if (rendererData.videoId) ytData.videoId = rendererData.videoId;
        if (rendererData.channelId) ytData.channelId = rendererData.channelId;

        // Extract Title
        if (rendererData.title?.runs?.length > 0) {
            ytData.title = rendererData.title.runs.map(r => r.text).join('');
        } else if (rendererData.title?.simpleText) {
            ytData.title = rendererData.title.simpleText;
        } else if (rendererData.headline?.simpleText) { // Shorts
            ytData.title = rendererData.headline.simpleText;
        }

        // Extract Channel
        const owner = rendererData.ownerText || rendererData.shortBylineText || rendererData.longBylineText;
        if (owner?.runs?.length > 0) {
            ytData.channelName = owner.runs[0].text;
            const endpoint = owner.runs[0].navigationEndpoint;
            if (endpoint?.browseEndpoint) {
                ytData.channelId = endpoint.browseEndpoint.browseId;
            }
        }
        
        return ytData;
    };

    const filterYoutubeData = (obj) => {
        if (!obj || typeof obj !== 'object') return false;

        // If array, iterate backwards and splice if child signals deletion
        if (Array.isArray(obj)) {
            for (let i = obj.length - 1; i >= 0; i--) {
                if (filterYoutubeData(obj[i])) {
                    obj.splice(i, 1);
                }
            }
            return false;
        }

        let shouldDelete = false;

        for (const key in obj) {
            if (!obj.hasOwnProperty(key)) continue;

            const child = obj[key];
            if (child && typeof child === 'object') {
                
                // If it's a known renderer wrapper, check its contents
                if (RENDERER_KEYS.includes(key)) {
                    let rendererData = child;
                    
                    // richItemRenderer usually wraps another renderer
                    if (key === 'richItemRenderer' && child.content) {
                        const innerKey = Object.keys(child.content)[0];
                        if (innerKey) rendererData = child.content[innerKey];
                    }

                    const ytData = extractYtData(rendererData);
                    
                    if ((ytData.videoId || ytData.channelId) && !isWhitelisted(ytData) && isBlocked(ytData)) {
                        shouldDelete = true;
                        console.log(`[NetKalkan] Gizlendi: ${ytData.title} (${ytData.videoId || ytData.channelId})`);
                        break; 
                    }
                }

                // Recurse deeper
                if (filterYoutubeData(child)) {
                    delete obj[key];
                }
            }
        }
        
        return shouldDelete;
    };

    // 6. Apply Traps
    
    // Trap Initial Data (Home Page, Search Results, etc.)
    defineProperty('ytInitialData', undefined, (data) => {
        filterYoutubeData(data);
    });

    // Trap Initial Player (Direct Link Navigation)
    defineProperty('ytInitialPlayerResponse', undefined, handlePlayerResponse);

    // Trap fetch/JSON parsing for subsequent SPA navigations
    const originalParse = JSON.parse;
    JSON.parse = function() {
        const result = originalParse.apply(this, arguments);
        
        if (result && typeof result === 'object') {
            if (result.videoDetails && result.playabilityStatus) {
                handlePlayerResponse(result);
            }
            // Filter search results, recommendations, comments etc.
            filterYoutubeData(result);
        }
        return result;
    };

    // Trap modern fetch JSON extraction
    if (window.Response && Response.prototype.json) {
        const origJson = Response.prototype.json;
        Response.prototype.json = function() {
            return origJson.apply(this, arguments).then(result => {
                if (result && typeof result === 'object') {
                    if (result.videoDetails && result.playabilityStatus) {
                        handlePlayerResponse(result);
                    }
                    filterYoutubeData(result);
                }
                return result;
            });
        };
    }
    
    // Trap modern fetch text extraction (sometimes used before JSON.parse)
    if (window.Response && Response.prototype.text) {
        const origText = Response.prototype.text;
        Response.prototype.text = function() {
            return origText.apply(this, arguments).then(result => {
                try {
                    const parsed = JSON.parse(result);
                    if (parsed && typeof parsed === 'object') {
                        if (parsed.videoDetails && parsed.playabilityStatus) {
                            handlePlayerResponse(parsed);
                        }
                        filterYoutubeData(parsed);
                    }
                    return JSON.stringify(parsed);
                } catch(e) {}
                return result;
            });
        };
    }

})();
