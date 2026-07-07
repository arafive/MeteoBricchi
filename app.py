import re
import os
import glob
import json
import datetime

import numpy as np
import pandas as pd
from flask import Flask, render_template, jsonify, abort, request, send_file

app = Flask(__name__)

# Cartelle
CARTELLA_COORD = os.path.join(os.path.dirname(__file__), "coordinate")
CARTELLA_SERIE = os.path.join(os.path.dirname(__file__), "dati1D")
CARTELLA_CAMPI = os.path.join(os.path.dirname(__file__), "dati2D")
CARTELLE_RADAR = {
    "radar": os.path.join(CARTELLA_CAMPI, "radar_sri"),
    "riflettivita": os.path.join(CARTELLA_CAMPI, "radar_vmi"),
    "caldo": os.path.join(CARTELLA_CAMPI, "heatindex2D_obs"),
    "freddo": os.path.join(CARTELLA_CAMPI, "windchill2D_obs"),
}
CARTELLA_FULMINI = os.path.join(CARTELLA_CAMPI, "fulmini")
# Prodotti satellite: stessa idea di CARTELLE_RADAR, ma frame in .webp e
# cadenza di 10 minuti invece di 5.
CARTELLE_SATELLITE = {
    "geocolour": os.path.join(CARTELLA_CAMPI, "geocolour"),
    "sandwich": os.path.join(CARTELLA_CAMPI, "sandwich"),
}

# Colonne del CSV fulmini gia' moltiplicate per 10000 (interi): vanno
# riportate in unita' reali dividendo per 10000 prima dell'uso.
FATTORE_FULMINI = 10000.0

# Valore sentinella usato nei CSV per i dati mancanti
NODATA = -999

# SERIE = dati 1D (serie temporali su stazioni puntuali): sottocartelle di dati1D/
SERIE_VALIDE = {"vento", "temperatura"}
# CAMPO = dati 2D (griglia lat/lon): sottocartelle di dati2D/ - per ora solo il bottone
CAMPI_VALIDI = {"radar", "riflettivita", "fulmini"}


def trova_frame(cartella, estensione):
    """File gia' pronti in <cartella>/AAAA/MM/GG/*.<estensione>, ordinati
    cronologicamente (il nome file e' ordinabile lessicograficamente)."""
    return sorted(glob.glob(os.path.join(cartella, "*", "*", "*", f"*.{estensione}")))


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
    """Lista delle stazioni (pallini) per una SERIE 1D. Vuota se non ci sono dati."""
    serie = request.args.get("serie", "")
    if serie not in SERIE_VALIDE:
        abort(404)
    return jsonify(leggi_stazioni(serie))


@app.route("/serie/<codice>")
def serie_stazione(codice):
    """Serie temporale (dato 1D) di una stazione, per una serie e una data.

    Percorso atteso: dati1D/<serie>/YYYY/mm/dd/<codice>/<codice>.csv
    Parametri query: ?serie=vento|temperatura&data=YYYY-MM-DD
    Converte i -999 in NaN (-> null) e divide i valori per 10.
    Risponde 404 se il file per quella combinazione non esiste.
    """
    # Difesa contro path traversal: accetto solo codici alfanumerici
    if not re.fullmatch(r"[A-Za-z0-9_]+", codice):
        abort(404)

    # Serie: deve essere una di quelle ammesse (= sottocartelle di dati1D/)
    serie = request.args.get("serie", "")
    if serie not in SERIE_VALIDE:
        abort(404)

    # Data: deve essere una data valida in formato ISO YYYY-MM-DD
    try:
        d = datetime.date.fromisoformat(request.args.get("data", ""))
    except ValueError:
        abort(404)

    # Costruisco il percorso: i componenti sono tutti validati, niente traversal
    percorso = os.path.join(
        CARTELLA_SERIE, serie,
        f"{d.year:04d}", f"{d.month:02d}", f"{d.day:02d}",
        codice, f"{codice}.csv",
    )
    if not os.path.exists(percorso):
        abort(404)

    # prima colonna = istante temporale (indice), il resto sono le tracce (linee)
    df = pd.read_csv(percorso, index_col=0, parse_dates=True)

    # -999 -> NaN, poi tutti i valori divisi per 10
    df = df.replace(NODATA, np.nan) / 10.0

    tempo = df.index.strftime("%Y-%m-%dT%H:%M:%S").tolist()
    tracce = [
        {
            "nome": colonna,
            # NaN -> None (JSON null): ECharts li mostra come interruzioni
            "valori": [None if pd.isna(v) else float(v) for v in df[colonna]],
        }
        for colonna in df.columns
    ]
    return jsonify({"tempo": tempo, "tracce": tracce})


