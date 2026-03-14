'use client';

import { useEffect } from 'react';

export default function ServiceWorkerRegistration() {
    useEffect(() => {
        if (typeof window === 'undefined' || !('serviceWorker' in navigator)) {
            return;
        }

        // Register service worker after page load for better performance
        window.addEventListener('load', registerSW);

        return () => {
            window.removeEventListener('load', registerSW);
        };
    }, []);

    return null;
}

async function registerSW() {
    try {
        const registration = await navigator.serviceWorker.register('/sw.js', {
            scope: '/',
        });

        // Check for updates periodically (every 60 minutes)
        setInterval(() => {
            registration.update();
        }, 60 * 60 * 1000);
    } catch (error) {
        // Service worker registration failed — non-critical, app works without it
        console.warn('SW registration failed:', error);
    }
}
