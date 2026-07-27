#!/bin/bash

rsyncd() {
    rsync -rahzPuv --update --modify-window=1 --info=progress2 "$@"
}

LOCKFILE="/tmp/sync_meteoprod2daniele.lock"

# Evita esecuzioni multiple contemporanee
if [ -e "$LOCKFILE" ]; then
    echo "$(date): script già in esecuzione"
    exit 1
fi

trap 'rm -f $LOCKFILE' EXIT
touch "$LOCKFILE"

##############################################################################

RADICE_DANIELE='/media/daniele/Daniele2TB/repo/MeteoBricchi'
RADICE_ARPAL='/home/cfmi.arpal.org/daniele.carnevale/Scrivania/MeteoBricchi'

if [ -d "$RADICE_DANIELE" ]; then
    RADICE_REPO="$RADICE_DANIELE"
elif [ -d "$RADICE_ARPAL" ]; then
    RADICE_REPO="$RADICE_ARPAL"
else
    echo "$(date): nessuna delle due cartelle MeteoBricchi trovata, esco."
    exit 1
fi

##############################################################################

DA='/home/cfmi.arpal.org/meteo/uv_roberto/plot/*'
A="$RADICE_REPO/dati1D/dati_osservati/UV/."
rsyncd meteo@meteo-prod:$DA $A

