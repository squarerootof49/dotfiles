#!/bin/zsh
#------------------------------------------------------------------------
# seven's custom toggle script for the other stupid volumecontrol script.
#------------------------------------------------------------------------

# This just serves as a toggle for the waybar trigger.
if pgrep -f volumecontrol.py >/dev/null; then
    pkill -f volumecontrol.py
else
    ~/.config/waybar/scripts/volumecontrol.py &
fi
