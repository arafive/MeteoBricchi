import re
import os
import glob
import json
import datetime

import numpy as np
import pandas as pd
import shapefile
from pyproj import Transformer
from flask import Flask, render_template, jsonify, abort, request, send_file

app = Flask(__name__)

# Cartelle
CARTELLA_COORD = os.path.join(os.path.dirname(__file__), "coordinate")
CARTELLA_SERIE = os.path.join(os.path.dirname(__file__), "dati1D")
# Osservati (dati veri, non di un modello): MeteoBricchi/../QRF/osservati/<codice>.csv
CARTELLA_OSSERVATI = os.path.join(
    os.path.dirname(__file__), "..", "QRF", "osservati"
)
# Il CSV di QRF/osservati/<codice>.csv contiene TUTTE le variabili osservate
# insieme: per ogni serie si prendono solo le colonne elencate qui (nome
# colonna nel CSV -> nome da mostrare nel grafico). Una colonna assente nel
# file per quella stazione viene semplicemente saltata (non sono sempre
# tutte presenti, es. puo' mancare TEMPX).
# vento e umidita sono segnaposto: sostituisci "VENTOM"/"RAFFICAM"/"UMIDM"
# con i nomi reali delle colonne quando li conosci.
COLONNE_OSSERVATI_PER_SERIE = {
    "temperatura": {
        "TEMPM": "Obs media",
        "TEMPN": "Obs minima",
        "TEMPX": "Obs massima",
    },
    "vento": {
        "WSPDM": "Obs vento",
        "WSPDX": "Obs raffica",
        "WDIRP": "Obs direzione",
    },
    "umidita": {
        "REHUM": "Obs media",
    },
}
CARTELLA_CAMPI = os.path.join(os.path.dirname(__file__), "dati2D")
# valore: (cartella, estensione dei frame, mimetype da servire)
CARTELLE_RADAR = {
    "radar": (os.path.join(CARTELLA_CAMPI, "radar_sri"), "webp", "image/webp"),
    "riflettivita": (os.path.join(CARTELLA_CAMPI, "radar_vmi"), "webp", "image/webp"),
    "vert_int_liq": (os.path.join(CARTELLA_CAMPI, "radar_vil"), "webp", "image/webp"),
    "vil-dens": (os.path.join(CARTELLA_CAMPI, "radar_vil-dens"), "webp", "image/webp"),
    # "convergenze" e' diventato un campo virtuale lato frontend con tre
    # prodotti scelti dall'utente (RH, convergenze del vento, cumulata): i
    # tre PNG vivono nella stessa cartella, distinti solo dal prefisso del
    # nome file (vedi CAMPI_PREFISSO_FRAME).
    "convergenze_vento": (os.path.join(CARTELLA_CAMPI, "convergenze2D_obs"), "png", "image/png"),
    "convergenze_cum": (os.path.join(CARTELLA_CAMPI, "convergenze2D_obs"), "png", "image/png"),
    "convergenze_rh": (os.path.join(CARTELLA_CAMPI, "convergenze2D_obs"), "png", "image/png"),
    "caldo_obs": (os.path.join(CARTELLA_CAMPI, "heatindex2D_obs"), "png", "image/png"),
    "freddo_obs": (os.path.join(CARTELLA_CAMPI, "windchill2D_obs"), "png", "image/png"),
    "caldo_prev": (os.path.join(CARTELLA_CAMPI, "heatindex2D_prev", "ecita"), "png", "image/png"),
    "freddo_prev": (os.path.join(CARTELLA_CAMPI, "windchill2D_prev", "ecita"), "png", "image/png"),
}
CARTELLA_FULMINI = os.path.join(CARTELLA_CAMPI, "fulmini")
# Prodotti satellite: stessa idea di CARTELLE_RADAR, ma frame in .webp e
# cadenza di 10 minuti invece di 5.
CARTELLE_SATELLITE = {
    "geocolour": os.path.join(CARTELLA_CAMPI, "geocolour"),
    "sandwich": os.path.join(CARTELLA_CAMPI, "sandwich"),
}
# Echo Top: stessa idea di CARTELLE_SATELLITE, ma il "prodotto" selezionabile
# e' il livello di soglia in dBZ (radar_etp/<livello>/AAAA/MM/GG/*.webp).
CARTELLA_ECHOTOP = os.path.join(CARTELLA_CAMPI, "radar_etp")
# Confini geografici statici (shapefile), overlay opzionali sulla mappa.
LIVELLI_ECHOTOP_VALIDI = {"18", "35", "45"}
# Ogni sottocartella contiene UN solo .shp (nome variabile: si trova per
# estensione) + i sidecar .dbf/.shx/.prj/.cpg.
CARTELLA_SHAPEFILE = os.path.join(os.path.dirname(__file__), "shapefile")
SHAPEFILE_VALIDI = {"aree", "bacini", "comprensori", "comuni", "regioni"}
# nome -> GeoJSON gia' convertito (i file non cambiano a runtime)
_cache_shapefile = {}

