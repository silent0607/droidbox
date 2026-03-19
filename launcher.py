#!/usr/bin/env python3
"""
My Android — GTK3 Launcher
Start/Stop the Android container with a beautiful GUI.
"""
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk, Pango, GdkPixbuf
import subprocess
import os
import threading
import time
import re

# ANSI escape code pattern
ANSI_RE = re.compile(r'\x1b\[[0-9;]*m')

INSTALL_DIR = "/opt/my-android"
ICON_PATH = os.path.join(INSTALL_DIR, "icon.png")

# ─── CSS ──────────────────────────────────────────────────────────────────
CSS = b"""
* {
    background-image: none;
}
window {
    background: #0d1117;
}
.title-label {
    color: #58a6ff;
    font-size: 26px;
    font-weight: bold;
}
.subtitle-label {
    color: #8b949e;
    font-size: 12px;
}
.status-running {
    color: #3fb950;
    font-size: 14px;
    font-weight: bold;
}
.status-stopped {
    color: #f85149;
    font-size: 14px;
    font-weight: bold;
}
.status-busy {
    color: #d29922;
    font-size: 14px;
    font-weight: bold;
}
.info-frame {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
}
.info-key {
    color: #8b949e;
    font-size: 11px;
}
.info-val {
    color: #c9d1d9;
    font-size: 11px;
    font-weight: bold;
}
.start-button {
    background: #238636;
    color: #ffffff;
    border: 1px solid #2ea043;
    border-radius: 8px;
    font-weight: bold;
}
.start-button:hover {
    background: #2ea043;
}
.start-button:disabled {
    background: #21262d;
    color: #484f58;
}
.stop-button {
    background: #da3633;
    color: #ffffff;
    border: 1px solid #f85149;
    border-radius: 8px;
    font-weight: bold;
}
.stop-button:hover {
    background: #f85149;
}
.stop-button:disabled {
    background: #21262d;
    color: #484f58;
}
.log-view {
    background: #0d1117;
    color: #3fb950;
    font-family: monospace;
    font-size: 11px;
    border: 1px solid #30363d;
}
"""


class LauncherWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="My Android")
        self.set_default_size(620, 560)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_resizable(False)
        self.sudo_password = None

        # Load CSS
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        # ─── Main layout ─────────────────────────────────────────────
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        main_box.set_margin_top(24)
        main_box.set_margin_bottom(24)
        main_box.set_margin_start(32)
        main_box.set_margin_end(32)
        self.add(main_box)

        # Icon + Title row
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        header.set_halign(Gtk.Align.CENTER)
        if os.path.exists(ICON_PATH):
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(ICON_PATH, 56, 56, True)
                icon = Gtk.Image.new_from_pixbuf(pixbuf)
                header.pack_start(icon, False, False, 0)
            except Exception:
                pass
        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        title = Gtk.Label(label="My Android")
        title.get_style_context().add_class("title-label")
        title.set_xalign(0)
        title_box.pack_start(title, False, False, 0)
        subtitle = Gtk.Label(label="Redmi 9 (lancelot) · LineageOS 20 · Android 13")
        subtitle.get_style_context().add_class("subtitle-label")
        subtitle.set_xalign(0)
        title_box.pack_start(subtitle, False, False, 0)
        header.pack_start(title_box, False, False, 0)
        main_box.pack_start(header, False, False, 0)

        # ─── Device info frame ─────────────────────────────────────────
        info_frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        info_frame.get_style_context().add_class("info-frame")
        info_data = [
            ("Device:", "Redmi 9 (M2004J19G)"),
            ("Build:", "TQ3A.230901.001"),
            ("Bootloader:", "🔒 Locked"),
            ("Root:", "❌ Not Rooted"),
            ("Verified Boot:", "🟢 Green"),
        ]
        for key, val in info_data:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            k = Gtk.Label(label=key)
            k.get_style_context().add_class("info-key")
            k.set_xalign(0)
            k.set_size_request(120, -1)
            v = Gtk.Label(label=val)
            v.get_style_context().add_class("info-val")
            v.set_xalign(0)
            row.pack_start(k, False, False, 0)
            row.pack_start(v, True, True, 0)
            info_frame.pack_start(row, False, False, 0)

        # Status row inside info
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        k = Gtk.Label(label="Status:")
        k.get_style_context().add_class("info-key")
        k.set_xalign(0)
        k.set_size_request(120, -1)
        self.status_label = Gtk.Label(label="● Stopped")
        self.status_label.get_style_context().add_class("status-stopped")
        self.status_label.set_xalign(0)
        row.pack_start(k, False, False, 0)
        row.pack_start(self.status_label, True, True, 0)
        info_frame.pack_start(row, False, False, 0)

        main_box.pack_start(info_frame, False, False, 0)

        # ─── Buttons ─────────────────────────────────────────────────
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        btn_box.set_halign(Gtk.Align.CENTER)

        self.start_btn = Gtk.Button(label="▶  Start")
        self.start_btn.get_style_context().add_class("start-button")
        self.start_btn.connect("clicked", self.on_start_clicked)
        btn_box.pack_start(self.start_btn, False, False, 0)

        self.stop_btn = Gtk.Button(label="■  Stop")
        self.stop_btn.get_style_context().add_class("stop-button")
        self.stop_btn.connect("clicked", self.on_stop_clicked)
        self.stop_btn.set_sensitive(False)
        btn_box.pack_start(self.stop_btn, False, False, 0)

        main_box.pack_start(btn_box, False, False, 8)

        # ─── Log view ─────────────────────────────────────────────────
        scroll = Gtk.ScrolledWindow()
        scroll.set_min_content_height(200)
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

        # Check initial state
        GLib.timeout_add(500, self._check_initial_state)

    # ─── Helpers ──────────────────────────────────────────────────────
    def log(self, msg):
        GLib.idle_add(self._log_ui, msg)

    def _log_ui(self, msg):
        end = self.log_buffer.get_end_iter()
        self.log_buffer.insert(end, msg + "\n")
        self.log_view.scroll_to_iter(self.log_buffer.get_end_iter(), 0.0, False, 0.0, 0.0)

    def set_status(self, state):
        """state: 'running', 'stopped', 'starting', 'stopping'"""
        GLib.idle_add(self._set_status_ui, state)

    def _set_status_ui(self, state):
        for cls in ["status-running", "status-stopped", "status-busy"]:
            self.status_label.get_style_context().remove_class(cls)
        if state == "running":
            self.status_label.set_text("● Running")
            self.status_label.get_style_context().add_class("status-running")
            self.start_btn.set_sensitive(False)
            self.stop_btn.set_sensitive(True)
        elif state == "stopped":
            self.status_label.set_text("● Stopped")
            self.status_label.get_style_context().add_class("status-stopped")
            self.start_btn.set_sensitive(True)
            self.stop_btn.set_sensitive(False)
        elif state == "starting":
            self.status_label.set_text("⟳ Starting…")
            self.status_label.get_style_context().add_class("status-busy")
            self.start_btn.set_sensitive(False)
            self.stop_btn.set_sensitive(False)
        elif state == "stopping":
            self.status_label.set_text("⟳ Stopping…")
            self.status_label.get_style_context().add_class("status-busy")
            self.start_btn.set_sensitive(False)
            self.stop_btn.set_sensitive(False)

    def _check_initial_state(self):
        """Check if container is already running."""
        try:
            out = subprocess.check_output(
                "lxc-info -n my-android 2>/dev/null | grep -c RUNNING",
                shell=True, stderr=subprocess.DEVNULL
            ).decode().strip()
            if out == "1":
                self.set_status("running")
                self.log("[✓] Device is already running.")
        except Exception:
            pass
        return False  # Don't repeat

    def ask_password(self):
        """Show password dialog. Returns password or None."""
        dialog = Gtk.Dialog(
            title="Yetkilendirme",
            transient_for=self,
            modal=True,
            destroy_with_parent=True,
        )
        dialog.add_buttons("İptal", Gtk.ResponseType.CANCEL, "Doğrula", Gtk.ResponseType.OK)
        dialog.set_default_size(360, -1)
        dialog.set_resizable(False)

        content = dialog.get_content_area()
        content.set_spacing(10)
        content.set_margin_top(14)
        content.set_margin_bottom(8)
        content.set_margin_start(18)
        content.set_margin_end(18)

        lbl = Gtk.Label()
        lbl.set_markup("<b>🔒  Root şifresi gerekli</b>")
        content.pack_start(lbl, False, False, 0)

        entry = Gtk.Entry()
        entry.set_visibility(False)
        entry.set_invisible_char('●')
        entry.set_placeholder_text("Şifre")
        entry.connect("activate", lambda e: dialog.response(Gtk.ResponseType.OK))
        content.pack_start(entry, False, False, 0)

        err_lbl = Gtk.Label()
        err_lbl.get_style_context().add_class("status-stopped")
        err_lbl.set_no_show_all(True)
        content.pack_start(err_lbl, False, False, 0)

        dialog.show_all()

        while True:
            resp = dialog.run()
            if resp != Gtk.ResponseType.OK:
                dialog.destroy()
                return None
            pwd = entry.get_text()
            if not pwd:
                err_lbl.set_text("Şifre boş olamaz")
                err_lbl.show()
                continue
            try:
                subprocess.check_output(
                    f"echo '{pwd}' | sudo -S -k id",
                    shell=True, stderr=subprocess.STDOUT, timeout=10
                )
                dialog.destroy()
                return pwd
            except subprocess.CalledProcessError:
                err_lbl.set_text("❌ Şifre yanlış")
                err_lbl.show()
                entry.set_text("")
                entry.grab_focus()

    def run_script(self, script_path, label):
        """Run a script with sudo, streaming output to log."""
        if not self.sudo_password:
            pwd = self.ask_password()
            if not pwd:
                return False
            self.sudo_password = pwd

        self.log(f"\n{'─' * 50}")
        self.log(f"▸ {label}")

        try:
            proc = subprocess.Popen(
                f"echo '{self.sudo_password}' | sudo -S bash {script_path} 2>&1",
                shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
            )
            for line in iter(proc.stdout.readline, b''):
                text = line.decode('utf-8', errors='replace').rstrip()
                text = ANSI_RE.sub('', text)  # Strip ANSI color codes
                if text and not text.startswith('[sudo]'):
                    self.log(text)
            proc.wait()
            return proc.returncode == 0
        except Exception as e:
            self.log(f"[✖] Error: {e}")
            return False

    # ─── Button handlers ──────────────────────────────────────────────
    def on_start_clicked(self, btn):
        self.set_status("starting")
        threading.Thread(target=self._do_start, daemon=True).start()

    def on_stop_clicked(self, btn):
        self.set_status("stopping")
        threading.Thread(target=self._do_stop, daemon=True).start()

    def _do_start(self):
        ok = self.run_script(f"{INSTALL_DIR}/start.sh", "Starting Android…")
        if ok:
            self.set_status("running")
        else:
            self.set_status("stopped")
            self.log("[✖] Boot failed.")

    def _do_stop(self):
        ok = self.run_script(f"{INSTALL_DIR}/stop.sh", "Stopping Android…")
        self.set_status("stopped")
        if ok:
            self.log("[✓] Device powered off.")


# ─── Main ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = LauncherWindow()
    app.connect("destroy", Gtk.main_quit)
    app.show_all()
    Gtk.main()
