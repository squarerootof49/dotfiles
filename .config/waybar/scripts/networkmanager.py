#!/usr/bin/env python3

#------------------------------------------
# seven's custom network controller script.
#------------------------------------------

# WARNING: this shit works thanks to miracles bestowed upon me by the python gods themselves. I have no idea how or why this works, it is half vibe coded, and I could not be bothered to make it optimized. It probably sucks, you've been warned.

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
import subprocess
import threading
import time

class WiFiNetwork:
    def __init__(self, ssid, signal_strength, security, connected=False, saved=False):
        self.ssid = ssid
        self.signal_strength = signal_strength
        self.security = security
        self.connected = connected
        self.saved = saved

class WiFiManager:
    def __init__(self):
        self.networks = []
        self.scanning = False
        self.last_scan_time = 0
        self.scan_cooldown = 10

    def should_scan(self):
        """Check if enough time has passed since last scan"""
        current_time = time.time()
        return (current_time - self.last_scan_time) > self.scan_cooldown

    def get_networks(self, force_scan=False):
        """Get available WiFi networks using nmcli"""
        try:
            if force_scan and self.should_scan():
                print("Performing network scan...")
                self.scan()
                self.last_scan_time = time.time()
                time.sleep(3)

            result = subprocess.run(['nmcli', '-t', '-f', 'SSID,SIGNAL,SECURITY', 'dev', 'wifi', 'list'],
                                  capture_output=True, text=True, timeout=10)
            available = {}
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        parts = line.split(':')
                        if len(parts) >= 3 and parts[0]:
                            ssid = parts[0]
                            signal = int(parts[1]) if parts[1] else 0
                            security = parts[2] if parts[2] else 'Open'
                            if ssid not in available or signal > available[ssid]['signal']:
                                available[ssid] = {'signal': signal, 'security': security}

            result = subprocess.run(['nmcli', '-t', '-f', 'NAME,TYPE', 'con', 'show'],
                                  capture_output=True, text=True, timeout=10)
            saved = set()
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        parts = line.split(':')
                        if len(parts) >= 2 and parts[1] == '802-11-wireless':
                            saved.add(parts[0])

            result = subprocess.run(['nmcli', '-t', '-f', 'NAME', 'con', 'show', '--active'],
                                  capture_output=True, text=True, timeout=10)
            connected = None
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line and line in saved:
                        connected = line
                        break

            networks = []
            for ssid, data in available.items():
                is_connected = (ssid == connected)
                is_saved = ssid in saved
                networks.append(WiFiNetwork(ssid, data['signal'], data['security'],
                                          is_connected, is_saved))

            for ssid in saved:
                if ssid not in available:
                    is_connected = (ssid == connected)
                    networks.append(WiFiNetwork(ssid, 0, 'Unknown', is_connected, True))

            return sorted(networks, key=lambda n: (-n.connected, -n.signal_strength))

        except subprocess.TimeoutExpired:
            print("nmcli command timed out")
            return []
        except Exception as e:
            print(f"Error getting networks: {e}")
            return []

    def connect_to_network(self, ssid, password=None):
        """Connect to a network"""
        try:
            if password:
                cmd = ['nmcli', 'dev', 'wifi', 'connect', ssid, 'password', password]
            else:
                cmd = ['nmcli', 'dev', 'wifi', 'connect', ssid]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return result.returncode == 0, result.stderr
        except subprocess.TimeoutExpired:
            return False, "Connection attempt timed out"
        except Exception as e:
            return False, str(e)

    def disconnect(self):
        """Disconnect from current network"""
        try:
            result = subprocess.run(['nmcli', 'dev', 'disconnect', 'wlan0'],
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except:
            return False

    def forget_network(self, ssid):
        """Forget a saved network"""
        try:
            result = subprocess.run(['nmcli', 'con', 'delete', ssid],
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except:
            return False

    def scan(self):
        """Trigger a network scan - use sparingly"""
        try:
            if self.scanning:
                print("Scan already in progress, skipping...")
                return False

            self.scanning = True
            result = subprocess.run(['nmcli', 'dev', 'wifi', 'rescan'],
                                  capture_output=True, text=True, timeout=15)
            success = result.returncode == 0
            self.scanning = False
            return success
        except:
            self.scanning = False
            return False

class PasswordDialog(Gtk.Dialog):
    def __init__(self, parent, ssid):
        super().__init__(title=f"Connect to {ssid}", parent=parent, modal=True)
        self.set_default_size(300, 150)
        self.set_border_width(10)

        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        self.add_button("Connect", Gtk.ResponseType.OK)

        content = self.get_content_area()
        content.set_spacing(10)

        label = Gtk.Label(label=f"Enter password for '{ssid}':")
        label.set_halign(Gtk.Align.START)
        content.pack_start(label, False, False, 0)

        self.entry = Gtk.Entry()
        self.entry.set_visibility(False)
        self.entry.set_placeholder_text("Password")
        self.entry.connect('activate', lambda e: self.response(Gtk.ResponseType.OK))
        content.pack_start(self.entry, False, False, 0)

        show_password = Gtk.CheckButton(label="Show password")
        show_password.connect('toggled', self.on_show_password)
        content.pack_start(show_password, False, False, 0)

        self.show_all()

    def on_show_password(self, checkbox):
        self.entry.set_visibility(checkbox.get_active())

    def get_password(self):
        return self.entry.get_text()

class NetworkManager(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Network manager")
        self.set_default_size(400, 500)
        self.set_border_width(10)
        self.set_resizable(True)

        self.wifi_manager = WiFiManager()
        self.refresh_in_progress = False

        header = Gtk.HeaderBar(title="Network manager")
        header.set_show_close_button(True)
        self.set_titlebar(header)

        self.refresh_btn = Gtk.Button.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.BUTTON)
        self.refresh_btn.set_tooltip_text("Refresh networks")
        self.refresh_btn.connect('clicked', self.on_refresh)
        header.pack_start(self.refresh_btn)

        self.disconnect_btn = Gtk.Button(label="Disconnect")
        self.disconnect_btn.set_sensitive(False)
        self.disconnect_btn.connect('clicked', self.on_disconnect)
        header.pack_end(self.disconnect_btn)

        self.apply_css()

        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main_vbox.set_margin_top(10)
        main_vbox.set_margin_bottom(10)
        main_vbox.set_margin_start(10)
        main_vbox.set_margin_end(10)
        self.add(main_vbox)

        self.status_label = Gtk.Label(label="Loading networks...")
        self.status_label.get_style_context().add_class("section-title")
        self.status_label.set_halign(Gtk.Align.START)
        main_vbox.pack_start(self.status_label, False, False, 0)

        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        main_vbox.pack_start(separator, False, False, 5)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        main_vbox.pack_start(scrolled, True, True, 0)

        self.network_listbox = Gtk.ListBox()
        self.network_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        scrolled.add(self.network_listbox)

        self.connect("key-press-event", self.on_key_press)
        self.connect("destroy", Gtk.main_quit)

        self.refresh_networks(force_scan=False)

    def section_title(self, text):
        label = Gtk.Label(label=text)
        label.get_style_context().add_class("section-title")
        label.set_halign(Gtk.Align.START)
        return label

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.close()

    def apply_css(self):
        css = b"""
        .section-title {
            font-weight: bold;
            font-size: 16px;
            color: #f2cdcd;
        }

        .network-row {
            padding: 8px;
            margin: 2px 0;
        }

        .network-name {
            font-weight: bold;
            font-size: 14px;
        }

        .network-info {
            font-size: 12px;
            opacity: 0.8;
        }

        .connected {
            color: #a6e3a1;
        }

        .signal-excellent {
            color: #a6e3a1;
            font-size: 20px;
            margin-right: 1rem;
        }
        .signal-good {
            color: #f9e2af;
            font-size: 20px;
            margin-right: 1rem;
        }
        .signal-ok {
            color: #eba0ac;
            font-size: 20px;
            margin-right: 1rem;
        }
        .signal-weak {
            color: #f38ba8;
            font-size: 20px;
            margin-right: 1rem;
        }
        """
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def get_signal_icon_and_class(self, signal_strength):
        if signal_strength > 75:
            return "󰤨", "signal-excellent"
        elif signal_strength > 50:
            return "󰤥", "signal-good"
        elif signal_strength > 25:
            return "󰤢", "signal-ok"
        elif signal_strength > 0:
            return "󰤟", "signal-weak"
        else:
            return "󰤯", "signal-weak"

    def create_network_row(self, network):
        """Create a row for a network"""
        row = Gtk.ListBoxRow()
        row.get_style_context().add_class("network-row")

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        hbox.set_margin_start(10)
        hbox.set_margin_end(10)
        hbox.set_margin_top(8)
        hbox.set_margin_bottom(8)
        row.add(hbox)

        signal_icon, signal_class = self.get_signal_icon_and_class(network.signal_strength)
        icon_label = Gtk.Label(label=signal_icon)
        icon_label.get_style_context().add_class(signal_class)
        hbox.pack_start(icon_label, False, False, 0)

        info_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)

        name_label = Gtk.Label(label=network.ssid)
        name_label.get_style_context().add_class("network-name")
        name_label.set_halign(Gtk.Align.START)
        if network.connected:
            name_label.get_style_context().add_class("connected")
        info_vbox.pack_start(name_label, False, False, 0)

        details = []
        if network.connected:
            details.append("Connected")
        elif network.saved:
            details.append("Saved")

        if network.security != 'Open':
            details.append(network.security)
        else:
            details.append("Open")

        if network.signal_strength > 0:
            details.append(f"{network.signal_strength}%")

        detail_text = " • ".join(details)
        detail_label = Gtk.Label(label=detail_text)
        detail_label.get_style_context().add_class("network-info")
        detail_label.set_halign(Gtk.Align.START)
        info_vbox.pack_start(detail_label, False, False, 0)

        hbox.pack_start(info_vbox, True, True, 0)

        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        if network.connected:
            check_label = Gtk.Label(label="✓")
            check_label.get_style_context().add_class("connected")
            button_box.pack_start(check_label, False, False, 0)
        elif network.saved:
            connect_btn = Gtk.Button(label="Connect")
            connect_btn.connect('clicked', lambda b, n=network: self.connect_to_network(n))
            button_box.pack_start(connect_btn, False, False, 0)

            forget_btn = Gtk.Button(label="Forget")
            forget_btn.get_style_context().add_class("destructive-action")
            forget_btn.connect('clicked', lambda b, n=network: self.forget_network(n))
            button_box.pack_start(forget_btn, False, False, 0)
        else:
            connect_btn = Gtk.Button(label="Connect")
            connect_btn.connect('clicked', lambda b, n=network: self.connect_to_network(n))
            button_box.pack_start(connect_btn, False, False, 0)

        hbox.pack_end(button_box, False, False, 0)

        return row

    def refresh_networks(self, force_scan=True):
        """Refresh the network list"""
        if self.refresh_in_progress:
            print("Refresh already in progress, skipping...")
            return

        self.refresh_in_progress = True

        for child in self.network_listbox.get_children():
            self.network_listbox.remove(child)

        if force_scan:
            self.status_label.set_text("Scanning for networks...")
            self.refresh_btn.set_sensitive(False)
        else:
            self.status_label.set_text("Loading networks...")

        def load_networks():
            try:
                networks = self.wifi_manager.get_networks(force_scan=force_scan)
                GLib.idle_add(self.update_network_list, networks)
            except Exception as e:
                print(f"Error in load_networks: {e}")
                GLib.idle_add(self.update_network_list, [])

        thread = threading.Thread(target=load_networks)
        thread.daemon = True
        thread.start()

    def update_network_list(self, networks):
        """Update the network list in the main thread"""
        self.refresh_in_progress = False
        self.refresh_btn.set_sensitive(True)
        connected = any(n.connected for n in networks)
        self.disconnect_btn.set_sensitive(connected)

        if not networks:
            self.status_label.set_text("No networks found")
            return

        connected_count = sum(1 for n in networks if n.connected)
        if connected_count > 0:
            self.status_label.set_text(f"Connected • {len(networks)} network(s) available")
        else:
            self.status_label.set_text(f"{len(networks)} network(s) available")

        for network in networks:
            row = self.create_network_row(network)
            self.network_listbox.add(row)

        self.network_listbox.show_all()

    def connect_to_network(self, network):
        """Connect to a network"""
        if network.security != 'Open' and not network.saved:
            dialog = PasswordDialog(self, network.ssid)
            response = dialog.run()

            if response == Gtk.ResponseType.OK:
                password = dialog.get_password()
                dialog.destroy()

                if password:
                    self.perform_connection(network.ssid, password)
            else:
                dialog.destroy()
        else:
            self.perform_connection(network.ssid)

    def perform_connection(self, ssid, password=None):
        """Actually perform the connection"""
        self.status_label.set_text(f"Connecting to {ssid}...")

        def connect():
            success, error = self.wifi_manager.connect_to_network(ssid, password)
            GLib.idle_add(self.connection_complete, success, error, ssid)

        thread = threading.Thread(target=connect)
        thread.daemon = True
        thread.start()

    def connection_complete(self, success, error, ssid):
        """Handle connection completion"""
        if success:
            self.status_label.set_text(f"Connected to {ssid}")
            self.refresh_networks(force_scan=False)
        else:
            self.status_label.set_text(f"Failed to connect: {error}")

    def forget_network(self, network):
        """Forget a saved network"""
        success = self.wifi_manager.forget_network(network.ssid)
        if success:
            self.status_label.set_text(f"Forgot {network.ssid}")
            self.refresh_networks(force_scan=False)
        else:
            self.status_label.set_text(f"Failed to forget {network.ssid}")

    def on_disconnect(self, button):
        """Disconnect from current network"""
        success = self.wifi_manager.disconnect()
        if success:
            self.status_label.set_text("Disconnected")
            self.refresh_networks(force_scan=False)
        else:
            self.status_label.set_text("Failed to disconnect")

    def on_refresh(self, button):
        """Refresh networks with scan"""
        self.refresh_networks(force_scan=True)

if __name__ == "__main__":
    win = NetworkManager()
    win.show_all()
    Gtk.main()
