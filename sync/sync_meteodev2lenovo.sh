#!/bin/bash

rsyncd() {
    rsync -rahzPuv --update --modify-window=1 --info=progress2 "$@"
}

LOCKFILE="/tmp/sync_meteodev2lenovo.lock"

# Evita esecuzioni multiple contemporanee
if [ -e "$LOCKFILE" ]; then
    echo "$(date): script già in esecuzione"
    exit 1
fi

trap 'rm -f $LOCKFILE' EXIT
touch "$LOCKFILE"

##############################################################################

DA='/home/cfmi.arpal.org/meteo/QnapDevMeteo/MeteoBricchi/dati1D'
A='/home/cfmi.arpal.org/daniele.carnevale/Scrivania/MeteoBricchi/.'
rsyncd meteo@meteo-dev:$DA $A

##############################################################################

DA='/home/cfmi.arpal.org/meteo/QnapDevMeteo/MeteoBricchi/dati2D'
A='/home/cfmi.arpal.org/daniele.carnevale/Scrivania/MeteoBricchi/.'
rsyncd meteo@meteo-dev:$DA $A

##############################################################################

DA='/home/cfmi.arpal.org/meteo/QnapDevMeteo/download-mtg/mtg_fci_hd_nord_italia/web/geocolour/'
A='/home/cfmi.arpal.org/daniele.carnevale/Scrivania/MeteoBricchi/dati2D/geocolour/.'
rsyncd --include='202*/' --include='202*/**' --exclude='*' meteo@meteo-dev:$DA $A

##############################################################################

DA='/home/cfmi.arpal.org/meteo/QnapDevMeteo/download-mtg/mtg_fci_hd_nord_italia/web/sandwich/'  
A='/home/cfmi.arpal.org/daniele.carnevale/Scrivania/MeteoBricchi/dati2D/sandwich/.'
rsyncd --include='202*/' --include='202*/**' --exclude='*' meteo@meteo-dev:$DA $A

##############################################################################

DA='/home/cfmi.arpal.org/daniele.carnevale/Scrivania/MeteoBricchi/dati1D'
A='/run/media/daniele.carnevale/Daniele2TB/repo/MeteoBricchi/.'
rsyncd $DA $A

DA='/home/cfmi.arpal.org/daniele.carnevale/Scrivania/MeteoBricchi/dati2D'
A='/run/media/daniele.carnevale/Daniele2TB/repo/MeteoBricchi/.'
rsyncd $DA $A

