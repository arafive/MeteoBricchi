"""
Scarica dalla pagina "Alps by Davide"
(https://cmi-servizi.arpal.liguria.it/alps/) le immagini .png delle
localita' elencate in sites.json, e le archivia insieme al file stesso in:

    dati1D/Alps/<anno>/<mese>/<giorno>/<nome>.png
    dati1D/Alps/<anno>/<mese>/<giorno>/sites.json

usando la data di ultima modifica di sites.json (header HTTP
Last-Modified), non la data odierna: cosi' rilanciando lo script un altro
giorno (es. da cron) i file vecchi non vengono sovrascritti, finiscono
semplicemente in una cartella diversa. Tutte le immagini di una stessa
esecuzione finiscono nella cartella del giorno di sites.json (stessa
cartella, in un colpo solo): e' cosi' che il backend sa, per ogni giorno,
quali localita' erano valide quel giorno (leggendo il sites.json di quella
cartella) e quali immagini esistono davvero.

Uso:
    python download_alps.py [--destinazione dati1D/Alps]

Richiede: requests
    pip install requests --break-system-packages
"""

import argparse
import os
import re
import sys
from datetime import datetime
from email.utils import parsedate_to_datetime

import requests

URL_BASE = "https://cmi-servizi.arpal.liguria.it/alps/"

# Nome di una localita' valido (stesso pattern di NOME_SITO_ALPS_RE in
# app.py): protegge da path traversal se sites.json contenesse un "name"
# inatteso.
NOME_SITO_RE = re.compile(r"^[A-Za-z0-9_]+$")


def data_da_intestazione(risposta):
    """Data di ultima modifica di una risposta HTTP (header
    Last-Modified), o None se l'header manca o non e' leggibile."""
    ultima_modifica = risposta.headers.get("Last-Modified")
    if not ultima_modifica:
        return None
    try:
        return parsedate_to_datetime(ultima_modifica).replace(tzinfo=None)
    except (TypeError, ValueError):
        return None


def scarica_sites_json(cartella_destinazione):
    """Scarica sites.json, lo salva in dati1D/Alps/AAAA/MM/GG/ (cartella
    del suo giorno, dedotta dall'header HTTP Last-Modified) e ne ritorna
    il contenuto gia' decodificato (lista di localita'), insieme alla data
    del giorno da usare anche per le immagini: cosi' sites.json e le png
    finiscono sempre nella STESSA cartella, in una sola esecuzione."""
    risposta = requests.get(URL_BASE + "sites.json", timeout=30)
    risposta.raise_for_status()

    data = data_da_intestazione(risposta)
    if data is None:
        print("  attenzione: nessun header Last-Modified per sites.json, uso la data odierna", file=sys.stderr)
        data = datetime.now()

    cartella = os.path.join(
        cartella_destinazione, f"{data.year:04d}", f"{data.month:02d}", f"{data.day:02d}",
    )
    os.makedirs(cartella, exist_ok=True)
    percorso = os.path.join(cartella, "sites.json")
    nuovo = not os.path.exists(percorso)
    if nuovo:
        with open(percorso, "wb") as f:
            f.write(risposta.content)

    return risposta.json(), data, nuovo


def scarica_file(url_base, nome_file, data, cartella_destinazione):
    """Scarica un singolo file (png o sites.json) in
    dati1D/Alps/AAAA/MM/GG/<nome_file>, nella cartella del giorno indicato
    da `data`. Se il file e' gia' presente (stessa esecuzione rilanciata)
    non lo riscarica."""
    cartella = os.path.join(
        cartella_destinazione,
        f"{data.year:04d}",
        f"{data.month:02d}",
        f"{data.day:02d}",
    )
    os.makedirs(cartella, exist_ok=True)
    percorso = os.path.join(cartella, nome_file)

    if os.path.exists(percorso):
        return percorso, False  # gia' presente

    risposta = requests.get(url_base + nome_file, timeout=30)
    risposta.raise_for_status()
    with open(percorso, "wb") as f:
        f.write(risposta.content)
    return percorso, True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--destinazione",
        default=os.path.join("dati1D", "Alps"),
        help="Cartella base di archiviazione (default: dati1D/Alps)",
    )
    args = parser.parse_args()

    siti, data, sites_nuovo = scarica_sites_json(args.destinazione)
    print(f"sites.json: {len(siti)} localita' ({'scaricato' if sites_nuovo else 'gia presente'})")

    scaricati = 1 if sites_nuovo else 0
    gia_presenti = 0 if sites_nuovo else 1
    errori = 0

    for sito in siti:
        nome = sito.get("name", "")
        if not NOME_SITO_RE.match(nome):
            print(f"  attenzione: nome localita' non valido ({nome!r}), salto", file=sys.stderr)
            errori += 1
            continue
        try:
            percorso, nuovo = scarica_file(
                URL_BASE, f"{nome}.png", data, args.destinazione
            )
            if nuovo:
                print(f"  scaricata: {percorso}")
                scaricati += 1
            else:
                print(f"  gia' presente: {percorso}")
                gia_presenti += 1
        except requests.RequestException as e:
            print(f"  ERRORE su {nome}.png: {e}", file=sys.stderr)
            errori += 1

    print(
        f"Fatto: {scaricati} scaricati, {gia_presenti} gia' presenti, "
        f"{errori} errori"
    )


if __name__ == "__main__":
    main()
