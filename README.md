# DroidBox — Stealth Android Container

A custom, high-performance Android container system designed for stealth and indistinguishable device identity.

## Features
- **Redmi 9 (lancelot) Identity**: Injects real build properties, locked bootloader, and green verified boot status.
- **GTK3 Installer**: Easy deployment with root password authentication and progress tracking.
- **GTK3 Launcher**: Beautiful dashboard with Start/Stop controls, live log streaming, and device status.
- **Wayland Support**: Seamless display integration on modern Linux desktops.
- **No Waydroid**: Fully independent LXC-based implementation.

## How to Install
1.  Run the installer:
    ```bash
    python3 installer.py
    ```
2.  Authorize and follow the on-screen instructions.

## How to Run
- Launch the **My Android** app from your desktop menu.
- Or run manually:
    ```bash
    python3 /opt/my-android/launcher.py
    ```

## Stealth Properties
- `ro.secure=1`
- `ro.debuggable=0`
- `ro.boot.verifiedbootstate=green`
- `ro.boot.flash.locked=1`
- `ro.build.product=lancelot`
