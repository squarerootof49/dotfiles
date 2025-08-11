#!/usr/bin/env python3

#----------------------------------------------------------------------------------------
# seven's custom brightness, keyboard backlight and screen temperature controller script.
#----------------------------------------------------------------------------------------

# WARNING: this shit works thanks to miracles bestowed upon me by the python gods themselves. I have no idea how or why this works, it is half vibe coded, and I could not be bothered to make it optimized. It probably sucks, you've been warned.

import subprocess
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk

def device_exists(device):
    try:
        subprocess.check_output(["brightnessctl", "-d", device, "info"], text=True)
        return True
    except subprocess.CalledProcessError:
        return False

def get_brightness(device):
    try:
        out = subprocess.check_output(["brightnessctl", "-d", device, "get"], text=True).strip()
        max_out = subprocess.check_output(["brightnessctl", "-d", device, "max"], text=True).strip()
        return int(out) / int(max_out) * 100
    except:
        return 0

def set_brightness(device, value):
    subprocess.run(["brightnessctl", "-d", device, "set", f"{round(value)}%"])

def get_temp():
    return 6500

def set_temp(value):
    subprocess.run(["pkill", "-f", "gammastep"])
    subprocess.Popen(["gammastep", "-O", str(int(value))])

class LightControl(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Light control")
        self.set_default_size(465, 370)
        self.set_size_request(465, 370)
        self.set_resizable(True)

        header = Gtk.HeaderBar(title="Light control")
        header.set_show_close_button(True)
        self.set_titlebar(header)

        self.apply_css()

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_top(20)
        vbox.set_margin_bottom(20)
        vbox.set_margin_start(20)
        vbox.set_margin_end(20)
        self.add(vbox)

        if device_exists("intel_backlight"):
            vbox.pack_start(self.section_title("  Screen brightness"), False, False, 0)
            brightness_adj = Gtk.Adjustment(value=get_brightness("intel_backlight"), lower=1, upper=100, step_increment=1)
            brightness_slider = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=brightness_adj)
            brightness_slider.set_digits(0)
            brightness_slider.connect("value-changed", lambda w: set_brightness("intel_backlight", w.get_value()))
            vbox.pack_start(brightness_slider, False, False, 0)
            vbox.pack_start(self.separator_line(), False, False, 10)

        if device_exists("asus::kbd_backlight"):
            vbox.pack_start(self.section_title("  Keyboard backlight"), False, False, 0)
            kb_adj = Gtk.Adjustment(value=get_brightness("asus::kbd_backlight"), lower=0, upper=100, step_increment=1)
            kb_slider = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=kb_adj)
            kb_slider.set_digits(0)
            kb_slider.connect("value-changed", lambda w: set_brightness("asus::kbd_backlight", w.get_value()))
            vbox.pack_start(kb_slider, False, False, 0)
            vbox.pack_start(self.separator_line(), False, False, 10)

        vbox.pack_start(self.section_title("  Screen temperature"), False, False, 0)
        temp_adj = Gtk.Adjustment(value=get_temp(), lower=3000, upper=6500, step_increment=100)
        temp_slider = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=temp_adj)
        temp_slider.set_digits(0)
        temp_slider.connect("value-changed", lambda w: set_temp(w.get_value()))
        vbox.pack_start(temp_slider, False, False, 0)

        self.connect("key-press-event", self.on_key_press)
        self.connect("destroy", Gtk.main_quit)

    def section_title(self, text):
        label = Gtk.Label(label=text)
        label.get_style_context().add_class("section-title")
        label.set_halign(Gtk.Align.START)
        return label

    def separator_line(self):
        return Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)

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

if __name__ == "__main__":
    win = LightControl()
    win.show_all()
    Gtk.main()
