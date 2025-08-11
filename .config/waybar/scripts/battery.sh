#!/bin/zsh

#------------------------------------------
# seven's custom battery icon thing script.
#------------------------------------------

# This is a quick and random thing made for waybar to output a battery icon depending on the current battery %.

perc=$(upower -i $(upower -e | grep BAT) | grep -E "percentage" | awk '{print $2}' | tr -d '%')

if   [ "$perc" -lt 5 ];  then icon=""
elif [ "$perc" -le 40 ]; then icon=""
elif [ "$perc" -le 60 ]; then icon=""
elif [ "$perc" -le 95 ]; then icon=""
else                          icon=""
fi

echo "$icon $perc%"