# Colonne LON/LAT/DTRFSEC del CSV fulmini gia' moltiplicate per 10000
# (interi): vanno riportate in unita' reali (gradi/secondi) dividendo per
# 10000 prima dell'uso. Prima del fix allo script di generazione, DTRFSEC
# finiva con un fattore diverso (equivalente a *10) per via di un bug nella
# conversione data->secondi (vedi cronologia): coi CSV rigenerati dopo il
# fix, usa correttamente lo stesso fattore di LON/LAT.
FATTORE_FULMINI = 10000.0

# Valore sentinella usato nei CSV per i dati mancanti
NODATA = -999

# SERIE = dati 1D (serie temporali su stazioni puntuali): sottocartelle di dati1D/
SERIE_VALIDE = {"vento", "temperatura", "umidita", "pioggia"}
# CAMPO = dati 2D (griglia lat/lon): sottocartelle di dati2D/ - per ora solo il bottone
CAMPI_VALIDI = {"radar", "riflettivita", "vert_int_liq", "vil-dens", "fulmini"}


def trova_frame(cartella, estensione):
    """File gia' pronti in <cartella>/AAAA/MM/GG/*.<estensione>, ordinati
    cronologicamente (il nome file e' ordinabile lessicograficamente)."""
    return sorted(glob.glob(os.path.join(cartella, "*", "*", "*", f"*.{estensione}")))


def trova_per_nome(cartella, nome, estensione):
    """Cerca <nome>.<estensione> dentro <cartella>/AAAA/MM/GG/. Il nome
    contiene gia' la data (vedi NOME_FRAME_RE), quindi il percorso diretto
    <cartella>/AAAA/MM/GG/<nome>.<estensione> e' quasi sempre quello giusto:
    lo tento per primo (una sola stat, niente glob). Se il file non c'e' li'
    puo' essere per un piccolo sfasamento fra nome e sottocartella reale
    (es. frame generati a cavallo di mezzanotte): in quel caso ripiego sulla
    ricerca esaustiva con la glob, come prima."""
    m = NOME_FRAME_RE.match(nome)
    if m:
        aaaa, mm, gg, _ = m.groups()
        percorso_diretto = os.path.join(
            cartella, aaaa, mm, gg, f"{nome}.{estensione}")
        if os.path.isfile(percorso_diretto):
            return percorso_diretto

    corrispondenze = glob.glob(
        os.path.join(cartella, "*", "*", "*", f"{nome}.{estensione}"))
    return corrispondenze[0] if corrispondenze else None


def trova_shp(cartella):
    """C'e' uno e un solo .shp per sottocartella (il nome puo' variare): lo
    trovo per estensione, senza doverlo conoscere in anticipo."""
    trovati = glob.glob(os.path.join(cartella, "*.shp"))
    return trovati[0] if trovati else None


def _riproietta_coordinate(coord, trasforma):
    """Riproietta ricorsivamente le coordinate di una geometria GeoJSON
    (Point/LineString/Polygon/Multi*): scende nelle liste annidate finche'
    non trova una coppia (x, y) da trasformare."""
    if isinstance(coord[0], (int, float)):
        x, y = trasforma(coord[0], coord[1])
        return [x, y]
    return [_riproietta_coordinate(c, trasforma) for c in coord]


def _valore_json_sicuro(v):
    """I campi degli attributi shapefile possono contenere date: le
    trasformo in stringa ISO, altrimenti jsonify si romperebbe."""
    if isinstance(v, (datetime.date, datetime.datetime)):
        return v.isoformat()
    return v


def leggi_shapefile_geojson(nome):
    """Legge shapefile/<nome>/*.shp e lo converte in GeoJSON in EPSG:4326
    (WGS84), pronto per L.geoJSON in Leaflet. La proiezione sorgente viene
    letta dal sidecar .prj; l'encoding dei campi testo dal sidecar .cpg.
    Tenuto in cache: i file non cambiano mentre il server e' in esecuzione.
    """
    if nome in _cache_shapefile:
        return _cache_shapefile[nome]

    percorso_shp = trova_shp(os.path.join(CARTELLA_SHAPEFILE, nome))
    if percorso_shp is None:
        return None
    base = os.path.splitext(percorso_shp)[0]

    percorso_prj = base + ".prj"
    if os.path.exists(percorso_prj):
        with open(percorso_prj) as f:
            trasforma = Transformer.from_crs(
                f.read(), "EPSG:4326", always_xy=True).transform
    else:
        def trasforma(x, y):
            return x, y

    percorso_cpg = base + ".cpg"
    codifica = "utf-8"
    if os.path.exists(percorso_cpg):
        with open(percorso_cpg) as f:
            codifica = f.read().strip() or "utf-8"

    try:
        feature = _costruisci_feature_shapefile(
            percorso_shp, codifica, trasforma)
    except UnicodeDecodeError:
        # Niente .cpg (o .cpg sbagliato) e non e' UTF-8: probabile shapefile
        # "vecchio stile" (ArcGIS/MapInfo su Windows), quasi sempre
        # Latin-1/CP1252. Latin-1 non solleva mai UnicodeDecodeError (mappa
        # tutti i 256 valori di byte), quindi e' un ripiego sicuro.
        feature = _costruisci_feature_shapefile(
            percorso_shp, "latin-1", trasforma)

    geojson = {"type": "FeatureCollection", "features": feature}
    _cache_shapefile[nome] = geojson
    return geojson


