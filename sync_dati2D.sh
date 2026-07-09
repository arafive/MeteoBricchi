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
SOURCE_GEOCOLOUR="meteo@meteo-dev:/home/cfmi.arpal.org/meteo/QnapDevMeteo/download-mtg/mtg_fci_hd_nord_italia/web/geocolour/"
SOURCE_SANDWICH="meteo@meteo-dev:/home/cfmi.arpal.org/meteo/QnapDevMeteo/download-mtg/mtg_fci_hd_nord_italia/web/sandwich/"
RSYNC_OPTS=(-rahzPuv --update --modify-window=1 --info=progress2 --include='*/' --include='*.png' --include='*.csv' --include='*.json' --exclude='*')
RSYNC_OPTS_MTG=(-rahzPuv --update --modify-window=1 --info=progress2 --include='202*/' --include='202*/**' --exclude='*')

DEST_SCRIVANIA="/home/cfmi.arpal.org/daniele.carnevale/Scrivania/MeteoBricchi"
DEST_2TB="/run/media/daniele.carnevale/Daniele2TB/repo/MeteoBricchi"

for DEST in "$DEST_SCRIVANIA" "$DEST_2TB"; do
if [ -d "$DEST" ]; then
        cd "$DEST" || continue
        rsync "${RSYNC_OPTS[@]}" "$SOURCE" .
        mkdir -p dati2D/geocolour dati2D/sandwich
        rsync "${RSYNC_OPTS_MTG[@]}" "$SOURCE_GEOCOLOUR" dati2D/geocolour/.
        rsync "${RSYNC_OPTS_MTG[@]}" "$SOURCE_SANDWICH" dati2D/sandwich/.
    else
        echo "$(date): $DEST non trovata, salto"
    fi
done

##############################################################################
# Sync finale tra le due destinazioni locali (mantiene allineate solo le dati2D)
DATI2D_SCRIVANIA="$DEST_SCRIVANIA/dati2D"
DATI2D_2TB="$DEST_2TB/dati2D"

if [ -d "$DATI2D_SCRIVANIA" ] && [ -d "$DATI2D_2TB" ]; then
    rsync "${RSYNC_OPTS[@]}" "$DATI2D_SCRIVANIA"/ "$DATI2D_2TB"/
    rsync "${RSYNC_OPTS[@]}" "$DATI2D_2TB"/ "$DATI2D_SCRIVANIA"/
else
    echo "$(date): una delle due cartelle dati2D non trovata, salto sync finale"
fi

echo "$(date): sincronizzazione completata"
