/**
 * Jeba Enterprise Landing Page Script (v3.0 - Bulletproof)
 * Optimized for Mobile Performance & Reliability
 */

// --- 0. SAFETY FIRST: Anti-Disappear Guard-Rail ---
(function forceVisibilityFallback() {
    // If GSAP crashes, network fails, or script hangs,
    // this ensures the site becomes visible after 3 seconds.
    setTimeout(() => {
        document.body.classList.add('js-ready');
        document.querySelectorAll('.gs-reveal, .gs-scale, .gs-up').forEach(el => {
            el.style.opacity = '1';
            el.style.visibility = 'visible';
            el.style.transform = 'none';
        });
        
        // Kill loader if stuck
        const loader = document.getElementById('site-loader');
        if (loader && loader.style.display !== 'none') {
            loader.style.display = 'none';
            document.getElementById('landing-wrapper').style.opacity = '1';
        }
    }, 3000);
})();

// --- CORE INIT ---
document.addEventListener("DOMContentLoaded", () => {
    // 1. Immediate UI Unblock
    revealSite();
    
    // 2. Initialize Theme
    initTheme();

    // 3. Initialize Logic
    initVariationLogic();
    
    // 4. Native Island Bar (Zero-Dependency)
    initIslandLogic();

    // 5. Desktop Animations (Safe Mode)
    if (window.innerWidth > 768 && typeof gsap !== 'undefined') {
        initDesktopAnimations();
    }
});

// --- 1. VISIBILITY & LOADER ---
function revealSite() {
    const loader = document.getElementById('site-loader');
    const wrapper = document.getElementById('landing-wrapper');
    
    if (wrapper) wrapper.style.opacity = '1';
    
    if (loader) {
        loader.style.opacity = '0';
        setTimeout(() => loader.style.display = 'none', 500);
    }
}

// --- 2. ISLAND BAR (SUPER RELIABLE NATIVE OBSERVER) ---
function initIslandLogic() {
    const hero = document.getElementById('hero-trigger');
    const island = document.getElementById('island-bar');
    
    if (!hero || !island) return;

    // The Observer watches the HERO section.
    // When Hero is NOT intersecting (meaning it scrolled out of view), show Island.
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            // entry.boundingClientRect.top < 0 means we scrolled DOWN past it
            if (!entry.isIntersecting && entry.boundingClientRect.top < 0) {
                island.classList.add('visible');
            } else {
                island.classList.remove('visible');
            }
        });
    }, {
        root: null, // viewport
        threshold: 0, // trigger as soon as 1 pixel leaves
        rootMargin: "-100px 0px 0px 0px" // Offset slightly so it doesn't flicker at the exact edge
    });

    observer.observe(hero);
}

// --- 3. THEME ENGINE ---
function initTheme() {
    const savedTheme = localStorage.getItem('jeba_theme');
    if (savedTheme === 'dark') {
        document.body.setAttribute('data-theme', 'dark');
        const btn = document.querySelector('#theme-btn i');
        if(btn) { btn.classList.remove('fa-moon'); btn.classList.add('fa-sun'); }
    }
}

function toggleTheme() {
    const body = document.body;
    const icon = document.querySelector('#theme-btn i');
    const hint = document.getElementById('theme-hint');
    if (hint) hint.remove();

    if (body.getAttribute('data-theme') === 'dark') {
        body.removeAttribute('data-theme');
        if(icon) { icon.classList.remove('fa-sun'); icon.classList.add('fa-moon'); }
        localStorage.setItem('jeba_theme', 'light');
    } else {
        body.setAttribute('data-theme', 'dark');
        if(icon) { icon.classList.remove('fa-moon'); icon.classList.add('fa-sun'); }
        localStorage.setItem('jeba_theme', 'dark');
    }
}

// --- 4. FORM & VARIATION LOGIC ---
function initVariationLogic() {
    if (typeof VARIATIONS !== 'undefined') {
        const keys = Object.keys(VARIATIONS);
        if (keys.length > 0) selectVariation(keys[0], null);
    }
}

function selectVariation(varId, element) {
    if (typeof VARIATIONS === 'undefined' || !VARIATIONS[varId]) return;
    const data = VARIATIONS[varId];

    document.querySelectorAll('.var-option').forEach(el => {
        el.classList.toggle('active', el.dataset.id === varId);
    });

    ['form-variation-id', 'form-variation-id-mob', 'island-variation-input'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = varId;
    });

    updatePrice(data.price, data.original, data.has_discount);
    if (data.image) {
        ['hero-main-image', 'hero-main-image-mobile', 'island-thumb'].forEach(id => {
            const img = document.getElementById(id);
            if (img) img.src = data.image;
        });
    }
}

function updatePrice(price, original, hasDiscount) {
    const fmt = (n) => "৳" + parseInt(n);
    const update = (valId, strikeId, val, strike, showStrike) => {
        const vEl = document.getElementById(valId);
        const sEl = document.getElementById(strikeId);
        if(vEl) vEl.innerText = val;
        if(sEl) {
            sEl.innerText = strike;
            sEl.classList.toggle('d-none', !showStrike);
            if(strikeId === 'island-strike') sEl.style.display = showStrike ? 'inline' : 'none';
        }
    };

    const p = fmt(price);
    const o = fmt(original);

    update('hero-price-val', 'hero-price-strike', p, o, hasDiscount);
    update('hero-price-val-mob', 'hero-price-strike-mob', p, o, hasDiscount);
    update('island-price', 'island-strike', p, o, hasDiscount);
}

function handleSubmit(form) {
    const btn = form.querySelector('button[type="submit"]');
    if (btn) {
        if (!btn.dataset.originalText) btn.dataset.originalText = btn.innerText;
        btn.style.opacity = '0.7';
        btn.innerText = 'Wait...';
        setTimeout(() => btn.disabled = true, 50);
    }
}

// --- 5. DESKTOP ANIMATIONS (Safe GSAP) ---
function initDesktopAnimations() {
    gsap.registerPlugin(ScrollTrigger);
    
    // We animate FROM opacity 0.
    // CSS sets them to opacity 1 by default (safe).
    // GSAP immediately snaps them to 0 and animates to 1.
    // If GSAP fails, they stay at 1. Perfect.
    
    gsap.utils.toArray('.gs-reveal').forEach(el => {
        gsap.from(el.children, { 
            scrollTrigger: { trigger: el, start: "top 85%" }, 
            y: 30, opacity: 0, duration: 0.6, stagger: 0.1, clearProps: "all" 
        });
    });

    gsap.utils.toArray('.gs-scale').forEach(el => {
        gsap.from(el, { 
            scrollTrigger: { trigger: el, start: "top 90%" }, 
            scale: 0.95, opacity: 0, duration: 0.8, clearProps: "all" 
        });
    });
}

// Global Restore (Back Button Cache)
window.addEventListener('pageshow', (e) => {
    if (e.persisted) {
        document.querySelectorAll('button[type="submit"]').forEach(btn => {
            btn.disabled = false;
            btn.style.opacity = "1";
            if (btn.dataset.originalText) btn.innerText = btn.dataset.originalText;
        });
    }
});