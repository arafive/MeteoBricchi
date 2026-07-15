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
# DOPO
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
# Confini geografici statici (shapefile), overlay opzionali sulla mappa.
# Ogni sottocartella contiene UN solo .shp (nome variabile: si trova per
# estensione) + i sidecar .dbf/.shx/.prj/.cpg.
CARTELLA_SHAPEFILE = os.path.join(os.path.dirname(__file__), "shapefile")
SHAPEFILE_VALIDI = {"aree", "bacini", "comprensori", "comuni", "regioni"}
# nome -> GeoJSON gia' convertito (i file non cambiano a runtime)
_cache_shapefile = {}

# Colonne del CSV fulmini gia' moltiplicate per 10000 (interi): vanno
# riportate in unita' reali dividendo per 10000 prima dell'uso.
FATTORE_FULMINI = 10000.0

# Valore sentinella usato nei CSV per i dati mancanti
NODATA = -999

# SERIE = dati 1D (serie temporali su stazioni puntuali): sottocartelle di dati1D/
SERIE_VALIDE = {"vento", "temperatura", "umidita", "pioggia"}
# CAMPO = dati 2D (griglia lat/lon): sottocartelle di dati2D/ - per ora solo il bottone
CAMPI_VALIDI = {"radar", "riflettivita", "vert_int_liq", "fulmini"}


def trova_frame(cartella, estensione):
    """File gia' pronti in <cartella>/AAAA/MM/GG/*.<estensione>, ordinati
    cronologicamente (il nome file e' ordinabile lessicograficamente)."""
    return sorted(glob.glob(os.path.join(cartella, "*", "*", "*", f"*.{estensione}")))


def trova_per_nome(cartella, nome, estensione):
    """Cerca <nome>.<estensione> dentro <cartella>/AAAA/MM/GG/ senza
    assumere che le componenti di data nel nome corrispondano esattamente
    alla sottocartella in cui il file si trova davvero (puo' non essere
    cosi' per frame generati/salvati con un piccolo sfasamento rispetto
    al proprio nome, es. a cavallo di mezzanotte)."""
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
    sempre False. Vuota se non ci sono stazioni."""
    serie = request.args.get("serie", "")
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


NOME_FRAME_RE = re.compile(r"^[A-Za-z0-9_]+_(\d{4})-(\d{2})-(\d{2})_(\d{4})$")


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


@app.route("/fulmini/dati/<nome>")
def fulmini_dati(nome):
    """Punti (lon, lat) di un frame fulmini, identificato per NOME (non per
    indice): stesso motivo della route /immagine/<nome>.png, un indice ha
    senso solo riferito alla stessa lista con cui e' stato calcolato e puo'
    spostarsi se nel frattempo un frame viene aggiunto o rimosso (retention).
    Nel CSV lon/lat sono interi moltiplicati per 10000: li riporto in gradi
    dividendo per 10000."""
    if not NOME_FRAME_RE.match(nome):
        abort(404)
    percorso = trova_per_nome(CARTELLA_FULMINI, nome, "csv")
    if percorso is None:
        abort(404)
    df = pd.read_csv(percorso, usecols=["LON", "LAT"]) / FATTORE_FULMINI
    punti = df.rename(columns={"LON": "lon", "LAT": "lat"}).to_dict(
        orient="records")
    return jsonify(punti)


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
    app.run(debug=True, port=5009)