def _costruisci_feature_shapefile(percorso_shp, codifica, trasforma):
    """Legge shape + attributi con una data codifica e li converte in una
    lista di Feature GeoJSON. Solleva UnicodeDecodeError se la codifica e'
    sbagliata (i campi testo del .dbf non decodificano)."""
    with shapefile.Reader(percorso_shp, encoding=codifica) as lettore:
        campi = [c[0] for c in lettore.fields[1:]]  # [0] = DeletionFlag
        feature = []
        for forma in lettore.shapeRecords():
            geom = forma.shape.__geo_interface__
            if geom.get("coordinates"):
                geom = dict(geom, coordinates=_riproietta_coordinate(
                    geom["coordinates"], trasforma))
            feature.append({
                "type": "Feature",
                "geometry": geom,
                "properties": {
                    k: _valore_json_sicuro(v)
                    for k, v in zip(campi, forma.record)
                },
            })
        return feature


# Per ora c'e' un solo modello di allenamento; in futuro ce ne saranno altri,
# selezionabili dal plot (come Geocolour/Sandwich per il satellite).
MODELLI_SERIE_VALIDI = {"ecita"}
MODELLO_SERIE_PREDEFINITO = "ecita"


def percorso_serie_stazione(serie, codice, d, modello=MODELLO_SERIE_PREDEFINITO):
    """Percorso del CSV di una SERIE 1D per una stazione e una data:
    dati1D/<serie>/<modello>/YYYY/mm/dd/<codice>.csv"""
    return os.path.join(
        CARTELLA_SERIE, serie, modello,
        f"{d.year:04d}", f"{d.month:02d}", f"{d.day:02d}",
        f"{codice}.csv",
    )


def leggi_stazioni(serie):
    """Legge il CSV delle coordinate per una SERIE 1D (coordinate/<serie>/*.csv)
    e restituisce la lista delle stazioni. Lista vuota se il file non c'è."""
    # Prende il primo file .csv presente nella sottocartella della serie
    file_csv = sorted(glob.glob(os.path.join(CARTELLA_COORD, serie, "*.csv")))
    if not file_csv:
        return []

    # sep=None -> rileva automaticamente il separatore (tab o virgola)
    df = pd.read_csv(file_csv[0], sep=',', engine="python")

    # La prima colonna (codice stazione) non ha intestazione nel file
    df = df.rename(columns={df.columns[0]: "Codice"})

    stazioni = [
        {
            "codice": str(riga["Codice"]),
            "nome": str(riga["Name"]),
            "lat": float(riga["Latitude"]),
            "lon": float(riga["Longitude"]),
            # Altitude può mancare o essere vuota -> None (in JSON null)
            "quota": (
                None if pd.isna(riga.get("Altitude")) else float(
                    riga["Altitude"])
            ),
        }
        for _, riga in df.iterrows()
    ]
    return stazioni


# Localita' Alps (sito esterno "Alps by Davide"): niente piu' richieste di
# rete a runtime. download_alps.py scarica periodicamente le png e
# sites.json in dati1D/Alps/AAAA/MM/GG/ (stesso schema di cartelle di
# percorso_serie_stazione), il backend si limita a leggerle da li'.
CARTELLA_ALPS = os.path.join(CARTELLA_SERIE, "Alps")
NOME_SITO_ALPS_RE = re.compile(r"^[A-Za-z0-9_]+$")


def percorso_cartella_alps(d):
    """Cartella del giorno per le localita' Alps: dati1D/Alps/AAAA/MM/GG,
    popolata da download_alps.py (sites.json + le png scaricate quel
    giorno)."""
    return os.path.join(
        CARTELLA_ALPS, f"{d.year:04d}", f"{d.month:02d}", f"{d.day:02d}"
    )


def leggi_siti_alps(d):
    """Legge sites.json del giorno d (vuoto se quel giorno non e' mai stato
    scaricato) e tiene solo le localita' la cui immagine e' stata
    effettivamente scaricata quel giorno: sono le uniche "disponibili" per
    quella data (stesso concetto di leggi_stazioni + disponibile, ma qui il
    file JSON stesso puo' avere localita' diverse giorno per giorno)."""
    cartella = percorso_cartella_alps(d)
    percorso_sites = os.path.join(cartella, "sites.json")
    if not os.path.exists(percorso_sites):
        return []
    with open(percorso_sites, encoding="utf-8") as f:
        siti = json.load(f)
    return [
        s for s in siti
        if os.path.exists(os.path.join(cartella, s["name"] + ".png"))
    ]


# Mappe giornaliere gia' pronte (PNG), come le foto Alps ma senza localita':
# una sola immagine per l'intera regione, una per giorno. Chiave = "serie"
# del bottone menu' (data-serie), valore = nome della sottocartella di
# dati1D/dati_osservati/ e prefisso del file (uguali per ognuna):
# dati1D/dati_osservati/<nome>/AAAA/MM/GG/<nome>_AAAA-MM-GG.png
CARTELLA_OSSERVATI_GIORNALIERI = os.path.join(CARTELLA_SERIE, "dati_osservati")
IMMAGINI_MEDIA_GIORNALIERA = {
    "temp_media": "temp_media",
    "prec_media": "prec_media",
    "sst": "SST",
    "sst_anomaly": "SST_ANOMALY",
}


