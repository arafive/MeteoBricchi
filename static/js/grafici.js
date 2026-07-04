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
      autoRange: true,
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
    "QRF modulo 25°-75°",
    "QRF raffica 25°-75°",
    // "QRF Tmin",
    // "QRF Tmin 25°-75°",
    // "Obs Tmin",
    // "QRF Tmean 25°-75°",
    // "QRF Tmax",
    // "QRF Tmax 25°-75°",
    // "Obs Tmax",
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

    const DEFINIZIONI_BANDA = [
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
    ];

    const tracceBanda = [];
    DEFINIZIONI_BANDA.forEach(function (def) {
      const traccBassa = dati.tracce.find(function (t) {
        return t.nome === def.nomi.basso;
      });
      const traccAlta = dati.tracce.find(function (t) {
        return t.nome === def.nomi.alto;
      });
      if (!traccBassa || !traccAlta) return;

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
      console.log("Traccia:", t.nome, "min:", tMin, "max:", tMax);
      if (tMin < min) min = tMin;
      if (tMax > max) max = tMax;
    });
    if (!isFinite(min) || !isFinite(max)) return null;
    console.log("ESTREMO GLOBALE min:", min, "max:", max);
    return { min: min, max: max };
  }

  function costruisciAsseY(cfg, dati) {
    const yAxis = { type: "value", axisLabel: { fontSize: 11 } };

    let yMin = cfg.yMin;
    let yMax = cfg.yMax;

    if (cfg.autoRange) {
      const estremi = calcolaEstremiDati(dati);
      if (estremi) {
        const passo = cfg.tickInterval || 1;
        yMin = Math.floor(estremi.min / passo) * passo - passo;
        yMax = Math.ceil(estremi.max / passo) * passo + passo;
      }
    }

    if (yMin !== null && yMin !== undefined) yAxis.min = yMin;
    if (yMax !== null && yMax !== undefined) yAxis.max = yMax;
    console.log("yAxis finale:", {
      min: yAxis.min,
      max: yAxis.max,
      interval: yAxis.interval,
    });
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
  function costruisciLegenda(serie) {
    const stileVoce = {
      icon: "path://M0,7 L20,7 L20,13 L0,13 Z",
      textStyle: { fontSize: 11 },
      itemWidth: 18,
      itemHeight: 10,
      itemGap: 12,
    };

    if (serie === "vento") {
      return Object.assign(
        { top: 4, right: 10, orient: "vertical", align: "right" },
        stileVoce,
        {
          data: [
            "QRF modulo",
            "QRF modulo 25°-75°",
            "Raw modulo",
            "Obs modulo",
            { name: "__sep0__", icon: "none" }, // separatore invisibile tra i due gruppi
            { name: "__sep1__", icon: "none" }, // separatore invisibile tra i due gruppi
            { name: "__sep2__", icon: "none" }, // separatore invisibile tra i due gruppi
            "QRF raffica",
            "QRF raffica 25°-75°",
            "Raw raffica",
            "Obs raffica",
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
        { top: 4, right: 10, orient: "vertical", align: "right" },
        stileVoce,
        {
          data: [
            "QRF Tmin",
            "QRF Tmin 25°-75°",
            "Obs Tmin",
            { name: "__sep0__", icon: "none" }, // separatore invisibile tra i due gruppi
            { name: "__sep1__", icon: "none" }, // separatore invisibile tra i due gruppi
            { name: "__sep2__", icon: "none" }, // separatore invisibile tra i due gruppi
            { name: "__sep3__", icon: "none" }, // separatore invisibile tra i due gruppi
            "QRF Tmean",
            "QRF Tmean 25°-75°",
            "Obs Tmean",
            "Raw Tmean",
            "Clima Tmean",
            { name: "__sep3__", icon: "none" }, // separatore invisibile tra i due gruppi
            { name: "__sep4__", icon: "none" }, // separatore invisibile tra i due gruppi
            { name: "__sep5__", icon: "none" }, // separatore invisibile tra i due gruppi
            { name: "__sep6__", icon: "none" }, // separatore invisibile tra i due gruppi
            "QRF Tmax",
            "QRF Tmax 25°-75°",
            "Obs Tmax",
          ],
          formatter: function (nome) {
            return nome.indexOf("__sep") === 0 ? "" : nome;
          },
          selected: costruisciSelected(),
        },
      );
    }
    return Object.assign({ top: 4 }, stileVoce, {
      selected: costruisciSelected(),
    });
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
        right: serie === "vento" || serie === "temperatura" ? 150 : 14,
        top: 50,
        bottom: 26,
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
    const grafico =
      echarts.getInstanceByDom(contenitore) || echarts.init(contenitore);
    grafico.setOption(opzioni(dati, serie), { notMerge: true });
    return grafico;
  }

  return {
    disegna: disegna,
    opzioni: opzioni, // esposta per test/uso avanzato
    CONFIG_SERIE: CONFIG_SERIE,
  };
})();
