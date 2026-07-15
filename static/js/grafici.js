/* grafici.js — generazione dei grafici delle SERIE (dati 1D) con ECharts.
 *
 * Il vento NON conosce mappa, popup o fetch: riceve un contenitore, i dati
 * grezzi ({ tempo, tracce }) e il nome della serie, e disegna. Espone un solo
 * oggetto globale: `Grafici`.
 *
 * >>> Per aggiungere una nuova serie in futuro, basta aggiungere una voce a
 * >>> CONFIG_SERIE qui sotto: nessuna modifica alla logica di disegno. <<<
 */
window.Grafici = (function () {
  "use strict";

  // --- Configurazione per serie -------------------------------------------
  // unita: etichetta dell'asse y (stringa vuota = nessuna).
  // yMin / yMax: limiti fissi dell'asse y (null = autoscala).
  const CONFIG_SERIE = {
    vento: {
      unita: "km/h",
      yMin: 0,
      yMax: 120,
      tickInterval: 10,
    },
    umidita: {
      unita: "%",
      yMin: 0,
      yMax: 100,
      tickInterval: 10,
    },
    temperatura: {
      unita: "\u00B0C", // °C
      yMin: null,
      yMax: null,
      limitiArrotondati: true,
      tickInterval: 2,
    },
  };

  // Ripiego per serie non ancora configurate: autoscala, nessuna unità.
  const CONFIG_DEFAULT = { unita: "", yMin: null, yMax: null };

  const COLORE_SORGENTE = {
    "QRF minima": "#17becf",
    "QRF media": "#2ca02c",
    "QRF massima": "#d62728",
    "Obs minima": "#000000",
    "Obs media": "#000000",
    "Obs massima": "#000000",
    ecita: "#ff7f0e",
    Clima: "#9467bd",
    //
    "QRF vento": "#17becf",
    "ecita vento": "#1f77b4",
    "Obs vento": "#000000",
    "QRF raffica": "#9467bd",
    "ecita raffica": "#d62728",
    "Obs raffica": "#000000",
  };
  COLORE_SORGENTE["ecita direzione"] = COLORE_SORGENTE["ecita vento"];
  COLORE_SORGENTE["RF direzione"] = COLORE_SORGENTE["QRF vento"];

  const STILE_SORGENTE = {
    "QRF minima": "dashed",
    "QRF media": "solid",
    "QRF massima": "dotted",
    "Obs minima": "dashed",
    "Obs media": "solid",
    "Obs massima": "dotted",
    ecita: "solid",
    Clima: "solid",
    //
    "QRF vento": "solid",
    "ecita vento": "solid",
    "Obs vento": "solid",
    "QRF raffica": "dashed",
    "ecita raffica": "dashed",
    "Obs raffica": "dashed",
  };

  // Nomi di serie da non mostrare mai nel tooltip (aggiungi qui le label da escludere)
  const ESCLUSI_TOOLTIP = new Set([
    "QRF vento 25°-75°",
    "QRF raffica 25°-75°",
    "QRF minima 25°-75°",
    "QRF media 25°-75°",
    "QRF massima 25°-75°",
  ]);

  // Bande sempre spente di default; "ecita"/"Clima" (temperatura) spenti,
  // "ecita vento"/"ecita raffica" invece accesi (nessun'altra fonte reale
  // per il vento, a differenza di temperatura/umidita che hanno gli
  // osservati). Gli "Obs *" non compaiono piu': sostituiti dagli osservati.
  const DISATTIVATI_DEFAULT = new Set([
    "QRF vento 25°-75°",
    "QRF raffica 25°-75°",
    "QRF minima",
    "QRF minima 25°-75°",
    "QRF massima",
    "QRF media 25°-75°",
    "Clima",
    "QRF massima 25°-75°",
    "Obs vento",
    "Obs raffica",
    "Obs massima",
    "Obs minima",
  ]);

  // Il vento arriva dal backend in m/s; il grafico lo mostra in km/h
  // (vedi CONFIG_SERIE.vento.unita), quindi tutto va moltiplicato per
  // 3.6 — tranne le colonne di direzione, che restano gradi cosi' come
  // sono e non vanno convertite.
  function fattoreConversioneVento(serie, nome) {
    if (serie !== "vento") return 1;
    return nome.indexOf("direzione") === -1 ? 3.6 : 1;
  }

  function costruisciSelected() {
    const selected = {};
    DISATTIVATI_DEFAULT.forEach(function (nome) {
      selected[nome] = false;
    });
    return selected;
  }

  // Nomi delle tracce di quantile usate per costruire la banda (non renderizzate come linee singole)
  const NOMI_BANDA_TMIN = { basso: "QRF minima 0.25", alto: "QRF minima 0.75" };
  const NOMI_BANDA_TMEAN = { basso: "QRF media 0.25", alto: "QRF media 0.75" };
  const NOMI_BANDA_TMAX = {
    basso: "QRF massima 0.25",
    alto: "QRF massima 0.75",
  };
  const NOMI_BANDA_MODULO = {
    basso: "QRF vento 0.25",
    alto: "QRF vento 0.75",
  };
  const NOMI_BANDA_RAFFICA = {
    basso: "QRF raffica 0.25",
    alto: "QRF raffica 0.75",
  };

  // Solo le bande pertinenti alla serie in disegno: prima si cercavano
  // sempre tutte e 5 (anche quelle dell'altra serie), che non trovandole
  // mai facevano scattare il warning di debug per un falso positivo.
  // A livello di modulo (non dentro costruisciTracce) perché la usa anche
  // costruisciLegenda, per sapere quali colonne diventano una banda.
  const DEFINIZIONI_BANDA_PER_SERIE = {
    temperatura: [
      {
        nomi: NOMI_BANDA_TMIN,
        colore: "rgba(23, 190, 207, 0.5)",
        etichetta: "QRF minima 25°-75°",
      },
      {
        nomi: NOMI_BANDA_TMEAN,
        colore: "rgba(44, 160, 44, 0.5)",
        etichetta: "QRF media 25°-75°",
      },
      {
        nomi: NOMI_BANDA_TMAX,
        colore: "rgba(214, 39, 40, 0.5)",
        etichetta: "QRF massima 25°-75°",
      },
    ],
    umidita: [
      {
        // stessa coppia di colonne quantile di temperatura (QRF media
        // 0.25/0.75): stesso trattamento a banda, stessa etichetta.
        nomi: NOMI_BANDA_TMEAN,
        colore: "rgba(44, 160, 44, 0.5)",
        etichetta: "QRF media 25°-75°",
      },
    ],
    vento: [
      {
        nomi: NOMI_BANDA_MODULO,
        colore: "rgba(23, 190, 207, 0.5)",
        etichetta: "QRF vento 25°-75°",
      },
      {
        nomi: NOMI_BANDA_RAFFICA,
        colore: "rgba(148, 103, 189, 0.5)",
        etichetta: "QRF raffica 25°-75°",
      },
    ],
  };

  // Layout esplicito della legenda per le serie configurate: una voce (nome
  // reale della traccia, o etichetta di banda) per cella riga/colonna;
  // null = cella vuota. Sostituisce il vecchio schema ad "a capo
  // automatico" con separatori invisibili (__sep__), che si riorganizzava
  // ridimensionando il popup: qui riga e colonna di ogni voce sono fisse.
  const RIGHE_LEGENDA_PER_SERIE = {
    temperatura: [
      ["QRF massima", "QRF massima 25°-75°", "ecita", "Obs massima"],
      ["QRF media", "QRF media 25°-75°", "Clima", "Obs media"],
      ["QRF minima", "QRF minima 25°-75°", null, "Obs minima"],
    ],
    vento: [
      ["QRF vento", "QRF vento 25°-75°", "ecita vento", "Obs vento"],
      ["QRF raffica", "QRF raffica 25°-75°", "ecita raffica", "Obs raffica"],
    ],
    umidita: [["QRF media", "QRF media 25°-75°", "ecita", "Obs media"]],
  };
  // Posizione (percentuale da sinistra) di ciascuna delle 4 colonne, e
  // altezza in px tra una riga e la successiva: valori percentuali cosi'
  // la griglia scala col popup ma senza mai cambiare struttura.
  const COLONNE_LEGENDA_GRIGLIA = ["4%", "24%", "50%", "70%"];
  const ALTEZZA_RIGA_LEGENDA = 26;

  // Spazio (px) da riservare in basso nel grafico per la legenda a
  // griglia di questa serie; le serie non configurate (legenda generica,
  // a capo automatico) restano al valore di sempre.
  function altezzaLegenda(serie) {
    const righe = RIGHE_LEGENDA_PER_SERIE[serie];
    if (!righe) return 100;
    return righe.length * ALTEZZA_RIGA_LEGENDA + 50;
  }

  // Costruisce le tracce (linee) ECharts dai dati grezzi.
  function costruisciTracce(dati, serie) {
    const DEFINIZIONI_BANDA = DEFINIZIONI_BANDA_PER_SERIE[serie] || [];

    // Nomi delle colonne "grezze" usate per costruire le bande di QUESTA
    // serie: vanno escluse dalle tracce normali (le disegna gia' la banda).
    // Le serie senza bande configurate (per ora: pioggia) non escludono
    // nulla: si vede ogni colonna del CSV cosi' com'e'.
    const nomiEsclusi = new Set();
    nomiEsclusi.add("RF direzione");
    nomiEsclusi.add("ecita direzione");
    DEFINIZIONI_BANDA.forEach(function (def) {
      nomiEsclusi.add(def.nomi.basso);
      nomiEsclusi.add(def.nomi.alto);
    });
    // Le serie con legenda a griglia (temperatura/vento/umidita) mostrano
    // solo le voci elencate in RIGHE_LEGENDA_PER_SERIE: gli "Obs *" non ci
    // sono piu', sostituiti dagli osservati veri (t.osservato).
    if (RIGHE_LEGENDA_PER_SERIE[serie]) {
      dati.tracce.forEach(function (t) {
        // Nascondi "Obs *" solo se NON e' un osservato vero (residuo del
        // vecchio schema nel CSV di previsione): gli osservati veri, anche
        // se rinominati "Obs media" ecc., vanno mostrati.
        if (t.nome.indexOf("Obs ") === 0 && !t.osservato) {
          nomiEsclusi.add(t.nome);
        }
      });
      // Un osservato in colonna 4 (es. "Obs minima") ha senso solo se
      // esiste anche il QRF di quella riga: se manca (stazione senza
      // "QRF minima"/"QRF massima"/"QRF raffica"), niente linea sul
      // grafico, non solo niente voce in legenda.
      RIGHE_LEGENDA_PER_SERIE[serie].forEach(function (riga) {
        const nomeQrf = riga[0];
        const nomeOsservato = riga[3];
        if (!nomeOsservato) return;
        const cePrevisione = dati.tracce.some(function (t) {
          return t.nome === nomeQrf;
        });
        if (!cePrevisione) nomiEsclusi.add(nomeOsservato);
      });
    }

    const tracceNormali = dati.tracce
      .filter(function (t) {
        return !nomiEsclusi.has(t.nome);
      })
      .map(function (t) {
        const fattore = fattoreConversioneVento(serie, t.nome);
        return {
          name: t.nome,
          type: "line",
          showSymbol: false,
          symbol: "none",
          smooth: true,
          // Tracce osservate (backend: "osservato":true) sempre nere,
          // indipendentemente dal nome della colonna nel CSV; lo stile
          // tratteggio/punteggiato invece segue comunque STILE_SORGENTE
          // (es. "Obs minima" tratteggiata come "QRF minima"), non e'
          // sempre "solid".
          color: t.osservato ? "#000000" : COLORE_SORGENTE[t.nome],
          lineStyle: {
            width: 3,
            type: STILE_SORGENTE[t.nome] || "solid",
          },
          // [istante, valore]; i null creano le interruzioni
          data: dati.tempo.map(function (istante, i) {
            const v = t.valori[i];
            return [istante, v == null ? null : v * fattore];
          }),
        };
      });

    const tracceBanda = [];
    DEFINIZIONI_BANDA.forEach(function (def) {
      const traccBassa = dati.tracce.find(function (t) {
        return t.nome === def.nomi.basso;
      });
      const traccAlta = dati.tracce.find(function (t) {
        return t.nome === def.nomi.alto;
      });
      if (!traccBassa || !traccAlta) {
        console.warn(
          "Banda '" +
            def.etichetta +
            "' non disegnata: manca '" +
            (traccBassa ? def.nomi.alto : def.nomi.basso) +
            "' tra le tracce ricevute dal backend.",
        );
        return;
      }

      const fattore = fattoreConversioneVento(serie, def.nomi.basso);
      const stackId = "banda-" + def.nomi.alto;
      tracceBanda.push(
        {
          name: def.etichetta,
          type: "line",
          stack: stackId,
          symbol: "none",
          smooth: true,
          color: def.colore,
          lineStyle: { opacity: 0 },
          data: dati.tempo.map(function (istante, i) {
            const v = traccBassa.valori[i];
            return [istante, v == null ? null : v * fattore];
          }),
        },
        {
          name: def.etichetta,
          type: "line",
          stack: stackId,
          symbol: "none",
          smooth: true,
          color: def.colore,
          lineStyle: { opacity: 0 },
          areaStyle: { color: def.colore },
          // valore = differenza alto - basso, perché la serie si somma alla precedente nello stack
          data: dati.tempo.map(function (istante, i) {
            const basso = traccBassa.valori[i];
            const alto = traccAlta.valori[i];
            return [
              istante,
              basso == null || alto == null ? null : (alto - basso) * fattore,
            ];
          }),
        },
      );
    });

    const tracceSoglie =
      serie === "vento"
        ? [
            {
              name: "__soglie__",
              type: "line",
              data: [],
              silent: true,
              markLine: {
                silent: true,
                symbol: "none",
                lineStyle: { color: "#000000", type: "dashed" },
                label: { show: false },
                data: [
                  { yAxis: 75, lineStyle: { width: 1.5 } },
                  { yAxis: 60, lineStyle: { width: 1.0 } },
                  { yAxis: 50, lineStyle: { width: 0.75 } },
                ],
              },
            },
          ]
        : [];

    console.log(
      "Serie banda costruite per '" + serie + "':",
      tracceBanda.map(function (s) {
        return {
          nome: s.name,
          stack: s.stack,
          haAreaStyle: !!s.areaStyle,
          nPunti: s.data.length,
          primi3: s.data.slice(0, 3),
          tipoValore: typeof (s.data.find(function (d) {
            return d[1] != null;
          }) || [null, null])[1],
        };
      }),
    );
    return tracceNormali.concat(tracceBanda, tracceSoglie);
  }

  // Trova il minimo e il massimo assoluti tra tutti i valori delle tracce.
  function calcolaEstremiDati(dati) {
    let min = Infinity,
      max = -Infinity;
    dati.tracce.forEach(function (t) {
      const valoriValidi = t.valori.filter(function (v) {
        return v != null && !Number.isNaN(v);
      });
      if (valoriValidi.length === 0) return;
      const tMin = Math.min.apply(null, valoriValidi);
      const tMax = Math.max.apply(null, valoriValidi);
      if (tMin < min) min = tMin;
      if (tMax > max) max = tMax;
    });
    if (!isFinite(min) || !isFinite(max)) return null;
    return { min: min, max: max };
  }

  function costruisciAsseY(cfg, dati) {
    const yAxis = { type: "value", axisLabel: { fontSize: 11 } };

    if (cfg.limitiArrotondati) {
      // min/max come FUNZIONI, non numeri fissi: un numero fisso e' quello
      // che impediva a ECharts di ricalcolare lo stacking delle bande ad
      // ogni cambio di legenda (restavano "non impilate" - vedi
      // discussione in chat). Le funzioni invece passano dallo stesso
      // percorso di calcolo dinamico dell'autoscala nativa, quindi lo
      // stacking si ricalcola comunque - pur restituendo sempre lo stesso
      // range fisso (floor/ceil degli estremi del CSV), non quello delle
      // sole tracce visibili in un dato momento.
      const estremi = calcolaEstremiDati(dati);
      if (estremi) {
        yAxis.min = function () {
          return Math.floor(estremi.min / 2) * 2; // pari piu' basso <= minimo
        };
        yAxis.max = function () {
          return Math.ceil(estremi.max / 2) * 2; // pari piu' alto >= massimo
        };
      }
    } else {
      if (cfg.yMin !== null && cfg.yMin !== undefined) yAxis.min = cfg.yMin;
      if (cfg.yMax !== null && cfg.yMax !== undefined) yAxis.max = cfg.yMax;
    }
    if (cfg.tickInterval) yAxis.interval = cfg.tickInterval;
    if (cfg.unita) {
      yAxis.name = cfg.unita;
      yAxis.nameLocation = "middle";
      yAxis.nameGap = 28;
      yAxis.nameRotate = 90;
      yAxis.nameTextStyle = { fontSize: 14, color: "#5a6b7b" };
    }
    return yAxis;
  }

  // Costruisce la configurazione della legenda in base alla serie.
  // Per "vento" servono due colonne separate (vento / raffica).
  // Icone custom per ogni voce di legenda: niente icona "di default" di
  // ECharts, che per le serie di tipo line è sempre trattino+pallino a
  // prescindere dal symbol:"none" dei dati veri (quello vale solo per i
  // marker sul grafico, non per l'icona della legenda). Un blocchetto
  // pieno/tratteggiato/punteggiato disegnato a mano evita il pallino e
  // riflette comunque lo stile reale della linea.
  const ICONA_PER_STILE = {
    solid: "path://M0,7 L20,7 L20,13 L0,13 Z",
    dashed: "path://M0,7L8,7L8,13L0,13ZM12,7L20,7L20,13L12,13Z",
    dotted:
      "path://M0,7L4,7L4,13L0,13ZM8,7L12,7L12,13L8,13ZM16,7L20,7L20,13L16,13Z",
  };

  function costruisciLegenda(dati, serie) {
    // Etichette un po' piu' grandi (era 11/18/10/12).
    const stileVoce = {
      textStyle: { fontSize: 13 },
      itemWidth: 22,
      itemHeight: 12,
      itemGap: 14,
    };

    // Voce di legenda per una traccia: icona in base allo stile reale della
    // linea (STILE_SORGENTE). Le bande e i nomi non configurati (es. gli
    // osservati, il cui nome dipende dal CSV) ricadono su "solid": le bande
    // sono comunque un'AREA piena (lineStyle invisibile), quindi lo stesso
    // rettangolo pieno va bene anche per loro.
    function voce(nome) {
      return {
        name: nome,
        icon: ICONA_PER_STILE[STILE_SORGENTE[nome]] || ICONA_PER_STILE.solid,
      };
    }

    const righe = RIGHE_LEGENDA_PER_SERIE[serie];
    if (righe) {
      // Una voce = un componente legend a se', posizionato con left/bottom
      // espliciti invece del solito a capo automatico di ECharts: cosi'
      // la disposizione a righe/colonne resta quella voluta qualunque sia
      // la larghezza del popup (prima, ridimensionando, l'a-capo automatico
      // spostava le voci e rompeva i due gruppi vento/raffica o le tre
      // righe di temperatura).
      const componenti = [];
      righe.forEach(function (riga, indiceRiga) {
        const bottom = (righe.length - 1 - indiceRiga) * ALTEZZA_RIGA_LEGENDA;
        riga.forEach(function (nome, indiceColonna) {
          if (!nome) return; // cella vuota
          // La colonna degli osservati (indice 3) ha senso solo se il
          // plot ha anche il QRF di quella riga: senza "QRF minima" non
          // si mostra "Obs minima" (idem massima, raffica).
          if (indiceColonna === 3) {
            const nomeQrf = riga[0];
            const cePrevisione = dati.tracce.some(function (t) {
              return t.nome === nomeQrf;
            });
            if (!cePrevisione) return;
          }
          componenti.push(
            Object.assign({}, stileVoce, {
              left: COLONNE_LEGENDA_GRIGLIA[indiceColonna],
              bottom: bottom,
              data: [voce(nome)],
              selected: costruisciSelected(),
            }),
          );
        });
      });

      return componenti;
    }

    return Object.assign(
      { bottom: 0, left: "center", orient: "horizontal" },
      stileVoce,
      {
        selected: costruisciSelected(),
      },
    );
  }

  // --- Frecce di direzione del vento ---------------------------------------
  // Simbolo: il path del tuo freccia.svg (punta verso l'ALTO) — copiato
  // com'e' dall'attributo "d" del file, con "path://" davanti: resta un
  // path vero (non un'immagine), quindi itemStyle.color continua a
  // funzionare per colorarlo diversamente per ecita/RF.
  const SIMBOLO_FRECCIA_VENTO =
    "path://m 31.5703,6.5391 -15.625,-15.625 c -1.2188,-1.2188 -3.1875,-1.2188 -4.4062,0 l -15.625,15.625 c -1.2188,1.2188 -1.2188,3.1875 0,4.4062 1.2188,1.2187 3.1875,1.2188 4.4062,0 l 10.281,-10.281 v 61.219 c 0,1.7188 1.4062,3.125 3.125,3.125 1.7188,0 3.125,-1.4062 3.125,-3.125 V 0.6643 l 10.281,10.281 c 1.2188,1.2188 3.1875,1.2188 4.4062,0 1.2187,-1.2188 1.2188,-3.1875 0,-4.4062 z";

  const COLONNE_DIREZIONE_VENTO = ["ecita direzione", "RF direzione"];
  const ALTEZZA_CORSIA_FRECCE = 34;
  const MARGINE_CORSIA_FRECCE = 8; // sopra la legenda, sotto la corsia
  const MARGINE_SOTTO_FRECCE = -10; // sotto le etichette della data, sopra la corsia

  function formattaDataOraFreccia(istante) {
    const MESI = [
      "gen", "feb", "mar", "apr", "mag", "giu",
      "lug", "ago", "set", "ott", "nov", "dic",
    ];
    const d = new Date(istante);
    return (
      String(d.getDate()).padStart(2, "0") +
      " " +
      MESI[d.getMonth()] +
      " " +
      String(d.getHours()).padStart(2, "0") +
      ":" +
      String(d.getMinutes()).padStart(2, "0")
    );
  }

  function costruisciFrecceDirezione(dati, serie) {
    if (serie !== "vento") return null;

    const colonnePresenti = COLONNE_DIREZIONE_VENTO.filter(function (nome) {
      return dati.tracce.some(function (t) {
        return t.nome === nome;
      });
    });
    if (!colonnePresenti.length) return null;

    const series = colonnePresenti.map(function (nome) {
      const traccia = dati.tracce.find(function (t) {
        return t.nome === nome;
      });
      const datiFreccia = dati.tempo
        .map(function (istante, i) {
          return { istante: istante, direzione: traccia.valori[i] };
        })
        .filter(function (p) {
          return p.direzione != null;
        })
        .map(function (p) {
          return { value: [p.istante, nome], direzione: p.direzione };
        });
      return {
        name: nome,
        type: "scatter",
        xAxisIndex: 1,
        yAxisIndex: 1,
        symbol: SIMBOLO_FRECCIA_VENTO,
        symbolSize: [9, 18],
        symbolRotate: function (value, params) {
          return (params.data.direzione + 180) % 360;
        },
        itemStyle: { color: COLORE_SORGENTE[nome] || "#5a6b7b" },
        tooltip: {
          trigger: "item",
          formatter: function (params) {
            return formattaDataOraFreccia(params.data.value[0]);
          },
        },
        data: datiFreccia,
      };
    });

    return {
      grid: {
        left: 44,
        right: 14,
        bottom:
          RIGHE_LEGENDA_PER_SERIE[serie].length * ALTEZZA_RIGA_LEGENDA +
          MARGINE_CORSIA_FRECCE,
        height: ALTEZZA_CORSIA_FRECCE,
      },
      xAxis: { type: "time", gridIndex: 1, show: false },
      yAxis: { type: "category", gridIndex: 1, data: colonnePresenti, show: false },
      series: series,
    };
  }

  // Costruisce l'intero oggetto option di ECharts per una serie.
  function opzioni(dati, serie) {
    const cfg = CONFIG_SERIE[serie] || CONFIG_DEFAULT;
    const frecce = costruisciFrecceDirezione(dati, serie);
    const grigliaPrincipale = {
      left: 44,
      right: 14,
      top: 50,
      bottom: altezzaLegenda(serie) +
        (frecce ? ALTEZZA_CORSIA_FRECCE + MARGINE_CORSIA_FRECCE + MARGINE_SOTTO_FRECCE : 0),
    };
    const assePrincipaleX = {
      type: "time",
      minInterval: 3600 * 1000,
      axisLabel: {
        fontSize: 11,
        interval: function (index, valore) {
          return new Date(valore).getHours() % 3 === 0;
        },
        formatter: function (valore) {
          const GIORNI = ["dom", "lun", "mar", "mer", "gio", "ven", "sab"];
          const MESI = [
            "gen", "feb", "mar", "apr", "mag", "giu",
            "lug", "ago", "set", "ott", "nov", "dic",
          ];
          const d = new Date(valore);
          if (d.getHours() === 0) {
            const giorno = String(d.getDate()).padStart(2, "0");
            return (
              "{bold|" + GIORNI[d.getDay()] + "}\n{bold|" +
              giorno + " " + MESI[d.getMonth()] + "}"
            );
          }
          return String(d.getHours()).padStart(2, "0") + ":00";
        },
        rich: { bold: { fontWeight: "bold", lineHeight: 16 } },
      },
      axisTick: {
        interval: function (index, valore) {
          return new Date(valore).getHours() % 3 === 0;
        },
      },
    };
    return {
      animation: true,
      animationDuration: 700,
      animationEasing: "linear",
      animationThreshold: 10000,
      grid: frecce ? [grigliaPrincipale, frecce.grid] : grigliaPrincipale,
      tooltip: {
        trigger: "axis",
        textStyle: { fontSize: 10 },
        padding: 2,
        formatter: function (params) {
          const righe = params
            .map(function (p) {
              if (ESCLUSI_TOOLTIP.has(p.seriesName)) return null;
              const val = Array.isArray(p.value) ? p.value[1] : p.value;
              if (val == null) return null;
              const arrotondato = Math.round(val * 10) / 10;
              return (
                '<div style="display:flex;justify-content:space-between;align-items:center;margin:6px 0;">' +
                "<span>" +
                p.marker +
                p.seriesName +
                "</span>" +
                '<span style="font-weight:bold;margin-left:12px;">' +
                arrotondato +
                "</span>" +
                "</div>"
              );
            })
            .filter(function (r) {
              return r !== null;
            })
            .join("");
          const etichettaTempo = params.length ? params[0].axisValueLabel : "";
          return (
            '<div style="font-size:11px;line-height:14px;">' +
            etichettaTempo +
            righe +
            "</div>"
          );
        },
      },

      toolbox: {
        top: -15,
        left: 15,
        itemSize: 15,
        itemGap: 10,
        feature: {
          dataZoom: {
            // yAxisIndex rimosso: zoom rettangolare su x e y, come in Plotly
            iconStyle: { borderColor: "#5a6b7b" },
            emphasis: { iconStyle: { borderColor: "#d62728", borderWidth: 2 } },
          },
          saveAsImage: {},
        },
      },
    legend: costruisciLegenda(dati, serie),
      xAxis: frecce ? [assePrincipaleX, frecce.xAxis] : assePrincipaleX,
      yAxis: frecce
        ? [costruisciAsseY(cfg, dati), frecce.yAxis]
        : costruisciAsseY(cfg, dati),
      series: frecce
        ? costruisciTracce(dati, serie).concat(frecce.series)
        : costruisciTracce(dati, serie),
    };
  }

  // API pubblica: disegna (o aggiorna) il grafico della serie nel contenitore.
  // Riusa l'istanza ECharts già presente sul contenitore, se c'è.
  function disegna(contenitore, dati, serie) {
    const esistente = echarts.getInstanceByDom(contenitore);
    const grafico = esistente || echarts.init(contenitore);
    const opz = opzioni(dati, serie);

    // Se il grafico esisteva gia' (non e' il primo disegno), preservo cio'
    // che l'utente ha acceso/spento a mano nella legenda: altrimenti ogni
    // ridisegno (cambio data, "Oggi", rotella sul calendario, refresh...)
    // lo resetterebbe silenziosamente ai default, con notMerge:true.
    // getOption().legend e' sempre un array (anche per le serie con un solo
    // componente legend, come prima): ora che alcune serie ne hanno uno per
    // voce, si uniscono gli "selected" di TUTTI i componenti vecchi in
    // un'unica mappa e la si riapplica a tutti i componenti nuovi.
    if (esistente) {
      const vecchiaLegenda = esistente.getOption().legend || [];
      const vecchioSelected = {};
      vecchiaLegenda.forEach(function (l) {
        Object.assign(vecchioSelected, l.selected);
      });
      if (Object.keys(vecchioSelected).length) {
        const nuoveLegende = Array.isArray(opz.legend)
          ? opz.legend
          : [opz.legend];
        nuoveLegende.forEach(function (l) {
          l.selected = Object.assign({}, l.selected, vecchioSelected);
        });
      }
    }

    grafico.setOption(opz, { notMerge: true });
    return grafico;
  }

  return {
    disegna: disegna,
    opzioni: opzioni, // esposta per test/uso avanzato
    CONFIG_SERIE: CONFIG_SERIE,
  };
})();
