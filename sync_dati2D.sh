#!/bin/bash

# Lo rendo eseguibile con: chmod +x sync_meteo-dev.sh
# Problemi si sync con https://chatgpt.com/share/6a05d1e4-5690-83eb-a0ee-7af4cb8117b6

# Directory dove vuoi salvare i file
DEST="/run/media/daniele.carnevale/Daniele2TB/repo/MeteoBricchi"
cd "$DEST" || exit 1
rsync -rahzPuv --update --modify-window=1 --info=progress2 \
    --include='*/' \
    --include='*.png' \
    --include='*.json' \
    --include='*.csv' \
    --exclude='*' \
    /home/cfmi.arpal.org/daniele.carnevale/Scrivania/MeteoBricchi/dati2D .

echo "$(date): sincronizzazione completata"
