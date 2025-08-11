#!/usr/bin/env python3

#-----------------------------------------
# seven's custom volume controller script.
#-----------------------------------------

# WARNING: this shit works thanks to miracles bestowed upon me by the python gods themselves. I have no idea how or why this works, it is half vibe coded, and I could not be bothered to make it optimized. It probably sucks, you've been warned.

import subprocess
import gi, re
gi.require_version("Gtk", "3.0")
gi.require_version("GLib", "2.0")
from gi.repository import Gtk, Gdk, GLib

VOLUME_REGEX = re.compile(r"Volume:.*?/\s*([0-9]+)%")

def parse_pactl_list(target, block_start):
    output = subprocess.check_output(["pactl", "list", target], text=True)
    devices, current = [], None
    for line in output.splitlines():
        line = line.strip()
        if line.startswith(block_start):
            if current:
                devices.append(current)
            current = {"id": line.split("#")[1], "name": "", "vol": 0}
        elif line.startswith("Name:") and current:
            current["name"] = line.split(":", 1)[1].strip()
        elif line.startswith("application.name") and current:
            current["name"] = line.split("=", 1)[1].strip().strip('"')
        elif line.startswith("Volume:") and current:
            m = VOLUME_REGEX.search(line)
            if m:
                current["vol"] = int(m.group(1))
    if current:
        devices.append(current)
    return devices

def get_sinks(): return parse_pactl_list("sinks", "Sink #")
def get_sources(): return parse_pactl_list("sources", "Source #")
def get_playbacks(): return parse_pactl_list("sink-inputs", "Sink Input #")

def set_volume(sink_id, value, is_source=False, is_playback=False):
    cmd = ["pactl"]
    if is_playback:
        cmd += ["set-sink-input-volume", sink_id]
    elif is_source:
        cmd += ["set-source-volume", sink_id]
    else:
        cmd += ["set-sink-volume", sink_id]
    cmd.append(f"{int(value)}%")
    subprocess.run(cmd)

class VolumeControl(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Volume control")
        self.set_default_size(200, 500)
        self.set_size_request(200, 500)
        self.set_resizable(True)

        header = Gtk.HeaderBar(title="Volume control")
        header.set_show_close_button(True)
        self.set_titlebar(header)
        self.apply_css()

        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.add(self.scrolled)

        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        self.vbox.set_margin_top(20)
        self.vbox.set_margin_bottom(20)
        self.vbox.set_margin_start(20)
        self.vbox.set_margin_end(20)
        self.scrolled.add(self.vbox)

        self.refresh_ui()

        self.connect("key-press-event", self.on_key_press)
        self.connect("destroy", Gtk.main_quit)

        self.proc = subprocess.Popen(["pactl", "subscribe"], stdout=subprocess.PIPE, text=True)
        GLib.io_add_watch(self.proc.stdout, GLib.IO_IN, self.on_pactl_event)

    def refresh_ui(self):
        for child in self.vbox.get_children():
            self.vbox.remove(child)

        self.vbox.pack_start(self.section_title("  Output devices"), False, False, 0)
        for sink in get_sinks():
            self._add_device_slider(sink, is_source=False, is_playback=False)
        self.vbox.pack_start(self.separator_line(), False, False, 10)

        self.vbox.pack_start(self.section_title("  Input devices"), False, False, 0)
        for source in get_sources():
            self._add_device_slider(source, is_source=True, is_playback=False)
        self.vbox.pack_start(self.separator_line(), False, False, 10)

        self.vbox.pack_start(self.section_title("▶  Playback streams"), False, False, 0)
        for pb in get_playbacks():
            self._add_device_slider(pb, is_source=False, is_playback=True)

        self.show_all()

    def section_title(self, text):
        label = Gtk.Label(label=text)
        label.get_style_context().add_class("section-title")
        label.set_halign(Gtk.Align.START)
        return label

    def separator_line(self):
        return Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)

    def _add_device_slider(self, device, is_source=False, is_playback=False):
        label = Gtk.Label(label=f"{device_icon(is_source, is_playback)}  {device['name']}")
        label.set_halign(Gtk.Align.START)
        self.vbox.pack_start(label, False, False, 0)

        adj = Gtk.Adjustment(value=device['vol'], lower=0, upper=150, step_increment=1)
        slider = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adj)
        slider.set_digits(0)
        slider.set_hexpand(True)
        slider.connect("value-changed",
            lambda w, d_id=device["id"], src=is_source, pb=is_playback: set_volume(d_id, w.get_value(), src, pb))
        self.vbox.pack_start(slider, False, False, 0)

    def on_pactl_event(self, source, condition):
        line = source.readline()
        if "sink" in line or "source" in line or "input" in line:
            self.refresh_ui()
        return True

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
        """
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

def device_icon(is_source, is_playback):
    if is_playback: return "▶"
    elif is_source: return ""
    else: return ""

if __name__ == "__main__":
    win = VolumeControl()
    win.show_all()
    Gtk.main()
