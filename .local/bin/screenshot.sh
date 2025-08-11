#!/bin/bash
DIR="$HOME/Pictures/Screenshots"
mkdir -p "$DIR"

FILENAME="$DIR/$(date +'%Y-%m-%d_%H-%M-%S').png"

# Select area → save → annotate in Swappy
grim -g "$(slurp)" - | tee "$FILENAME" | swappy -f -

# Copy final screenshot to clipboard
wl-copy < "$FILENAME"
