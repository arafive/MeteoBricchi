#!/bin/bash

# Lo rendo eseguibile con: chmod +x sync_meteo-dev.sh
# Problemi si sync con https://chatgpt.com/share/6a05d1e4-5690-83eb-a0ee-7af4cb8117b6

LOCKFILE="/tmp/sync_dati2D.lock"

# Evita esecuzioni multiple contemporanee
if [ -e "$LOCKFILE" ]; then
    echo "$(date): script già in esecuzione"
    exit 1
fi

trap "rm -f $LOCKFILE" EXIT
touch "$LOCKFILE"

##############################################################################
SOURCE="meteo@meteo-dev:/home/cfmi.arpal.org/meteo/QnapDevMeteo/MeteoBricchi/dati2D"
RSYNC_OPTS=(-rahzPuv --update --modify-window=1 --info=progress2 --include='*/' --include='*.png' --include='*.csv' --include='*.json' --exclude='*')

for DEST in "/home/cfmi.arpal.org/daniele.carnevale/Scrivania/MeteoBricchi" "/run/media/daniele.carnevale/Daniele2TB/repo/MeteoBricchi"; do
    if [ -d "$DEST" ]; then
        cd "$DEST" && rsync "${RSYNC_OPTS[@]}" "$SOURCE" .
    else
        echo "$(date): $DEST non trovata, salto"
    fi
done

echo "$(date): sincronizzazione completata"

