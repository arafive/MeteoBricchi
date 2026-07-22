#!/bin/bash

rsyncd() {
    rsync -rahzPuv --update --modify-window=1 --info=progress2 "$@"
}

LOCKFILE="/tmp/sync.lock"

# Evita esecuzioni multiple contemporanee
if [ -e "$LOCKFILE" ]; then
    echo "$(date): script già in esecuzione"
    exit 1
fi

trap 'rm -f $LOCKFILE' EXIT
touch "$LOCKFILE"

##########################

DA='/home/cfmi.arpal.org/meteo/QnapDevMeteo/MeteoBricchi/dati2D'
A1='/home/cfmi.arpal.org/daniele.carnevale/Scrivania/MeteoBricchi/.'
rsyncd --include='*/' --include='*.png' --include='*.csv' --include='*.webp' --include='*.json' --exclude='*' meteo@meteo-dev:$DA $A1

##########################

DA='/home/cfmi.arpal.org/meteo/QnapDevMeteo/download-mtg/mtg_fci_hd_nord_italia/web/geocolour/'
A1='/home/cfmi.arpal.org/daniele.carnevale/Scrivania/MeteoBricchi/dati2D/geocolour/.'
rsyncd --include='202*/' --include='202*/**' --exclude='*' meteo@meteo-dev:$DA $A1

##########################

DA='/home/cfmi.arpal.org/meteo/QnapDevMeteo/download-mtg/mtg_fci_hd_nord_italia/web/sandwich/'  
A1='/home/cfmi.arpal.org/daniele.carnevale/Scrivania/MeteoBricchi/dati2D/sandwich/.'
rsyncd --include='202*/' --include='202*/**' --exclude='*' meteo@meteo-dev:$DA $A1

##########################

DA='/home/cfmi.arpal.org/daniele.carnevale/Scrivania/MeteoBricchi/dati1D'
A1='/run/media/daniele.carnevale/Daniele2TB/repo/MeteoBricchi/.'
rsyncd $DA $A1

##########################

DA='/run/media/daniele.carnevale/Daniele2TB/repo/MeteoBricchi/dati1D'
A1='/home/cfmi.arpal.org/daniele.carnevale/Scrivania/MeteoBricchi/.'
rsyncd $DA $A1

##########################

DA='/home/cfmi.arpal.org/daniele.carnevale/Scrivania/MeteoBricchi/dati2D'
A1='/run/media/daniele.carnevale/Daniele2TB/repo/MeteoBricchi/.'
rsyncd $DA $A1

##########################

DA='/run/media/daniele.carnevale/Daniele2TB/repo/MeteoBricchi/dati2D'
A1='/home/cfmi.arpal.org/daniele.carnevale/Scrivania/MeteoBricchi/.'
rsyncd $DA $A1

##########################

DA1='/home/cfmi.arpal.org/daniele.carnevale/Scrivania/MeteoBricchi/dati2D'
DA2='/home/cfmi.arpal.org/daniele.carnevale/Scrivania/MeteoBricchi/dati1D'
A='/media/daniele/Daniele2TB/repo/MeteoBricchi/.'
rsyncd daniele.carnevale@01588-lenovo.cfmi.arpal.org:$DA1 $A
rsyncd daniele.carnevale@01588-lenovo.cfmi.arpal.org:$DA2 $A






















echo "$(date): sincronizzazione completata"