def percorso_immagine_media_giornaliera(serie, d):
    nome = IMMAGINI_MEDIA_GIORNALIERA[serie]
    return os.path.join(
        CARTELLA_OSSERVATI_GIORNALIERI, nome,
        f"{d.year:04d}", f"{d.month:02d}", f"{d.day:02d}",
        f"{nome}_{d.year:04d}-{d.month:02d}-{d.day:02d}.png",
    )


# UV osservato: a differenza delle mappe giornaliere qui sopra, esiste solo
# per due stazioni puntuali (non un'unica immagine regionale) e un file ogni
# 30 minuti (non uno al giorno). Le coordinate sono le stesse gia' lette per
# la SERIE "temperatura" (stessa rete di stazioni fisiche), filtrate alle
# due disponibili per l'UV.
# dati1D/dati_osservati/UV/<codice>/AAAA/MM/GG/AAAA-MM-GG_HHMM.png
CARTELLA_UV = os.path.join(CARTELLA_OSSERVATI_GIORNALIERI, "UV")
STAZIONI_UV = {"CFUNZ", "SPZIA"}


def percorso_immagine_uv(codice, dt):
    """dt e' un datetime (non date): serve anche l'ora, essendo un file ogni
    30 minuti."""
    return os.path.join(
        CARTELLA_UV, codice,
        f"{dt.year:04d}", f"{dt.month:02d}", f"{dt.day:02d}",
        f"{dt.year:04d}-{dt.month:02d}-{dt.day:02d}_{dt.hour:02d}{dt.minute:02d}.png",
    )


def ultima_immagine_uv_disponibile(codice, dt):
    """Istante dell'ultimo file UV disponibile per la stazione, non
    successivo a dt: se manca il file esatto per l'istante richiesto, la
    foto da mostrare per prima e' comunque l'ultima buona invece che
    un'immagine mancante. None se non c'e' proprio nulla prima di dt."""
    frame = sorted(glob.glob(
        os.path.join(CARTELLA_UV, codice, "*", "*", "*", "*.png")))
    nome_richiesto = dt.strftime("%Y-%m-%d_%H%M")
    frame = [
        p for p in frame
        if os.path.splitext(os.path.basename(p))[0] <= nome_richiesto
    ]
    if not frame:
        return None
    nome = os.path.splitext(os.path.basename(
        frame[-1]))[0]  # "AAAA-MM-GG_HHMM"
    return datetime.datetime.strptime(nome, "%Y-%m-%d_%H%M")


@app.route("/")
def index():
    # Le stazioni non vengono più iniettate qui: dipendono dalla serie e
    # vengono caricate dinamicamente dal client tramite /stazioni.
    return render_template("index.html")


@app.route("/stazioni")
def stazioni():
    """Lista delle stazioni (pallini) per una SERIE 1D, con l'indicazione
    (campo "disponibile") se per la data richiesta esiste il file da poter
    plottare per quella stazione. Senza ?data= valida, "disponibile" e'
    sempre False. Vuota se non ci sono stazioni.

    La SERIE speciale "alps" non e' una vera serie 1D: sono le localita'
    esterne del sito di Davide, ma lette da dati1D/Alps/AAAA/MM/GG/ (vedi
    leggi_siti_alps) invece che da un CSV: senza una ?data= valida, o se
    quel giorno non e' stato scaricato, e' semplicemente vuota."""
    serie = request.args.get("serie", "")

    if serie == "alps":
        try:
            d = datetime.date.fromisoformat(request.args.get("data", ""))
        except ValueError:
            return jsonify([])
        return jsonify([
            {
                "codice": "ALPS_" + s["name"],
                "nome": s["name"],
                "lat": s["lat"],
                "lon": s["lng"],
                "quota": None,
                "disponibile": True,
                "alps": True,
                "data": d.isoformat(),
            }
            for s in leggi_siti_alps(d)
        ])

    if serie == "uv":
        try:
            d = datetime.date.fromisoformat(request.args.get("data", ""))
        except ValueError:
            return jsonify([])
        # ?ora=HH:MM: arrotondata per difetto alla mezz'ora, per aprire il
        # popup gia' sull'istante piu' vicino a quello mostrato altrove.
        try:
            ora_h, ora_m = map(int, request.args.get("ora", "").split(":"))
            ora_m = 0 if ora_m < 30 else 30
        except ValueError:
            ora_h, ora_m = 12, 0
        dt_richiesto = datetime.datetime(d.year, d.month, d.day, ora_h, ora_m)

        risultato = []
        for s in leggi_stazioni("temperatura"):
            if s["codice"] not in STAZIONI_UV:
                continue
            esiste_esatto = os.path.exists(
                percorso_immagine_uv(s["codice"], dt_richiesto))
            # Il pallino (disponibile) resta legato all'istante esatto
            # richiesto; la foto mostrata per prima invece ripiega
            # sull'ultima disponibile, se quell'istante esatto manca.
            dt_da_mostrare = dt_richiesto if esiste_esatto else (
                ultima_immagine_uv_disponibile(s["codice"], dt_richiesto)
                or dt_richiesto
            )
            risultato.append({
                "codice": s["codice"],
                "nome": s["nome"],
                "lat": s["lat"],
                "lon": s["lon"],
                "quota": s["quota"],
                "disponibile": esiste_esatto,
                "uv": True,
                "data": dt_da_mostrare.strftime("%Y-%m-%dT%H:%M"),
            })
        return jsonify(risultato)

    if serie not in SERIE_VALIDE:
        abort(404)

    modello = request.args.get("modello", MODELLO_SERIE_PREDEFINITO)
    if modello not in MODELLI_SERIE_VALIDI:
        abort(404)

    try:
        d = datetime.date.fromisoformat(request.args.get("data", ""))
    except ValueError:
        d = None

    elenco = leggi_stazioni(serie)
    for s in elenco:
        s["disponibile"] = d is not None and os.path.exists(
            percorso_serie_stazione(serie, s["codice"], d, modello))
    return jsonify(elenco)


