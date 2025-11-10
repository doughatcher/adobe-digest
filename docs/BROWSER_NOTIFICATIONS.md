# Browser Notifications

Adobe Digest supports browser-based push notifications to alert users when new security bulletins are posted. This feature uses the standard Web Notifications API available in modern browsers.

## Features

- **Real-time Alerts**: Get notified immediately when new security bulletins are published
- **Browser Native**: Uses Chrome, Firefox, Safari, and Edge's built-in notification system
- **Privacy-Focused**: All data stored locally in browser localStorage
- **Periodic Checks**: Automatically checks for new bulletins every 6 hours
- **One-Click Toggle**: Easy enable/disable from the homepage

## User Guide

### Enabling Notifications

1. Visit [adobedigest.com](https://adobedigest.com)
2. Scroll to the "Browser Notifications" section in the footer
3. Click "Enable Notifications"
4. Grant permission when prompted by your browser
5. You'll receive a welcome notification confirming setup

### Disabling Notifications

1. Visit [adobedigest.com](https://adobedigest.com)
2. Scroll to the "Browser Notifications" section
3. Click "Disable Notifications"

### Browser Compatibility

Browser notifications are supported in:
- Chrome 22+
- Firefox 22+
- Safari 16+ (macOS 13+)
- Edge 14+
- Opera 25+

**Note**: Some browsers require HTTPS for notifications to work. The feature is automatically disabled on browsers that don't support it.

## How It Works

### Architecture

```
User enables notifications
    ↓
Permission granted
    ↓
System starts periodic checks (every 6 hours)
    ↓
Fetches /feed.json
    ↓
Compares latest bulletin timestamp with last check
    ↓
If new bulletin found → Display notification
    ↓
Update last check timestamp
```

### Data Storage

The notification system stores minimal data in browser localStorage:

- **adobeDigestNotifications**: User preference (enabled/disabled)
- **adobeDigestLastCheck**: Timestamp of last bulletin check

No data is sent to servers. All checks are performed client-side.

### Privacy & Security

- **No Tracking**: No user data is collected or transmitted
- **Local Only**: All preferences stored in browser localStorage
- **User Control**: Users can disable notifications at any time
- **No Personal Data**: System only stores timestamps and boolean preferences

## Technical Details

### JavaScript API

The notification system exposes a global object `window.adobeDigestNotifications` with the following methods:

```javascript
// Check if notifications are supported
const isSupported = window.adobeDigestNotifications.isSupported();

// Get current permission status
const permission = window.adobeDigestNotifications.getPermission();
// Returns: 'granted', 'denied', 'default', or 'unsupported'

// Request permission
const granted = await window.adobeDigestNotifications.requestPermission();

// Disable notifications
window.adobeDigestNotifications.disable();

// Manually check for updates
await window.adobeDigestNotifications.checkForUpdates();

// Start periodic checks
window.adobeDigestNotifications.startPeriodicChecks();
```

### Notification Format

When a new bulletin is detected, the notification displays:

- **Title**: "New Adobe Security Bulletin"
- **Body**: The bulletin title (e.g., "APSB25-01 Security update for Adobe Commerce")
- **Icon**: Adobe Digest favicon
- **Click Action**: Opens the bulletin page in a new tab

### Check Interval

The system checks for new bulletins every 6 hours to match the scraper's update schedule. This interval is configurable in `/static/js/notifications.js`:

```javascript
const CHECK_INTERVAL = 6 * 60 * 60 * 1000; // 6 hours in milliseconds
```

## Development

### File Structure

```
static/js/notifications.js          # Main notification manager
layouts/partials/head.html          # Includes notification script
layouts/index.html                  # Notification toggle UI
```

### Testing

To test notifications locally:

1. Serve the site (e.g., with Hugo or a static server)
2. Enable notifications through the UI
3. Modify the CHECK_INTERVAL in notifications.js to a shorter duration (e.g., 30 seconds) for testing
4. Update /feed.json with a new bulletin
5. Wait for the check interval to trigger
6. Verify notification appears

### Debugging

Enable console logging by opening your browser's developer tools. The notification manager logs:

- Permission request results
- Update check attempts
- Notification display events
- Error messages

## Future Enhancements

Potential improvements for the notification system:

- [ ] Custom notification sounds
- [ ] Notification filtering by product (Adobe Commerce, AEM, etc.)
- [ ] Severity-based notifications (critical vs. informational)
- [ ] Notification history viewer
- [ ] Service Worker for background updates
- [ ] Push notification server for instant delivery

## Troubleshooting

### Notifications Not Working

1. **Check browser support**: Open developer console and run:
   ```javascript
   'Notification' in window
   ```

2. **Check permission status**:
   ```javascript
   Notification.permission
   ```

3. **Check if enabled**:
   ```javascript
   localStorage.getItem('adobeDigestNotifications')
   ```

4. **Verify HTTPS**: Some browsers require HTTPS for notifications

5. **Clear localStorage and retry**:
   ```javascript
   localStorage.removeItem('adobeDigestNotifications');
   localStorage.removeItem('adobeDigestLastCheck');
   ```

### Permission Denied

If you accidentally denied permission:

1. Click the lock/info icon in your browser's address bar
2. Find "Notifications" in the permissions list
3. Change from "Block" to "Allow"
4. Refresh the page and try again

## Contributing

To contribute improvements to the notification system:

1. Fork the repository
2. Make your changes to `/static/js/notifications.js`
3. Test thoroughly across different browsers
4. Submit a pull request with a clear description

## License

The notification system is part of Adobe Digest and is released under the MIT License. See [LICENSE](../LICENSE) for details.
