#!/usr/bin/env python3
"""
My Android Container - GTK3 Installer
Installs the custom Android container environment.
"""
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk, Pango, GdkPixbuf
import subprocess
import os
import sys
import shutil
import threading

# ─── Paths ────────────────────────────────────────────────────────────────
SOURCE_DIR = "/home/kali/İndirilenler/sondosyavendor"
INSTALL_DIR = "/opt/my-android"
IMAGES_DIR = os.path.join(INSTALL_DIR, "images")
ROOTFS_DIR = os.path.join(INSTALL_DIR, "rootfs")
CONFIG_DIR = os.path.join(INSTALL_DIR, "config")
DESKTOP_FILE = os.path.expanduser("~/.local/share/applications/my-android.desktop")
ICON_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")

# ─── CSS ──────────────────────────────────────────────────────────────────
CSS = b"""
window {
    background-color: #0d1117;
}
.title-label {
    color: #58a6ff;
    font-size: 28px;
    font-weight: bold;
}
.subtitle-label {
    color: #8b949e;
    font-size: 13px;
}
.status-label {
    color: #c9d1d9;
    font-size: 12px;
    font-family: monospace;
}
.success-label {
    color: #3fb950;
    font-size: 14px;
    font-weight: bold;
}
.error-label {
    color: #f85149;
    font-size: 14px;
    font-weight: bold;
}
.install-button {
    background-image: none;
    background-color: #238636;
    color: #ffffff;
    border: 1px solid #2ea043;
    border-radius: 8px;
    padding: 12px 40px;
    font-size: 16px;
    font-weight: bold;
}
.install-button:hover {
    background-color: #2ea043;
}
.install-button:disabled {
    background-color: #21262d;
    color: #484f58;
    border-color: #30363d;
}
.info-frame {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 16px;
}
.info-key {
    color: #8b949e;
    font-size: 12px;
}
.info-val {
    color: #c9d1d9;
    font-size: 12px;
    font-weight: bold;
}
.log-view {
    background-color: #0d1117;
    color: #3fb950;
    font-family: monospace;
    font-size: 11px;
    border: 1px solid #30363d;
    border-radius: 6px;
}
progressbar trough {
    background-color: #21262d;
    border-radius: 4px;
    min-height: 8px;
}
progressbar progress {
    background-color: #238636;
    border-radius: 4px;
    min-height: 8px;
}
"""


class InstallerWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="My Android — Installer")
        self.set_default_size(680, 620)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_resizable(False)

        # Load CSS
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        # ─── Main layout ─────────────────────────────────────────────
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        main_box.set_margin_top(30)
        main_box.set_margin_bottom(30)
        main_box.set_margin_start(40)
        main_box.set_margin_end(40)
        self.add(main_box)

        # Icon
        if os.path.exists(ICON_SRC):
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(ICON_SRC, 80, 80, True)
                icon_img = Gtk.Image.new_from_pixbuf(pixbuf)
                main_box.pack_start(icon_img, False, False, 0)
            except Exception:
                pass

        # Title
        title = Gtk.Label(label="My Android")
        title.get_style_context().add_class("title-label")
        main_box.pack_start(title, False, False, 0)

        subtitle = Gtk.Label(label="Redmi 9 (lancelot) · LineageOS 20 · Android 13")
        subtitle.get_style_context().add_class("subtitle-label")
        main_box.pack_start(subtitle, False, False, 4)

        # ─── System info frame ────────────────────────────────────────
        info_frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        info_frame.get_style_context().add_class("info-frame")
        info_frame.set_margin_top(8)

        sys_info = self._gather_sys_info()
        for key, val in sys_info:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            k = Gtk.Label(label=key)
            k.get_style_context().add_class("info-key")
            k.set_xalign(0)
            k.set_size_request(180, -1)
            v = Gtk.Label(label=val)
            v.get_style_context().add_class("info-val")
            v.set_xalign(0)
            v.set_ellipsize(Pango.EllipsizeMode.END)
            row.pack_start(k, False, False, 0)
            row.pack_start(v, True, True, 0)
            info_frame.pack_start(row, False, False, 0)

        main_box.pack_start(info_frame, False, False, 0)

        # ─── Progress bar ─────────────────────────────────────────────
        self.progress = Gtk.ProgressBar()
        self.progress.set_show_text(False)
        main_box.pack_start(self.progress, False, False, 4)

        # ─── Status label ─────────────────────────────────────────────
        self.status_label = Gtk.Label(label="Ready to install.")
        self.status_label.get_style_context().add_class("status-label")
        self.status_label.set_xalign(0)
        main_box.pack_start(self.status_label, False, False, 0)

        # ─── Log view ─────────────────────────────────────────────────
        scroll = Gtk.ScrolledWindow()
        scroll.set_min_content_height(160)
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.log_buffer = Gtk.TextBuffer()
        self.log_view = Gtk.TextView(buffer=self.log_buffer)
        self.log_view.set_editable(False)
        self.log_view.set_cursor_visible(False)
        self.log_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.log_view.get_style_context().add_class("log-view")
        self.log_view.set_left_margin(10)
        self.log_view.set_right_margin(10)
        self.log_view.set_top_margin(8)
        scroll.add(self.log_view)
        main_box.pack_start(scroll, True, True, 0)

        # ─── Install button ───────────────────────────────────────────
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        btn_box.set_halign(Gtk.Align.CENTER)
        self.install_btn = Gtk.Button(label="⬇  Install")
        self.install_btn.get_style_context().add_class("install-button")
        self.install_btn.connect("clicked", self.on_install_clicked)
        btn_box.pack_start(self.install_btn, False, False, 0)
        main_box.pack_start(btn_box, False, False, 4)

    # ─── helpers ──────────────────────────────────────────────────────
    def _gather_sys_info(self):
        kernel = self._cmd("uname -r")
        binder = "✅ Ready" if os.path.exists("/dev/binder") or os.path.exists("/dev/anbox-binder") else "❌ Not found"
        binder_mod = "✅ Loaded" if "binder_linux" in self._cmd("lsmod") else "❌ Not loaded"
        sys_img = "✅" if os.path.exists(os.path.join(SOURCE_DIR, "system.img")) else "❌ Missing"
        vnd_img = "✅" if os.path.exists(os.path.join(SOURCE_DIR, "vendor.img")) else "❌ Missing"
        return [
            ("Device:", "Redmi 9 (lancelot) — M2004J19G"),
            ("Android:", "13 (TQ3A.230901.001)"),
            ("ROM:", "LineageOS 20.0 GAPPS"),
            ("Security Patch:", "2026-02-01"),
            ("Bootloader:", "🔒 Locked"),
            ("Root Status:", "❌ Not Rooted (ro.secure=1)"),
            ("Verified Boot:", "🟢 Green (Verified)"),
            ("Host Kernel:", kernel),
            ("Binder:", binder),
            ("binder_linux:", binder_mod),
            ("system.img:", sys_img),
            ("vendor.img:", vnd_img),
        ]

    @staticmethod
    def _cmd(cmd):
        try:
            return subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL, timeout=5).decode().strip()
        except Exception:
            return ""

    def log(self, msg):
        GLib.idle_add(self._log_ui, msg)

    def _log_ui(self, msg):
        end_iter = self.log_buffer.get_end_iter()
        self.log_buffer.insert(end_iter, msg + "\n")
        self.log_view.scroll_to_iter(self.log_buffer.get_end_iter(), 0.0, False, 0.0, 0.0)

    def set_status(self, msg):
        GLib.idle_add(self.status_label.set_text, msg)

    def set_progress(self, frac):
        GLib.idle_add(self.progress.set_fraction, frac)

    def set_finished(self, success, msg):
        GLib.idle_add(self._finish_ui, success, msg)

    def _finish_ui(self, success, msg):
        self.status_label.set_text(msg)
        cls = "success-label" if success else "error-label"
        self.status_label.get_style_context().add_class(cls)
        self.install_btn.set_sensitive(True)
        self.install_btn.set_label("✅  Done" if success else "⟳  Retry")

    # ─── Password dialog ────────────────────────────────────────────────
    def ask_password(self):
        """Show a GTK password dialog. Returns the password or None."""
        dialog = Gtk.Dialog(
            title="Yetkilendirme Gerekli",
            parent=self,
            flags=Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
        )
        dialog.add_buttons(
            "İptal", Gtk.ResponseType.CANCEL,
            "Doğrula", Gtk.ResponseType.OK,
        )
        dialog.set_default_size(380, -1)
        dialog.set_resizable(False)

        # Style the dialog
        dialog.get_style_context().add_class("info-frame")

        content = dialog.get_content_area()
        content.set_spacing(12)
        content.set_margin_top(16)
        content.set_margin_bottom(8)
        content.set_margin_start(20)
        content.set_margin_end(20)

        # Lock icon + title
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        lock_label = Gtk.Label(label="🔒")
        lock_label.set_markup("<span size='xx-large'>🔒</span>")
        hbox.pack_start(lock_label, False, False, 0)
        title = Gtk.Label()
        title.set_markup("<b>Kurulum için root şifresi gerekli</b>")
        title.get_style_context().add_class("info-val")
        hbox.pack_start(title, False, False, 0)
        content.pack_start(hbox, False, False, 0)

        desc = Gtk.Label(label="Sistem dosyalarını yüklemek için yönetici şifrenizi girin:")
        desc.get_style_context().add_class("info-key")
        desc.set_xalign(0)
        content.pack_start(desc, False, False, 0)

        # Password entry
        entry = Gtk.Entry()
        entry.set_visibility(False)  # dots for password
        entry.set_invisible_char('●')
        entry.set_placeholder_text("Şifre")
        entry.connect("activate", lambda e: dialog.response(Gtk.ResponseType.OK))
        content.pack_start(entry, False, False, 0)

        # Error label (hidden initially)
        self.pwd_error = Gtk.Label()
        self.pwd_error.get_style_context().add_class("error-label")
        self.pwd_error.set_no_show_all(True)
        content.pack_start(self.pwd_error, False, False, 0)

        dialog.show_all()

        while True:
            response = dialog.run()
            if response != Gtk.ResponseType.OK:
                dialog.destroy()
                return None

            pwd = entry.get_text()
            if not pwd:
                self.pwd_error.set_text("Şifre boş olamaz")
                self.pwd_error.show()
                continue

            # Validate password
            try:
                subprocess.check_output(
                    f"echo '{pwd}' | sudo -S -k id",
                    shell=True, stderr=subprocess.STDOUT, timeout=10
                )
                dialog.destroy()
                return pwd
            except subprocess.CalledProcessError:
                self.pwd_error.set_text("❌ Şifre yanlış, tekrar deneyin")
                self.pwd_error.show()
                entry.set_text("")
                entry.grab_focus()
                continue

    # ─── Run command with sudo ────────────────────────────────────────
    def run_root(self, cmd):
        """Run a command as root using the stored password."""
        full = f"echo '{self.sudo_password}' | sudo -S bash -c \"{cmd}\""
        try:
            out = subprocess.check_output(full, shell=True, stderr=subprocess.STDOUT, timeout=300).decode()
            return 0, out.strip()
        except subprocess.CalledProcessError as e:
            return e.returncode, e.output.decode().strip() if e.output else str(e)
        except Exception as e:
            return 1, str(e)

    def write_root_file(self, content, dest_path, executable=False):
        """Write content to a root-owned file via temp file + sudo cp.
        This avoids all shell quoting issues with heredocs."""
        import tempfile
        tmp_fd, tmp_path = tempfile.mkstemp()
        try:
            with os.fdopen(tmp_fd, 'w') as f:
                f.write(content)
            rc, out = self.run_root(f"cp '{tmp_path}' '{dest_path}'")
            if rc != 0:
                raise RuntimeError(f"Failed to write {dest_path}: {out}")
            if executable:
                self.run_root(f"chmod +x '{dest_path}'")
        finally:
            os.unlink(tmp_path)

    # ─── Install button handler ───────────────────────────────────────
    def on_install_clicked(self, btn):
        # Ask for password first
        password = self.ask_password()
        if password is None:
            return  # User cancelled

        self.sudo_password = password
        btn.set_sensitive(False)
        btn.set_label("Installing…")
        self.log("▸ Yetkilendirme başarılı ✓")
        threading.Thread(target=self.do_install, daemon=True).start()

    # ─── Installation steps ───────────────────────────────────────────
    def do_install(self):
        steps = [
            (0.05, "Creating directories…",              self.step_create_dirs),
            (0.15, "Copying system.img…",                self.step_copy_system),
            (0.40, "Copying vendor.img…",                self.step_copy_vendor),
            (0.52, "Writing device configuration…",      self.step_write_lxc_conf),
            (0.60, "Injecting device identity…",         self.step_write_stealth_props),
            (0.68, "Writing launcher…",                  self.step_write_start_sh),
            (0.76, "Writing shutdown script…",            self.step_write_stop_sh),
            (0.82, "Installing launcher app…",           self.step_install_launcher),
            (0.88, "Installing icon…",                   self.step_install_icon),
            (0.93, "Creating desktop entry…",            self.step_create_desktop),
            (1.00, "Finalizing…",                        self.step_finalize),
        ]
        for frac, msg, func in steps:
            self.set_status(msg)
            self.log(f"▸ {msg}")
            self.set_progress(frac)
            try:
                func()
            except Exception as e:
                self.log(f"✖ ERROR: {e}")
                self.set_finished(False, f"Installation failed: {e}")
                return
        self.set_finished(True, "✅ Installation completed successfully!")
        self.log("─" * 50)
        self.log("✅ All done! You can now launch 'My Android' from your applications menu.")

    # ─── Individual steps ─────────────────────────────────────────────

    def step_create_dirs(self):
        for d in [INSTALL_DIR, IMAGES_DIR, ROOTFS_DIR, CONFIG_DIR]:
            rc, out = self.run_root(f"mkdir -p {d}")
            if rc != 0:
                raise RuntimeError(f"mkdir {d}: {out}")
            self.log(f"  ✓ {d}")

    def step_copy_system(self):
        src = os.path.join(SOURCE_DIR, "system.img")
        dst = os.path.join(IMAGES_DIR, "system.img")
        if not os.path.exists(src):
            raise FileNotFoundError(f"system.img not found at {src}")
        rc, out = self.run_root(f"cp '{src}' '{dst}'")
        if rc != 0:
            raise RuntimeError(f"Copy system.img failed: {out}")
        self.log(f"  ✓ system.img → {dst}")

    def step_copy_vendor(self):
        src = os.path.join(SOURCE_DIR, "vendor.img")
        dst = os.path.join(IMAGES_DIR, "vendor.img")
        if not os.path.exists(src):
            raise FileNotFoundError(f"vendor.img not found at {src}")
        rc, out = self.run_root(f"cp '{src}' '{dst}'")
        if rc != 0:
            raise RuntimeError(f"Copy vendor.img failed: {out}")
        self.log(f"  ✓ vendor.img → {dst}")

    def step_write_lxc_conf(self):
        conf = r"""# Device Configuration
# Auto-generated — lancelot (Redmi 9)

# Hostname matches real device
lxc.uts.name = localhost

# Root filesystem
lxc.rootfs.path = dir:/opt/my-android/rootfs

# Network — use host network
lxc.net.0.type = none

# No capability restrictions — Android init needs full caps
lxc.cap.drop =

# Security profile — unconfined for Android HAL compat
lxc.apparmor.profile = unconfined

# Console
lxc.tty.max = 0
lxc.pty.max = 1024

# Allow ALL device access (Android needs many char/block devices)
lxc.cgroup2.devices.allow = a

# Proc/sys — rw so Android init can write props
lxc.mount.auto = proc:rw sys:rw cgroup:mixed

# Binder devices (bind from host)
lxc.mount.entry = /dev/anbox-binder dev/binder none bind,create=file 0 0
lxc.mount.entry = /dev/anbox-hwbinder dev/hwbinder none bind,create=file,optional 0 0
lxc.mount.entry = /dev/anbox-vndbinder dev/vndbinder none bind,create=file,optional 0 0

# Wayland socket passthrough
lxc.mount.entry = /run/user/1000/wayland-0 run/user/1000/wayland-0 none bind,create=file,optional 0 0

# Stealth property overlay — bind over default.prop
lxc.mount.entry = /opt/my-android/config/stealth.prop default.prop none bind,create=file 0 0

# Hide container env vars from inside
lxc.environment = PATH=/product/bin:/apex/com.android.runtime/bin:/system/bin:/system/xbin:/vendor/bin
lxc.environment = ANDROID_ROOT=/system
lxc.environment = ANDROID_DATA=/data
lxc.environment = ANDROID_STORAGE=/storage
lxc.environment = BOOTCLASSPATH=/apex/com.android.art/javalib/core-oj.jar

# Init
lxc.init.cmd = /init
lxc.signal.halt = SIGRTMIN+3

# Logging
lxc.log.level = WARN
lxc.log.file = /opt/my-android/device.log
"""
        self.write_root_file(conf, f"{CONFIG_DIR}/lxc.conf")
        self.log(f"  ✓ {CONFIG_DIR}/lxc.conf")

    def step_write_stealth_props(self):
        """Write the stealth property override file that makes the device
        appear as a real Redmi 9 (lancelot) with locked bootloader, no root."""
        props = r"""# ═══════════════════════════════════════════════════════════════
# Device Identity — Redmi 9 (lancelot) — LineageOS 20
# This file overrides default.prop inside the Android environment
# to ensure the device appears as a genuine, non-rooted device.
# ═══════════════════════════════════════════════════════════════

# ─── Security & Root Status ───────────────────────────────────
ro.secure=1
ro.debuggable=0
ro.adb.secure=1
ro.allow.mock.location=0
persist.sys.usb.config=mtp
ro.build.selinux=1
ro.boot.flash.locked=1
ro.boot.verifiedbootstate=green
ro.boot.veritymode=enforcing
ro.boot.warranty_bit=0
ro.warranty_bit=0
ro.is_ever_orange=0

# ─── Device Identity ─────────────────────────────────────────
ro.build.product=lancelot
ro.build.description=lineage_lancelot-user 13 TQ3A.230901.001 eng.aleast.20260312.162339 release-keys
ro.build.display.id=lineage_lancelot-user 13 TQ3A.230901.001 eng.aleast.20260312.162339 release-keys
ro.build.flavor=lineage_lancelot-user
ro.build.host=zero
ro.build.id=TQ3A.230901.001
ro.build.tags=release-keys
ro.build.type=user
ro.build.user=aleasto
ro.build.date=Thu Mar 12 16:22:16 CET 2026
ro.build.date.utc=1773328936
ro.build.system_root_image=true
ro.build.characteristics=default
ro.build.version.release=13
ro.build.version.sdk=33
ro.build.version.security_patch=2026-02-01
ro.build.version.codename=REL
ro.build.version.incremental=eng.aleast.20260312.162339
ro.build.version.all_codenames=REL
ro.build.version.min_supported_target_sdk=23
ro.build.version.preview_sdk=0

# ─── Product Identity ────────────────────────────────────────
ro.product.system.brand=Redmi
ro.product.system.device=lancelot
ro.product.system.manufacturer=Xiaomi
ro.product.system.model=M2004J19G
ro.product.system.name=lineage_lancelot
ro.product.system_ext.brand=redmi
ro.product.system_ext.device=lancelot
ro.product.system_ext.manufacturer=Xiaomi
ro.product.system_ext.model=M2004J19G
ro.product.system_ext.name=lineage_lancelot
ro.product.cpu.abi=x86_64
ro.product.locale=en-US

# ─── System Fingerprint ──────────────────────────────────────
ro.system.build.fingerprint=redmi/lineage_lancelot/lancelot:13/TQ3A.230901.001/aleasto03121622:user/release-keys
ro.system.build.id=TQ3A.230901.001
ro.system.build.tags=release-keys
ro.system.build.type=user
ro.system.build.date=Thu Mar 12 16:22:16 CET 2026
ro.system.build.date.utc=1773328936
ro.system.build.version.release=13
ro.system.build.version.sdk=33
ro.system.build.version.incremental=eng.aleast.20260312.162339

# ─── LineageOS Identity ──────────────────────────────────────
ro.lineage.build.version=20.0
ro.lineage.device=lancelot
ro.lineage.display.version=20-20260312-GAPPS-lancelot
ro.lineage.releasetype=GAPPS
ro.lineage.version=20.0-20260312-GAPPS-lancelot
ro.modversion=20.0-20260312-GAPPS-lancelot

# ─── GMS / Google ────────────────────────────────────────────
ro.com.google.clientidbase=android-google
ro.com.google.gmsversion=13_202304
ro.opa.eligible_device=true

# ─── Surface Flinger ─────────────────────────────────────────
ro.surface_flinger.max_frame_buffer_acquired_buffers=3
ro.surface_flinger.running_without_sync_framework=true
ro.surface_flinger.vsync_event_phase_offset_ns=2000000
ro.surface_flinger.vsync_sf_event_offset_ns=6000000

# ─── Anti-Detection ──────────────────────────────────────────
# Props that container/emulator detection tools check
ro.kernel.qemu=0
ro.hardware.chipname=mt6768
ro.board.platform=mt6768
ro.mediatek.platform=MT6768
persist.sys.dalvik.vm.lib.2=libart.so
dalvik.vm.isa.x86_64.variant=x86_64
ro.hardware=mt6768
gsm.version.baseband=MOLY.LR12A.R3.MP.V133.6
ro.telephony.default_network=9
ro.setupwizard.mode=DISABLED
ro.controlprivapp_permissions=enforce
ro.actionable_compatible_property.enabled=true
"""
        self.write_root_file(props, f"{CONFIG_DIR}/stealth.prop")
        self.log(f"  ✓ {CONFIG_DIR}/stealth.prop — device identity injected")
        self.log(f"    → ro.secure=1, ro.debuggable=0")
        self.log(f"    → ro.boot.verifiedbootstate=green")
        self.log(f"    → ro.boot.flash.locked=1")
        self.log(f"    → Redmi 9 (lancelot) M2004J19G")

    def step_write_start_sh(self):
        script = r"""#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════
# My Android — Device Launcher
# Redmi 9 (lancelot) · LineageOS 20 · Android 13
# ═══════════════════════════════════════════════════════════════════════
set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

INSTALL="/opt/my-android"
IMAGES="$INSTALL/images"
ROOTFS="$INSTALL/rootfs"
CONFIG="$INSTALL/config/lxc.conf"
CONTAINER="my-android"

log()  { echo -e "${GREEN}[✓]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[✖]${NC} $*"; }
info() { echo -e "${CYAN}[i]${NC} $*"; }

cleanup() {
    err "Error occurred, cleaning up…"
    lxc-stop -n "$CONTAINER" -k 2>/dev/null || true
    umount "$ROOTFS/vendor" 2>/dev/null || true
    umount "$ROOTFS" 2>/dev/null || true
    [ -n "$LOOP_VND" ] && losetup -d "$LOOP_VND" 2>/dev/null || true
    [ -n "$LOOP_SYS" ] && losetup -d "$LOOP_SYS" 2>/dev/null || true
    exit 1
}
trap cleanup ERR

echo -e "${GREEN}"
echo "  ╔══════════════════════════════════════════════╗"
echo "  ║       Redmi 9 (lancelot) · Android 13       ║"
echo "  ║     LineageOS 20.0 · Build TQ3A.230901.001   ║"
echo "  ╚══════════════════════════════════════════════╝"
echo -e "${NC}"

# ─── 1. Detect platform ──────────────────────────────────────────────
if grep -q "Ubuntu Touch" /etc/os-release 2>/dev/null; then
    PLATFORM="ubuntu-touch"
    info "Platform: Ubuntu Touch"
    BINDER_DEV="/dev/binder"
else
    PLATFORM="desktop"
    info "Platform: Desktop Linux"
    if [ -e /dev/anbox-binder ]; then
        BINDER_DEV="/dev/anbox-binder"
    elif [ -e /dev/binder ]; then
        BINDER_DEV="/dev/binder"
    else
        BINDER_DEV=""
    fi
fi

# ─── 2. Check binder ─────────────────────────────────────────────────
if ! lsmod | grep -q binder_linux; then
    info "Loading binder driver…"
    modprobe binder_linux devices="binder,hwbinder,vndbinder" 2>/dev/null || {
        warn "binder_linux module not available"
        warn "Continuing with existing binder device"
    }
fi

if [ -n "$BINDER_DEV" ]; then
    log "Binder: $BINDER_DEV"
else
    warn "No binder device found"
fi

# ─── 3. Update binder path in config ─────────────────────────────────
if [ -n "$BINDER_DEV" ]; then
    sed -i "s|^lxc.mount.entry = .* dev/binder .*|lxc.mount.entry = $BINDER_DEV dev/binder none bind,create=file 0 0|" "$CONFIG"
fi

# ─── 4. Mount images ─────────────────────────────────────────────────
# system.img IS the rootfs (contains /init, /system/, etc.)
# vendor.img mounts at rootfs/vendor/
if mountpoint -q "$ROOTFS" 2>/dev/null; then
    log "system: mounted"
else
    info "Mounting system (rootfs)…"
    LOOP_SYS=$(losetup -fP --show "$IMAGES/system.img")
    mount -o rw "$LOOP_SYS" "$ROOTFS"
    log "system: $LOOP_SYS → $ROOTFS (rootfs)"
fi

if mountpoint -q "$ROOTFS/vendor" 2>/dev/null; then
    log "vendor: mounted"
else
    info "Mounting vendor…"
    LOOP_VND=$(losetup -fP --show "$IMAGES/vendor.img")
    mount -o ro "$LOOP_VND" "$ROOTFS/vendor"
    log "vendor: $LOOP_VND → $ROOTFS/vendor"
fi

# ─── 5. Prepare rootfs device nodes ──────────────────────────────────
# Android init needs these to exist BEFORE lxc-start
mkdir -p "$ROOTFS/dev" "$ROOTFS/dev/pts" "$ROOTFS/data" "$ROOTFS/cache" 2>/dev/null || true
mkdir -p "$ROOTFS/run/user/1000" 2>/dev/null || true

# Create essential device nodes if missing
[ -e "$ROOTFS/dev/null" ]    || mknod -m 666 "$ROOTFS/dev/null"    c 1 3
[ -e "$ROOTFS/dev/zero" ]    || mknod -m 666 "$ROOTFS/dev/zero"    c 1 5
[ -e "$ROOTFS/dev/full" ]    || mknod -m 666 "$ROOTFS/dev/full"    c 1 7
[ -e "$ROOTFS/dev/random" ]  || mknod -m 666 "$ROOTFS/dev/random"  c 1 8
[ -e "$ROOTFS/dev/urandom" ] || mknod -m 666 "$ROOTFS/dev/urandom" c 1 9
[ -e "$ROOTFS/dev/tty" ]     || mknod -m 666 "$ROOTFS/dev/tty"     c 5 0
[ -e "$ROOTFS/dev/ptmx" ]    || mknod -m 666 "$ROOTFS/dev/ptmx"    c 5 2
log "Device nodes: ready"

# ─── 6. Stealth — inject device identity ─────────────────────────────
if [ -f "$INSTALL/config/stealth.prop" ]; then
    cp "$INSTALL/config/stealth.prop" "$ROOTFS/default.prop" 2>/dev/null || true
    log "Device identity: injected"
fi

# ─── 6b. Create essential symlinks if missing ───────────────────────
ln -sf /proc/self/fd "$ROOTFS/dev/fd" 2>/dev/null || true
ln -sf /proc/self/fd/0 "$ROOTFS/dev/stdin" 2>/dev/null || true
ln -sf /proc/self/fd/1 "$ROOTFS/dev/stdout" 2>/dev/null || true
ln -sf /proc/self/fd/2 "$ROOTFS/dev/stderr" 2>/dev/null || true
log "Device nodes: prepared"

# ─── 7. Start Android ────────────────────────────────────────────────
if lxc-info -n "$CONTAINER" 2>/dev/null | grep -q "RUNNING"; then
    log "Device already running"
else
    info "Booting Android…"
    lxc-start -n "$CONTAINER" -f "$CONFIG" -d --logfile="$INSTALL/device.log" --logpriority=DEBUG
    sleep 2
    if lxc-info -n "$CONTAINER" 2>/dev/null | grep -q "RUNNING"; then
        log "Android booted successfully"
    else
        err "Boot failed. Check $INSTALL/device.log"
        tail -20 "$INSTALL/device.log" 2>/dev/null
        cleanup
    fi
fi

# ─── 8. Wayland display ──────────────────────────────────────────────
# sudo loses XDG_RUNTIME_DIR — find real user's socket
REAL_UID="${SUDO_UID:-$(id -u)}"
WAYLAND_SOCKET="/run/user/$REAL_UID/wayland-0"
if [ -S "$WAYLAND_SOCKET" ]; then
    log "Display: Wayland ($WAYLAND_SOCKET)"
    # Update LXC config with correct wayland path
    sed -i "s|^lxc.mount.entry = .* run/user/.*/wayland-0 .*|lxc.mount.entry = $WAYLAND_SOCKET run/user/1000/wayland-0 none bind,create=file,optional 0 0|" "$CONFIG"
else
    warn "Wayland display not found at $WAYLAND_SOCKET"
fi

# ─── 9. Device Status ────────────────────────────────────────────────
echo ""
echo -e "${GREEN}  ╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}  ║            Device Status Report              ║${NC}"
echo -e "${GREEN}  ╠══════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}  ║${NC}  Device:       Redmi 9 (M2004J19G)           ${GREEN}║${NC}"
echo -e "${GREEN}  ║${NC}  Codename:     lancelot                     ${GREEN}║${NC}"
echo -e "${GREEN}  ║${NC}  Android:      13 (API 33)                  ${GREEN}║${NC}"
echo -e "${GREEN}  ║${NC}  ROM:          LineageOS 20.0 GAPPS          ${GREEN}║${NC}"
echo -e "${GREEN}  ║${NC}  Build:        TQ3A.230901.001               ${GREEN}║${NC}"
echo -e "${GREEN}  ║${NC}  Bootloader:   🔒 Locked                     ${GREEN}║${NC}"
echo -e "${GREEN}  ║${NC}  Root:         ❌ Not Rooted                  ${GREEN}║${NC}"
echo -e "${GREEN}  ║${NC}  Verified Boot: 🟢 Green (Verified)          ${GREEN}║${NC}"
echo -e "${GREEN}  ║${NC}  SELinux:      Enforcing                     ${GREEN}║${NC}"
echo -e "${GREEN}  ║${NC}  Security:     2026-02-01                    ${GREEN}║${NC}"
echo -e "${GREEN}  ╠══════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}  ║${NC}  Status:       ${GREEN}● Running${NC}                     ${GREEN}║${NC}"
echo -e "${GREEN}  ╚══════════════════════════════════════════════╝${NC}"
echo ""
log "Device is ready."
log "To shut down: $INSTALL/stop.sh"
"""
        self.write_root_file(script, f"{INSTALL_DIR}/start.sh", executable=True)
        self.log(f"  ✓ {INSTALL_DIR}/start.sh")

    def step_write_stop_sh(self):
        script = r"""#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════
# My Android — Shutdown
# ═══════════════════════════════════════════════════════════════════════
set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

INSTALL="/opt/my-android"
ROOTFS="$INSTALL/rootfs"
CONTAINER="my-android"

log()  { echo -e "${GREEN}[✓]${NC} $*"; }
err()  { echo -e "${RED}[✖]${NC} $*"; }

# ─── 1. Stop device ──────────────────────────────────────────────────
if lxc-info -n "$CONTAINER" 2>/dev/null | grep -q "RUNNING"; then
    log "Shutting down device…"
    lxc-stop -n "$CONTAINER" -t 10 2>/dev/null || {
        log "Force shutdown…"
        lxc-stop -n "$CONTAINER" -k 2>/dev/null || true
    }
    log "Device powered off"
else
    log "Device is not running."
fi

# ─── 2. Unmount partitions ───────────────────────────────────────────
# vendor first (nested mount), then rootfs
for mp in "$ROOTFS/vendor" "$ROOTFS"; do
    if mountpoint -q "$mp" 2>/dev/null; then
        log "Unmounting $(basename $mp)…"
        umount "$mp" 2>/dev/null || umount -l "$mp" 2>/dev/null || true
        log "  $(basename $mp) unmounted"
    fi
done

# ─── 3. Release loop devices ────────────────────────────────────────
for img in system.img vendor.img; do
    LOOPS=$(losetup -j "$INSTALL/images/$img" 2>/dev/null | cut -d: -f1)
    for loop in $LOOPS; do
        losetup -d "$loop" 2>/dev/null || true
        log "Released $loop"
    done
done

# ─── 4. Cleanup ──────────────────────────────────────────────────────
lxc-destroy -n "$CONTAINER" 2>/dev/null || true

echo ""
echo -e "${GREEN}  Device powered off successfully.${NC}"
echo ""
"""
        self.write_root_file(script, f"{INSTALL_DIR}/stop.sh", executable=True)
        self.log(f"  ✓ {INSTALL_DIR}/stop.sh")

    def step_install_launcher(self):
        launcher_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "launcher.py")
        if os.path.exists(launcher_src):
            rc, out = self.run_root(f"cp '{launcher_src}' '{INSTALL_DIR}/launcher.py'")
            if rc != 0:
                raise RuntimeError(f"Copy launcher failed: {out}")
            self.run_root(f"chmod +x '{INSTALL_DIR}/launcher.py'")
            self.log(f"  ✓ Launcher app → {INSTALL_DIR}/launcher.py")
        else:
            self.log(f"  ⚠ launcher.py not found at {launcher_src}")

    def step_install_icon(self):
        if os.path.exists(ICON_SRC):
            rc, out = self.run_root(f"cp '{ICON_SRC}' '{INSTALL_DIR}/icon.png'")
            if rc != 0:
                raise RuntimeError(f"Copy icon failed: {out}")
            self.log(f"  ✓ Icon installed to {INSTALL_DIR}/icon.png")
        else:
            self.log(f"  ⚠ Icon not found at {ICON_SRC}, skipping")

    def step_create_desktop(self):
        desktop_dir = os.path.expanduser("~/.local/share/applications")
        os.makedirs(desktop_dir, exist_ok=True)

        desktop_content = """[Desktop Entry]
Name=My Android
Comment=Redmi 9 · LineageOS 20 · Android 13
Exec=python3 /opt/my-android/launcher.py
Icon=/opt/my-android/icon.png
Terminal=false
Type=Application
Categories=System;
Keywords=android;redmi;lineageos;
"""
        with open(DESKTOP_FILE, 'w') as f:
            f.write(desktop_content)
        os.chmod(DESKTOP_FILE, 0o755)
        self.log(f"  ✓ Desktop entry → {DESKTOP_FILE}")


    def step_finalize(self):
        # Update desktop database
        subprocess.run(["update-desktop-database",
                        os.path.expanduser("~/.local/share/applications")],
                       capture_output=True, timeout=10)
        self.log("  ✓ Desktop database updated")


# ─── Main ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = InstallerWindow()
    app.connect("destroy", Gtk.main_quit)
    app.show_all()
    Gtk.main()