@app.route("/stazione/<codice>/serie")
def serie_stazione_disponibili(codice):
    """Elenco delle SERIE 1D in cui compare una data stazione (indipendente
    dalla data): serve al popup del grafico per proporre le altre serie
    disponibili per la STESSA stazione, senza dover tornare al menu'.
    Una stazione e' "in" una serie se il suo codice compare nel CSV
    coordinate/<serie>/*.csv - non e' detto che per la data corrente esista
    gia' un file pronto da plottare (quello lo verifica /serie/<codice>)."""
    if not re.fullmatch(r"[A-Za-z0-9_]+", codice):
        abort(404)
    disponibili = [
        serie for serie in sorted(SERIE_VALIDE)
        if any(s["codice"] == codice for s in leggi_stazioni(serie))
    ]
    return jsonify(disponibili)


@app.route("/serie/<codice>")
def serie_stazione(codice):
    """Serie temporale (dato 1D) di una stazione, per una serie e una data.

    Percorso atteso: dati1D/<serie>/<modello>/YYYY/mm/dd/<codice>.csv
    Parametri query: ?serie=vento|temperatura&data=YYYY-MM-DD&modello=ecita
    Converte i -999 in NaN (-> null).
    Risponde 404 se il file per quella combinazione non esiste.
    """
    # Difesa contro path traversal: accetto solo codici alfanumerici
    if not re.fullmatch(r"[A-Za-z0-9_]+", codice):
        abort(404)

    # Serie: deve essere una di quelle ammesse (= sottocartelle di dati1D/)
    serie = request.args.get("serie", "")
    if serie not in SERIE_VALIDE:
        abort(404)

    # Modello di allenamento: per ora solo "ecita", in futuro selezionabile
    modello = request.args.get("modello", MODELLO_SERIE_PREDEFINITO)
    if modello not in MODELLI_SERIE_VALIDI:
        abort(404)

    # Data: deve essere una data valida in formato ISO YYYY-MM-DD
    try:
        d = datetime.date.fromisoformat(request.args.get("data", ""))
    except ValueError:
        abort(404)

    # Componenti tutti validati, niente traversal
    percorso = percorso_serie_stazione(serie, codice, d, modello)
    if not os.path.exists(percorso):
        abort(404)

    # prima colonna = istante temporale (indice), il resto sono le tracce (linee)
    df = pd.read_csv(percorso, index_col=0, parse_dates=True)

    # -999 -> NaN, poi tutti i valori divisi per 10
    df = df.replace(NODATA, np.nan)

    # Osservati: si aggiungono come colonne in piu', ma SOLO sugli istanti
    # gia' presenti nella previsione (reindex scarta il resto e mette NaN
    # dove per quell'istante non c'e' un osservato).
    colonne_osservati = set()
    mappa_osservati = COLONNE_OSSERVATI_PER_SERIE.get(serie)
    if mappa_osservati:
        percorso_oss = os.path.join(CARTELLA_OSSERVATI, f"{codice}.csv")
        if os.path.exists(percorso_oss):
            df_oss = pd.read_csv(percorso_oss, index_col=0, parse_dates=True)
            df_oss = df_oss.replace(NODATA, np.nan).reindex(df.index)
            # Solo le colonne configurate per questa serie: il CSV ne
            # contiene molte altre (di altre serie) da ignorare.
            presenti = [c for c in mappa_osservati if c in df_oss.columns]
            if presenti:
                df_oss = df_oss[presenti].rename(columns=mappa_osservati)
                colonne_osservati = set(df_oss.columns)
                df = pd.concat([df, df_oss], axis=1)

    tempo = df.index.strftime("%Y-%m-%dT%H:%M:%S").tolist()
    tracce = [
        {
            "nome": colonna,
            "osservato": colonna in colonne_osservati,
            "valori": [None if pd.isna(v) else v for v in df[colonna]],
        }
        for colonna in df.columns
    ]

    return jsonify({"tempo": tempo, "tracce": tracce})


