#!/bin/bash

rsyncd() {
    rsync -rahzPuv --update --modify-window=1 --info=progress2 "$@"
}

LOCKFILE="/tmp/sync_meteoprod2lenovo.lock"

# Evita esecuzioni multiple contemporanee
if [ -e "$LOCKFILE" ]; then
    echo "$(date): script già in esecuzione"
    exit 1
fi

trap 'rm -f $LOCKFILE' EXIT
touch "$LOCKFILE"

##############################################################################

DA='/home/cfmi.arpal.org/meteo/uv_roberto/plot/*'
A='/home/cfmi.arpal.org/daniele.carnevale/Scrivania/MeteoBricchi/dati1D/dati_osservati/UV/.'
rsyncd meteo@meteo-prod:$DA $A