@app.route("/radar/lista")
def radar_lista():
    """Elenco di tutti i frame + i bounds (identici per tutti, letti una volta
    dal sidecar del primo). Il client sfoglia poi solo cambiando immagine.
    Parametro query: ?campo=radar|riflettivita (quale cartella di dati2D/)."""
    campo = request.args.get("campo", "")
    cartella = CARTELLE_RADAR.get(campo)
    if cartella is None:
        abort(404)
    frame = trova_frame(cartella, "png")
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


NOME_FRAME_RE = re.compile(r"^[A-Za-z0-9_]+_(\d{4})-(\d{2})-(\d{2})_(\d{4})$")


@app.route("/immagine/<nome>.png")
def radar_immagine(nome):
    """Serve il frame identificato per NOME (es. "radar_vmi_2026-07-03_1200"),
    non per indice numerico: un indice ha senso solo se riferito alla stessa
    lista con cui e' stato calcolato, ma /radar/lista e questa route
    interrogano la cartella in momenti diversi - se nel frattempo arriva un
    nuovo frame, lo stesso indice puo' finire per indicare un file diverso.
    Il nome invece identifica sempre lo stesso file, univocamente.
    """
    campo = request.args.get("campo", "")
    cartella = CARTELLE_RADAR.get(campo)
    if cartella is None:
        abort(404)
    corrisp = NOME_FRAME_RE.match(nome)
    if not corrisp:
        abort(404)
    anno, mese, giorno = corrisp.group(1), corrisp.group(2), corrisp.group(3)
    percorso = os.path.join(cartella, anno, mese, giorno, nome + ".png")
    if not os.path.exists(percorso):
        abort(404)
    risposta = send_file(percorso, mimetype="image/png")
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


@app.route("/satellite/immagine/<int:indice>.webp")
def satellite_immagine(indice):
    """Stesso parametro ?prodotto= di /satellite/lista: l'indice ha senso
    solo riferito alla stessa cartella con cui e' stata costruita la lista."""
    prodotto = request.args.get("prodotto", "")
    cartella = CARTELLE_SATELLITE.get(prodotto)
    if cartella is None:
        abort(404)
    frame = trova_frame(cartella, "webp")
    if indice < 0 or indice >= len(frame):
        abort(404)
    risposta = send_file(frame[indice], mimetype="image/webp")
    risposta.headers["Cache-Control"] = "public, max-age=86400"
    return risposta


@app.route("/fulmini/dati/<int:indice>")
def fulmini_dati(indice):
    """Punti (lon, lat) di un frame fulmini. Nel CSV lon/lat sono interi
    moltiplicati per 10000: li riporto in gradi dividendo per 10000."""
    frame = trova_frame(CARTELLA_FULMINI, "csv")
    if indice < 0 or indice >= len(frame):
        abort(404)
    df = pd.read_csv(frame[indice], usecols=["LON", "LAT"]) / FATTORE_FULMINI
    punti = df.rename(columns={"LON": "lon", "LAT": "lat"}).to_dict(
        orient="records")
    return jsonify(punti)


if __name__ == "__main__":
    app.run(debug=True, port=5009)