# Alcuni campi affiancano ad ogni frame un secondo PNG con lo stesso nome
# piu' un suffisso (es. "convergenze": le frecce del vento sopra il campo
# principale, es. "convergenze_vento_obs_barbs_2026-07-26_2000.png" accanto
# a "convergenze_vento_obs_2026-07-26_2000.png"). Va scartato qui, altrimenti
# /radar/lista lo conterebbe come un frame indipendente invece che come
# accessorio del frame vero.
# Alcune cartelle sono condivise da piu' campi: i tre prodotti di
# "convergenze" (RH, convergenze del vento, cumulata), oppure un secondo PNG
# accessorio come le barbe del vento ("convergenze_vento_obs_barbs_2026-07-
# 26_2000.png" accanto a "convergenze_vento_obs_2026-07-26_2000.png"). Qui si
# specifica il prefisso ESATTO (nome del file meno "_AAAA-MM-GG_HHMM") che un
# campo deve avere: confronto esatto, non "startswith", altrimenti
# "convergenze_vento_obs" prenderebbe per errore anche
# "convergenze_vento_obs_barbs_...". Se un campo non e' qui, nessun filtro
# (e' l'unico occupante della sua cartella, come radar/riflettivita/ecc).
FRAME_PREFISSO_RE = re.compile(r"^(.+?)_\d{4}-\d{2}-\d{2}_\d{4}$")
CAMPI_PREFISSO_FRAME = {
    "convergenze_vento": "convergenze_vento_obs",
    "convergenze_cum": "convergenze_cum_vento_obs",
    "convergenze_rh": "rh_obs",
}


@app.route("/radar/lista")
def radar_lista():
    """Elenco di tutti i frame + i bounds (identici per tutti, letti una volta
    dal sidecar del primo). Il client sfoglia poi solo cambiando immagine.
    Parametro query: ?campo=radar|riflettivita|vert_int_liq|caldo_obs|freddo_obs."""
    campo = request.args.get("campo", "")
    voce = CARTELLE_RADAR.get(campo)
    if voce is None:
        abort(404)
    cartella, estensione, _ = voce
    frame = trova_frame(cartella, estensione)
    prefisso = CAMPI_PREFISSO_FRAME.get(campo)
    if prefisso:
        filtrati = []
        for percorso in frame:
            m = FRAME_PREFISSO_RE.match(
                os.path.splitext(os.path.basename(percorso))[0])
            if m and m.group(1) == prefisso:
                filtrati.append(percorso)
        frame = filtrati
    if not frame:
        return jsonify({"totale": 0, "bounds": None, "nomi": []})
    bounds = None
    for percorso_frame in frame:
        try:
            with open(os.path.splitext(percorso_frame)[0] + ".json") as f:
                sidecar = json.load(f)
            bounds = sidecar["bounds"]
            break
        except (OSError, ValueError, KeyError):
            continue
    nomi = [os.path.splitext(os.path.basename(p))[0] for p in frame]
    return jsonify({
        "totale": len(frame),
        "bounds": bounds,
        "nomi": nomi,
    })


NOME_FRAME_RE = re.compile(r"^[A-Za-z0-9_-]+_(\d{4})-(\d{2})-(\d{2})_(\d{4})$")


@app.route("/immagine/<nome>.<estensione>")
def radar_immagine(nome, estensione):
    """Serve il frame identificato per NOME (es. "radar_vmi_2026-07-03_1200"),
    non per indice numerico: un indice ha senso solo se riferito alla stessa
    lista con cui e' stato calcolato, ma /radar/lista e questa route
    interrogano la cartella in momenti diversi - se nel frattempo arriva un
    nuovo frame, lo stesso indice puo' finire per indicare un file diverso.
    Il nome invece identifica sempre lo stesso file, univocamente.

    L'estensione nell'URL deve combaciare con quella configurata per il
    campo (png per caldo_obs/freddo_obs, webp per radar/riflettivita/vert_int_liq):
    serve solo a evitare che un campo venga servito con l'estensione
    sbagliata, non e' liberamente scelta dal client.
    """
    campo = request.args.get("campo", "")
    voce = CARTELLE_RADAR.get(campo)
    if voce is None:
        abort(404)
    cartella, estensione_attesa, mimetype = voce
    if estensione != estensione_attesa:
        abort(404)
    if not NOME_FRAME_RE.match(nome):
        abort(404)
    percorso = trova_per_nome(cartella, nome, estensione)
    if percorso is None:
        abort(404)
    risposta = send_file(percorso, mimetype=mimetype)
    risposta.headers["Cache-Control"] = "public, max-age=86400"
    return risposta


@app.route("/fulmini/lista")
def fulmini_lista():
    """Elenco di tutti i frame fulmini: come /radar/lista ma senza bounds
    (i pallini si posizionano da soli, non serve un overlay georiferito)."""
    frame = trova_frame(CARTELLA_FULMINI, "csv")
    nomi = [os.path.splitext(os.path.basename(p))[0] for p in frame]
    return jsonify({"totale": len(frame), "nomi": nomi})


