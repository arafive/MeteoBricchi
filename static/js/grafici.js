/* grafici.js — generazione dei grafici delle SERIE (dati 1D) con ECharts.
 *
 * Il modulo NON conosce mappa, popup o fetch: riceve un contenitore, i dati
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
    "QRF Tmin": "#17becf",
    "QRF Tmean": "#2ca02c",
    "QRF Tmax": "#d62728",
    "Obs Tmin": "#000000",
    "Obs Tmean": "#000000",
    "Obs Tmax": "#000000",
    "Raw Tmean": "#ff7f0e",
    "Clima Tmean": "#9467bd",
    //
    "QRF modulo": "#17becf",
    "Raw modulo": "#1f77b4",
    "Obs modulo": "#000000",
    "QRF raffica": "#9467bd",
    "Raw raffica": "#d62728",
    "Obs raffica": "#000000",
  };

  const STILE_SORGENTE = {
    "QRF Tmin": "dashed",
    "QRF Tmean": "solid",
    "QRF Tmax": "dotted",
    "Obs Tmin": "dashed",
    "Obs Tmean": "solid",
    "Obs Tmax": "dotted",
    "Raw Tmean": "solid",
    "Clima Tmean": "solid",
    //
    "QRF modulo": "solid",
    "Raw modulo": "solid",
    "Obs modulo": "solid",
    "QRF raffica": "dashed",
    "Raw raffica": "dashed",
    "Obs raffica": "dashed",
  };

  // Nomi di serie da non mostrare mai nel tooltip (aggiungi qui le label da escludere)
  const ESCLUSI_TOOLTIP = new Set([
    "QRF modulo 25°-75°",
    "QRF raffica 25°-75°",
    "QRF Tmin 25°-75°",
    "QRF Tmean 25°-75°",
    "QRF Tmax 25°-75°",
  ]);

  const DISATTIVATI_DEFAULT = new Set([
    // vento: acceso di default solo QRF modulo, Obs modulo, QRF raffica, Obs raffica
    "QRF modulo 25°-75°",
    "Raw modulo",
    "QRF raffica 25°-75°",
    "Raw raffica",
    // temperatura: acceso di default solo QRF Tmin, QRF Tmean, QRF Tmax, Obs Tmean
    "QRF Tmin 25°-75°",
    "Obs Tmin",
    "QRF Tmean 25°-75°",
    "Raw Tmean",
    "Clima Tmean",
    "QRF Tmax 25°-75°",
    "Obs Tmax",
  ]);

  function costruisciSelected() {
    const selected = {};
    DISATTIVATI_DEFAULT.forEach(function (nome) {
      selected[nome] = false;
    });
    return selected;
  }

  // Nomi delle tracce di quantile usate per costruire la banda (non renderizzate come linee singole)
  const NOMI_BANDA_TMIN = { basso: "QRF Tmin 0.25", alto: "QRF Tmin 0.75" };
  const NOMI_BANDA_TMEAN = { basso: "QRF Tmean 0.25", alto: "QRF Tmean 0.75" };
  const NOMI_BANDA_TMAX = { basso: "QRF Tmax 0.25", alto: "QRF Tmax 0.75" };
  const NOMI_BANDA_MODULO = {
    basso: "QRF modulo 0.25",
    alto: "QRF modulo 0.75",
  };
  const NOMI_BANDA_RAFFICA = {
    basso: "QRF raffica 0.25",
    alto: "QRF raffica 0.75",
  };

  // Costruisce le tracce (linee) ECharts dai dati grezzi.
  function costruisciTracce(dati, serie) {
    const nomiBanda = new Set([
      NOMI_BANDA_TMIN.basso,
      NOMI_BANDA_TMIN.alto,
      NOMI_BANDA_TMEAN.basso,
      NOMI_BANDA_TMEAN.alto,
      NOMI_BANDA_TMAX.basso,
      NOMI_BANDA_TMAX.alto,
      NOMI_BANDA_MODULO.basso,
      NOMI_BANDA_MODULO.alto,
      NOMI_BANDA_RAFFICA.basso,
      NOMI_BANDA_RAFFICA.alto,
    ]);

    const tracceNormali = dati.tracce
      .filter(function (t) {
        return !nomiBanda.has(t.nome);
      })
      .map(function (t) {
        return {
          name: t.nome,
          type: "line",
          showSymbol: false,
          symbol: "none",
          smooth: true,
          color: COLORE_SORGENTE[t.nome],
          lineStyle: { width: 3, type: STILE_SORGENTE[t.nome] },
          // [istante, valore]; i null creano le interruzioni
          data: dati.tempo.map(function (istante, i) {
            return [istante, t.valori[i]];
          }),
        };
      });

    // Solo le bande pertinenti alla serie in disegno: prima si cercavano
    // sempre tutte e 5 (anche quelle dell'altra serie), che non trovandole
    // mai facevano scattare il warning di debug per un falso positivo.
    const DEFINIZIONI_BANDA_PER_SERIE = {
      temperatura: [
        {
          nomi: NOMI_BANDA_TMIN,
          colore: "rgba(23, 190, 207, 0.5)",
          etichetta: "QRF Tmin 25°-75°",
        },
        {
          nomi: NOMI_BANDA_TMEAN,
          colore: "rgba(44, 160, 44, 0.5)",
          etichetta: "QRF Tmean 25°-75°",
        },
        {
          nomi: NOMI_BANDA_TMAX,
          colore: "rgba(214, 39, 40, 0.5)",
          etichetta: "QRF Tmax 25°-75°",
        },
      ],
      vento: [
        {
          nomi: NOMI_BANDA_MODULO,
          colore: "rgba(23, 190, 207, 0.5)",
          etichetta: "QRF modulo 25°-75°",
        },
        {
          nomi: NOMI_BANDA_RAFFICA,
          colore: "rgba(148, 103, 189, 0.5)",
          etichetta: "QRF raffica 25°-75°",
        },
      ],
    };
    const DEFINIZIONI_BANDA = DEFINIZIONI_BANDA_PER_SERIE[serie] || [];

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
            return [istante, traccBassa.valori[i]];
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
              basso == null || alto == null ? null : alto - basso,
            ];
          }),
        },
      );
    });

    // Serie fittizia vuota: dà "corpo" alla voce separatore della legenda (solo vento).
    const tracceSeparatore = [
      { name: "__sep0__", type: "line", data: [], silent: true },
      { name: "__sep1__", type: "line", data: [], silent: true },
      { name: "__sep2__", type: "line", data: [], silent: true },
      { name: "__sep3__", type: "line", data: [], silent: true },
      { name: "__sep4__", type: "line", data: [], silent: true },
      { name: "__sep5__", type: "line", data: [], silent: true },
      { name: "__sep6__", type: "line", data: [], silent: true },
    ];

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
    return tracceNormali.concat(tracceBanda, tracceSeparatore, tracceSoglie);
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
  // Per "vento" servono due colonne separate (modulo / raffica).
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

  function costruisciLegenda(serie) {
    const stileVoce = {
      textStyle: { fontSize: 11 },
      itemWidth: 18,
      itemHeight: 10,
      itemGap: 12,
    };
    // Le bande 25°-75° rappresentano un'AREA piena (la loro lineStyle e'
    // invisibile, opacity 0): stessa icona "solid" delle linee continue.
    const iconaBanda = ICONA_PER_STILE.solid;

    // Voce di legenda per una traccia vera (non banda, non separatore):
    // sceglie l'icona in base allo stile reale della linea (STILE_SORGENTE).
    function voce(nome) {
      return {
        name: nome,
        icon: ICONA_PER_STILE[STILE_SORGENTE[nome]] || ICONA_PER_STILE.solid,
      };
    }

    if (serie === "vento") {
      return Object.assign(
        { bottom: 0, left: "center", orient: "horizontal" },
        stileVoce,
        {
          data: [
            voce("QRF modulo"),
            { name: "QRF modulo 25°-75°", icon: iconaBanda },
            voce("Raw modulo"),
            voce("Obs modulo"),
            { name: "__sep0__", icon: "none" }, // separatore invisibile tra i due gruppi
            { name: "__sep1__", icon: "none" }, // separatore invisibile tra i due gruppi
            { name: "__sep2__", icon: "none" }, // separatore invisibile tra i due gruppi
            voce("QRF raffica"),
            { name: "QRF raffica 25°-75°", icon: iconaBanda },
            voce("Raw raffica"),
            voce("Obs raffica"),
          ],
          formatter: function (nome) {
            return nome.indexOf("__sep") === 0 ? "" : nome;
          },
          selected: costruisciSelected(),
        },
      );
    }

    if (serie === "temperatura") {
      return Object.assign(
        { bottom: 0, left: "center", orient: "horizontal" },
        stileVoce,
        {
          data: [
            voce("QRF Tmin"),
            { name: "QRF Tmin 25°-75°", icon: iconaBanda },
            voce("Obs Tmin"),
            { name: "__sep0__", icon: "none" }, // separatore invisibile tra i due gruppi
            { name: "__sep1__", icon: "none" }, // separatore invisibile tra i due gruppi
            { name: "__sep2__", icon: "none" }, // separatore invisibile tra i due gruppi
            { name: "__sep3__", icon: "none" }, // separatore invisibile tra i due gruppi
            voce("QRF Tmean"),
            { name: "QRF Tmean 25°-75°", icon: iconaBanda },
            voce("Obs Tmean"),
            voce("Raw Tmean"),
            voce("Clima Tmean"),
            { name: "__sep4__", icon: "none" }, // separatore invisibile tra i due gruppi
            { name: "__sep5__", icon: "none" }, // separatore invisibile tra i due gruppi
            { name: "__sep6__", icon: "none" }, // separatore invisibile tra i due gruppi
            voce("QRF Tmax"),
            { name: "QRF Tmax 25°-75°", icon: iconaBanda },
            voce("Obs Tmax"),
          ],
          formatter: function (nome) {
            return nome.indexOf("__sep") === 0 ? "" : nome;
          },
          selected: costruisciSelected(),
        },
      );
    }
    return Object.assign(
      { bottom: 0, left: "center", orient: "horizontal" },
      stileVoce,
      {
        selected: costruisciSelected(),
      },
    );
  }

  // Costruisce l'intero oggetto option di ECharts per una serie.
  function opzioni(dati, serie) {
    const cfg = CONFIG_SERIE[serie] || CONFIG_DEFAULT;
    return {
      animation: true,
      animationDuration: 700,
      animationEasing: "linear",
      animationThreshold: 10000,
      grid: {
        left: 44,
        right: 14,
        top: 50,
        bottom: 100, // spazio per la legenda orizzontale sotto l'asse x, su piu' righe se serve
      },
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
      legend: costruisciLegenda(serie),
      xAxis: {
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
              "gen",
              "feb",
              "mar",
              "apr",
              "mag",
              "giu",
              "lug",
              "ago",
              "set",
              "ott",
              "nov",
              "dic",
            ];
            const d = new Date(valore);
            if (d.getHours() === 0) {
              const giorno = String(d.getDate()).padStart(2, "0");
              return (
                "{bold|" +
                GIORNI[d.getDay()] +
                "}\n{bold|" +
                giorno +
                " " +
                MESI[d.getMonth()] +
                "}"
              );
            }
            return String(d.getHours()).padStart(2, "0") + ":00";
          },
          rich: {
            bold: { fontWeight: "bold", lineHeight: 16 },
          },
        },
        axisTick: {
          interval: function (index, valore) {
            return new Date(valore).getHours() % 3 === 0;
          },
        },
      },
      yAxis: costruisciAsseY(cfg, dati),
      series: costruisciTracce(dati, serie),
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
    if (esistente) {
      const vecchiaLegenda = esistente.getOption().legend;
      const vecchioSelected =
        vecchiaLegenda && vecchiaLegenda[0] && vecchiaLegenda[0].selected;
      if (vecchioSelected) {
        opz.legend.selected = Object.assign(
          {},
          opz.legend.selected,
          vecchioSelected,
        );
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
