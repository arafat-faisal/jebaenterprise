/**
 * JEBA HIGH-FREQUENCY LANDING ANALYTICS (HFLA)
 * "The Black Box" Flight Recorder
 * * Objectives:
 * 1. Zero blocking overhead (Async/Beacon).
 * 2. millisecond-level precision on load times.
 * 3. Capture "Ghost Visits" (user bounces < 1s).
 * 4. Track Scroll Heatmap & Rage Clicks.
 */

(function() {
    'use strict';

    // --- 1. CONFIGURATION & STATE ---
    const CONFIG = {
        ingestUrl: '/analytics/ingest-beacon/', // Endpoint we will create in Step 2
        batchDelay: 3000, // Send data every 3s if active
        minScrollUpdate: 5, // Only track 5% increments
    };

    let sessionState = {
        sessionId: generateUUID(),
        startTime: Date.now(),
        maxScroll: 0,
        interactions: [],
        performance: {},
        isBounce: true
    };

    // --- 2. UTILS ---
    function generateUUID() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    // --- 3. PERFORMANCE PROBE ---
    function capturePerformanceMetrics() {
        if (window.performance) {
            const navEntry = performance.getEntriesByType("navigation")[0];
            const paintEntries = performance.getEntriesByType("paint");
            
            if (navEntry) {
                sessionState.performance.ttfb = Math.round(navEntry.responseStart - navEntry.requestStart);
                sessionState.performance.domReady = Math.round(navEntry.domContentLoadedEventEnd - navEntry.startTime);
                sessionState.performance.fullLoad = Math.round(navEntry.loadEventEnd - navEntry.startTime);
            }

            // First Contentful Paint (Visual Load)
            const fcp = paintEntries.find(entry => entry.name === 'first-contentful-paint');
            if (fcp) {
                sessionState.performance.fcp = Math.round(fcp.startTime);
            }
        }
    }

    // --- 4. INTERACTION TRACKERS ---
    
    // A. Click Tracker (Rage Clicks & CTAs)
    document.addEventListener('click', (e) => {
        sessionState.isBounce = false; // Interact = Not a bounce
        
        const target = e.target.closest('a, button, .clickable, input, select');
        const elementId = e.target.id || (target ? target.id : null) || 'anonymous';
        const tag = e.target.tagName;
        const text = (e.target.innerText || '').slice(0, 30);
        
        sessionState.interactions.push({
            type: 'CLICK',
            element: tag,
            id: elementId,
            text: text,
            time: Date.now() - sessionState.startTime,
            x: e.clientX,
            y: e.clientY
        });
    });

    // B. Scroll Tracker (Heatmap)
    let scrollTimeout;
    window.addEventListener('scroll', () => {
        if (scrollTimeout) return;
        
        scrollTimeout = setTimeout(() => {
            const scrollTop = window.scrollY || document.documentElement.scrollTop;
            const docHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight;
            const scrollPercent = Math.round((scrollTop / docHeight) * 100);

            if (scrollPercent > sessionState.maxScroll) {
                sessionState.maxScroll = scrollPercent;
                // Interaction if they scroll past 25%
                if (sessionState.maxScroll > 25) sessionState.isBounce = false;
            }
            scrollTimeout = null;
        }, 250); // Throttle 250ms
    });

    // --- 5. TRANSMISSION ENGINE (The Beacon) ---
    function sendTelem(isFinal = false) {
        // Gather latest perf metrics if not yet captured
        if (Object.keys(sessionState.performance).length === 0) {
            capturePerformanceMetrics();
        }

        const payload = new FormData();
        payload.append('session_id', sessionState.sessionId);
        payload.append('url', window.location.pathname);
        payload.append('timestamp', new Date().toISOString());
        payload.append('is_final', isFinal);
        
        // Data Payload
        const data = {
            duration: Date.now() - sessionState.startTime,
            performance: sessionState.performance,
            max_scroll: sessionState.maxScroll,
            interactions: sessionState.interactions,
            is_bounce: sessionState.isBounce,
            screen_width: window.innerWidth,
            user_agent: navigator.userAgent
        };
        
        payload.append('data', JSON.stringify(data));

        // Use Beacon API for reliability during unload
        if (navigator.sendBeacon) {
            const status = navigator.sendBeacon(CONFIG.ingestUrl, payload);
            if (!status && !isFinal) {
                 // Fallback to XHR if beacon fails and not unloading
                 // (Rare, but good redundancy)
                 const xhr = new XMLHttpRequest();
                 xhr.open('POST', CONFIG.ingestUrl);
                 xhr.send(payload);
            }
        } else {
            // Legacy Fallback
            const xhr = new XMLHttpRequest();
            xhr.open('POST', CONFIG.ingestUrl, false); // synchronous for final
            xhr.send(payload);
        }

        // Clear flushed interactions to save bandwidth
        if (!isFinal) {
            sessionState.interactions = [];
        }
    }

    // --- 6. TRIGGERS ---
    
    // Heartbeat (every 5 seconds) to track "Time on Page" accurately
    setInterval(() => sendTelem(false), 5000);

    // Visibility Change (Tab Switch / Mobile Minimize)
    document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === 'hidden') {
            sendTelem(false);
        }
    });

    // Page Unload (The End)
    window.addEventListener("pagehide", () => {
        sendTelem(true);
    });

    console.log("Jeba Analytics: Probe Active 🟢");

})();