@app.route("/satellite/lista")
def satellite_lista():
    """Elenco frame satellite (webp) + bounds, come /radar/lista.
    Parametro query: ?prodotto=geocolour|sandwich."""
    prodotto = request.args.get("prodotto", "")
    cartella = CARTELLE_SATELLITE.get(prodotto)
    if cartella is None:
        abort(404)
    frame = trova_frame(cartella, "webp")
    if not frame:
        return jsonify({"totale": 0, "bounds": None, "nomi": []})
    try:
        with open(os.path.splitext(frame[0])[0] + ".json") as f:
            sidecar = json.load(f)
        bounds = sidecar["bounds"]
    except (OSError, ValueError, KeyError):
        bounds = None
    nomi = [os.path.splitext(os.path.basename(p))[0] for p in frame]
    return jsonify({
        "totale": len(frame),
        "bounds": bounds,
        "nomi": nomi,
    })


@app.route("/satellite/immagine/<nome>.webp")
def satellite_immagine(nome):
    """Stesso parametro ?prodotto= di /satellite/lista. Identificato per
    NOME, non per indice: stesso motivo della route /immagine/<nome>.png,
    l'indice puo' spostarsi se nel frattempo un frame viene aggiunto o
    rimosso (retention)."""
    prodotto = request.args.get("prodotto", "")
    cartella = CARTELLE_SATELLITE.get(prodotto)
    if cartella is None:
        abort(404)
    if not NOME_FRAME_RE.match(nome):
        abort(404)
    percorso = trova_per_nome(cartella, nome, "webp")
    if percorso is None:
        abort(404)
    risposta = send_file(percorso, mimetype="image/webp")
    risposta.headers["Cache-Control"] = "public, max-age=86400"
    return risposta


@app.route("/echotop/lista")
def echotop_lista():
    """Elenco frame Echo Top (webp) + bounds, come /satellite/lista.
    Parametro query: ?livello=18|35|45 (soglia in dBZ)."""
    livello = request.args.get("livello", "")
    if livello not in LIVELLI_ECHOTOP_VALIDI:
        abort(404)
    frame = trova_frame(os.path.join(CARTELLA_ECHOTOP, livello), "webp")
    if not frame:
        return jsonify({"totale": 0, "bounds": None, "nomi": []})
    try:
        with open(os.path.splitext(frame[0])[0] + ".json") as f:
            sidecar = json.load(f)
        bounds = sidecar["bounds"]
    except (OSError, ValueError, KeyError):
        bounds = None
    nomi = [os.path.splitext(os.path.basename(p))[0] for p in frame]
    return jsonify({
        "totale": len(frame),
        "bounds": bounds,
        "nomi": nomi,
    })


@app.route("/echotop/immagine/<nome>.webp")
def echotop_immagine(nome):
    """Stesso parametro ?livello= di /echotop/lista. Identificato per NOME,
    non per indice: stesso motivo di /satellite/immagine/<nome>.webp."""
    livello = request.args.get("livello", "")
    if livello not in LIVELLI_ECHOTOP_VALIDI:
        abort(404)
    if not NOME_FRAME_RE.match(nome):
        abort(404)
    percorso = trova_per_nome(
        os.path.join(CARTELLA_ECHOTOP, livello), nome, "webp")
    if percorso is None:
        abort(404)
    risposta = send_file(percorso, mimetype="image/webp")
    risposta.headers["Cache-Control"] = "public, max-age=86400"
    return risposta


@app.route("/fulmini/dati/<nome>")
def fulmini_dati(nome):
    """Punti (lon, lat, t, tipo) di un frame fulmini, identificato per NOME
    (non per indice): stesso motivo della route /immagine/<nome>.png, un
    indice ha senso solo riferito alla stessa lista con cui e' stato
    calcolato e puo' spostarsi se nel frattempo un frame viene aggiunto o
    rimosso (retention). Nel CSV lon/lat sono interi moltiplicati per
    FATTORE_FULMINI, DTRFSEC (rinominato "t" nell'output, per alleggerire
    il JSON su tanti punti) per FATTORE_TEMPO_FULMINI: entrambi vanno
    riportati in unita' reali dividendo per il rispettivo fattore. COMMT
    (rinominato "tipo") e' una stringa ("G"/"C"), non va moltiplicata per
    nessun fattore; e' opzionale perche' i CSV piu' vecchi non ce l'hanno
    ancora, in quel caso "tipo" e' assente dal punto."""
    if not NOME_FRAME_RE.match(nome):
        abort(404)
    percorso = trova_per_nome(CARTELLA_FULMINI, nome, "csv")
    if percorso is None:
        abort(404)
    df = pd.read_csv(percorso)
    lon = (df["LON"] / FATTORE_FULMINI).to_numpy()
    lat = (df["LAT"] / FATTORE_FULMINI).to_numpy()
    t = (df["DTRFSEC"] / FATTORE_FULMINI).to_numpy()
    if "COMMT" in df.columns:
        tipo = df["COMMT"].to_numpy()
        punti = [{"lon": lo, "lat": la, "t": tt, "tipo": ti}
                 for lo, la, tt, ti in zip(lon, lat, t, tipo)]
    else:
        punti = [{"lon": lo, "lat": la, "t": tt}
                 for lo, la, tt in zip(lon, lat, t)]
    return jsonify(punti)


