
import os
import sys
import requests

import pandas as pd

from pathlib import Path

sys.path.insert(0, os.path.expanduser('~/.config'))
from config_percorsi_Daniele import CARTELLA_REPO_ROOT

cartella_lavoro = os.path.join(CARTELLA_REPO_ROOT, 'MeteoBricchi')
os.chdir(cartella_lavoro)

url_immagini = [
    "https://www.arpal.liguria.it/contenuti_statici/pubblicazioni/media_giornaliera_liguria/prec_media.png",
    "https://www.arpal.liguria.it/contenuti_statici/pubblicazioni/media_giornaliera_liguria/temp_media.png",
    "https://www.arpal.liguria.it/contenuti_statici/pubblicazioni/SST/SST.png",
    "https://www.arpal.liguria.it/contenuti_statici/pubblicazioni/SST/SST_ANOMALY.png",
]

cartelle_immagini = [
    'prec_media',
    'temp_media',
    'SST',
    'SST_ANOMALY'
    ]

oggi = pd.Timestamp.today().normalize()


headers = {"User-Agent": "Mozilla/5.0"}

for cartella, url in zip(cartelle_immagini, url_immagini):
    cartella_output = Path(f"dati1D/dati_osservati/{cartella}/{oggi.strftime('%Y/%m/%d')}")
    os.makedirs(cartella_output, exist_ok=True)
    
    nome_file = f"{cartella}_{oggi.strftime('%Y-%m-%d')}.png"
    percorso = cartella_output / nome_file
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    percorso.write_bytes(r.content)
    print(f"Scaricato: {nome_file}")
    
print('\n\nDone')