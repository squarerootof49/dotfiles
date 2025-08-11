#!/bin/zsh
#-----------------------------------------------------------------------
# seven's custom toggle script for the other stupid lightcontrol script.
#-----------------------------------------------------------------------

# This just serves as a toggle for the waybar trigger.
if pgrep -f lightcontrol.py >/dev/null; then
    pkill -f lightcontrol.py
else
    ~/.config/waybar/scripts/lightcontrol.py &
fi