# Limite di sicurezza sul numero di nomi accettati da /fulmini/dati_intervallo:
# una finestra di 24h a 5 minuti fa ~288 file, questo margine copre anche
# eventuali cadenze piu' fitte senza lasciare la porta aperta a richieste
# arbitrariamente grandi.
MAX_NOMI_INTERVALLO_FULMINI = 400


@app.route("/fulmini/dati_intervallo")
def fulmini_dati_intervallo():
    """Come /fulmini/dati/<nome> ma per PIU' frame in una volta sola: un
    solo giro di richiesta invece di uno per file, per non intasare il
    server quando la cumulata scelta dall'utente copre molti CSV (fino a
    24h = ~288 file da 5 minuti, vedi FINESTRA_FULMINI_VALORI_MIN nel
    frontend). Parametro ?nomi=<nome1>,<nome2>,... (stessi nomi restituiti
    da /fulmini/lista). Nomi non validi o file non trovati (es. per
    retention) vengono ignorati singolarmente, non fanno fallire l'intera
    richiesta."""
    nomi = [n for n in request.args.get("nomi", "").split(",") if n]
    nomi = nomi[:MAX_NOMI_INTERVALLO_FULMINI]
    punti = []
    for nome in nomi:
        if not NOME_FRAME_RE.match(nome):
            continue
        percorso = trova_per_nome(CARTELLA_FULMINI, nome, "csv")
        if percorso is None:
            continue
        df = pd.read_csv(percorso)
        lon = (df["LON"] / FATTORE_FULMINI).to_numpy()
        lat = (df["LAT"] / FATTORE_FULMINI).to_numpy()
        t = (df["DTRFSEC"] / FATTORE_FULMINI).to_numpy()
        if "COMMT" in df.columns:
            tipo = df["COMMT"].to_numpy()
            punti.extend(
                {"lon": lo, "lat": la, "t": tt, "tipo": ti}
                for lo, la, tt, ti in zip(lon, lat, t, tipo))
        else:
            punti.extend(
                {"lon": lo, "lat": la, "t": tt} for lo, la, tt in zip(lon, lat, t))
    return jsonify(punti)


@app.route("/alps/immagine/<nome>.png")
def alps_immagine(nome):
    """Immagine locale di una localita' Alps per una data (scaricata da
    download_alps.py in dati1D/Alps/AAAA/MM/GG/<nome>.png).
    Parametro query: ?data=YYYY-MM-DD"""
    if not NOME_SITO_ALPS_RE.match(nome):
        abort(404)
    try:
        d = datetime.date.fromisoformat(request.args.get("data", ""))
    except ValueError:
        abort(404)
    percorso = os.path.join(percorso_cartella_alps(d), f"{nome}.png")
    if not os.path.exists(percorso):
        abort(404)
    risposta = send_file(percorso, mimetype="image/png")
    risposta.headers["Cache-Control"] = "public, max-age=86400"
    return risposta


@app.route("/media_giornaliera/immagine/<serie>.png")
def media_giornaliera_immagine(serie):
    """Mappa giornaliera gia' pronta (PNG) per temp_media/prec_media/sst/
    sst_anomaly: stesso schema di /alps/immagine ma senza localita', una
    sola immagine per l'intera regione. Parametro query: ?data=YYYY-MM-DD"""
    if serie not in IMMAGINI_MEDIA_GIORNALIERA:
        abort(404)
    try:
        d = datetime.date.fromisoformat(request.args.get("data", ""))
    except ValueError:
        abort(404)
    percorso = percorso_immagine_media_giornaliera(serie, d)
    if not os.path.exists(percorso):
        abort(404)
    risposta = send_file(percorso, mimetype="image/png")
    # A differenza delle altre immagini (radar, satellite, alps...), queste
    # 4 possono essere rigenerate piu' volte nella stessa giornata: niente
    # cache, va rifatta la richiesta ogni volta.
    risposta.headers["Cache-Control"] = "no-store"
    return risposta


@app.route("/uv/immagine/<codice>.png")
def uv_immagine(codice):
    """Foto UV di una delle due stazioni (CFUNZ, SPZIA), una ogni 30 minuti.
    Parametro query: ?data=YYYY-MM-DDTHH:MM"""
    if codice not in STAZIONI_UV:
        abort(404)
    try:
        dt = datetime.datetime.fromisoformat(request.args.get("data", ""))
    except ValueError:
        abort(404)
    percorso = percorso_immagine_uv(codice, dt)
    if not os.path.exists(percorso):
        abort(404)
    risposta = send_file(percorso, mimetype="image/png")
    risposta.headers["Cache-Control"] = "public, max-age=86400"
    return risposta


@app.route("/shapefile/<nome>")
def shapefile_geojson(nome):
    """Shapefile convertito in GeoJSON (WGS84), per L.geoJSON su Leaflet."""
    if nome not in SHAPEFILE_VALIDI:
        abort(404)
    geojson = leggi_shapefile_geojson(nome)
    if geojson is None:
        abort(404)
    return jsonify(geojson)


if __name__ == "__main__":
    app.run(debug=True, port=5009, threaded=True)
