/**
 * Browser Notifications for Adobe Digest
 * Manages push notifications for new security bulletins
 */

(function() {
    'use strict';

    const STORAGE_KEY = 'adobeDigestNotifications';
    const LAST_CHECK_KEY = 'adobeDigestLastCheck';
    const CHECK_INTERVAL = 6 * 60 * 60 * 1000; // 6 hours in milliseconds

    class NotificationManager {
        constructor() {
            this.enabled = false;
            this.lastCheck = null;
            this.loadSettings();
        }

        /**
         * Load notification settings from localStorage
         */
        loadSettings() {
            try {
                const stored = localStorage.getItem(STORAGE_KEY);
                if (stored) {
                    const settings = JSON.parse(stored);
                    this.enabled = settings.enabled || false;
                }
                
                const lastCheck = localStorage.getItem(LAST_CHECK_KEY);
                if (lastCheck) {
                    this.lastCheck = parseInt(lastCheck, 10);
                }
            } catch (e) {
                console.error('Failed to load notification settings:', e);
            }
        }

        /**
         * Save notification settings to localStorage
         */
        saveSettings() {
            try {
                localStorage.setItem(STORAGE_KEY, JSON.stringify({
                    enabled: this.enabled
                }));
                if (this.lastCheck) {
                    localStorage.setItem(LAST_CHECK_KEY, this.lastCheck.toString());
                }
            } catch (e) {
                console.error('Failed to save notification settings:', e);
            }
        }

        /**
         * Check if notifications are supported by the browser
         */
        isSupported() {
            return 'Notification' in window;
        }

        /**
         * Get current notification permission status
         */
        getPermission() {
            if (!this.isSupported()) {
                return 'unsupported';
            }
            return Notification.permission;
        }

        /**
         * Request notification permission from the user
         */
        async requestPermission() {
            if (!this.isSupported()) {
                return false;
            }

            if (Notification.permission === 'granted') {
                this.enabled = true;
                this.saveSettings();
                return true;
            }

            if (Notification.permission === 'denied') {
                return false;
            }

            try {
                const permission = await Notification.requestPermission();
                if (permission === 'granted') {
                    this.enabled = true;
                    this.saveSettings();
                    this.showWelcomeNotification();
                    return true;
                }
                return false;
            } catch (e) {
                console.error('Failed to request notification permission:', e);
                return false;
            }
        }

        /**
         * Show a welcome notification after user enables notifications
         */
        showWelcomeNotification() {
            this.showNotification(
                'Adobe Digest Notifications Enabled',
                'You\'ll receive notifications when new security bulletins are posted.',
                '/favicon.ico'
            );
        }

        /**
         * Show a notification
         */
        showNotification(title, body, icon = '/favicon.ico', url = null) {
            if (!this.isSupported() || Notification.permission !== 'granted') {
                return null;
            }

            try {
                const notification = new Notification(title, {
                    body: body,
                    icon: icon,
                    badge: icon,
                    tag: 'adobe-digest',
                    requireInteraction: false,
                    silent: false
                });

                if (url) {
                    notification.onclick = function() {
                        window.open(url, '_blank');
                        notification.close();
                    };
                }

                return notification;
            } catch (e) {
                console.error('Failed to show notification:', e);
                return null;
            }
        }

        /**
         * Disable notifications
         */
        disable() {
            this.enabled = false;
            this.saveSettings();
        }

        /**
         * Check for new bulletins and notify if found
         */
        async checkForUpdates() {
            if (!this.enabled || Notification.permission !== 'granted') {
                return;
            }

            const now = Date.now();
            
            // Don't check too frequently
            if (this.lastCheck && (now - this.lastCheck) < CHECK_INTERVAL) {
                return;
            }

            try {
                // Fetch the RSS feed to check for new bulletins
                const response = await fetch('/feed.json');
                if (!response.ok) {
                    throw new Error('Failed to fetch feed');
                }

                const feed = await response.json();
                
                if (!feed.items || feed.items.length === 0) {
                    this.lastCheck = now;
                    this.saveSettings();
                    return;
                }

                // Get the most recent bulletin
                const latestItem = feed.items[0];
                const latestDate = new Date(latestItem.date_published).getTime();

                // Check if this is newer than our last check
                if (!this.lastCheck || latestDate > this.lastCheck) {
                    // Show notification for the new bulletin
                    this.showNotification(
                        'New Adobe Security Bulletin',
                        latestItem.title,
                        '/favicon.ico',
                        latestItem.url
                    );
                }

                this.lastCheck = now;
                this.saveSettings();
            } catch (e) {
                console.error('Failed to check for updates:', e);
            }
        }

        /**
         * Start periodic checks for new bulletins
         */
        startPeriodicChecks() {
            if (!this.enabled) {
                return;
            }

            // Check immediately
            this.checkForUpdates();

            // Then check periodically
            setInterval(() => {
                this.checkForUpdates();
            }, CHECK_INTERVAL);
        }
    }

    // Create global instance
    window.adobeDigestNotifications = new NotificationManager();

    // Start periodic checks when page loads
    document.addEventListener('DOMContentLoaded', function() {
        if (window.adobeDigestNotifications.enabled) {
            window.adobeDigestNotifications.startPeriodicChecks();
        }
    });

    // Expose utility function to toggle notifications
    window.toggleAdobeDigestNotifications = async function() {
        const manager = window.adobeDigestNotifications;
        
        if (!manager.isSupported()) {
            alert('Notifications are not supported in your browser.');
            return false;
        }

        if (manager.enabled) {
            manager.disable();
            return false;
        } else {
            const granted = await manager.requestPermission();
            if (granted) {
                manager.startPeriodicChecks();
            }
            return granted;
        }
    };

})();
