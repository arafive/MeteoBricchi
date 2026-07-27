#!/bin/bash

rsyncd() {
    rsync -rahzPuv --update --modify-window=1 --info=progress2 "$@"
}

LOCKFILE="/tmp/sync_lenovo2daniele.lock"

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

DA='/home/cfmi.arpal.org/daniele.carnevale/Scrivania/MeteoBricchi/dati1D'
A="$RADICE_REPO/."
rsyncd daniele.carnevale@01588-lenovo.cfmi.arpal.org:$DA $A

##############################################################################

DA='/home/cfmi.arpal.org/daniele.carnevale/Scrivania/MeteoBricchi/dati2D'
A="$RADICE_REPO/."
rsyncd daniele.carnevale@01588-lenovo.cfmi.arpal.org:$DA $A

