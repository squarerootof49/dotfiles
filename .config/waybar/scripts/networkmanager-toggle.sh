#!/bin/zsh
#-----------------------------------------------------------------------------
# seven's custom toggle script for the other stupid network controller script.
#-----------------------------------------------------------------------------

# This just serves as a toggle for the waybar trigger.
if pgrep -f networkmanager.py >/dev/null; then
    pkill -f networkmanager.py
else
    ~/.config/waybar/scripts/networkmanager.py &
fi
