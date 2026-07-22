
import warnings
warnings.simplefilter('ignore', FutureWarning)
warnings.simplefilter('ignore', UserWarning)

import os
import configparser

import pandas as pd

from datetime import datetime, timezone

from danilib import f_settaggio_db_arpal

os.chdir('/run/media/daniele.carnevale/Daniele2TB/repo/MeteoBricchi')
config = configparser.ConfigParser()
config.read('./config.ini')

cartella_destinazione = f"{config.get('DATI2D', 'cartella')}/fulmini"


def f_query(coord, t1_UTC, t2_UTC):
    
    connessione = f_settaggio_db_arpal()
    
    query = f"""
    select
    to_char(DTRFSEC, 'YYYY-MM-DD HH24:MI:SS') as DTRFSEC,
    lon/1e4 as lon,
    lat/1e4 as lat,
    intensity,
    commt
    
    from cfmi.lamps
    where DTRFSEC between to_date('{t1_UTC.strftime(format='%Y%m%d%H%M')}', 'YYYYMMDDHH24MI') AND to_date('{t2_UTC.strftime(format='%Y%m%d%H%M')}', 'YYYYMMDDHH24MI')
    and lon between {int(coord[0] * 10000)} and {int(coord[1] * 10000)} and lat between {int(coord[2] * 10000)} and {int(coord[3] * 10000)}
    and intensity>0
    
    order by DTRFSEC asc
    
    """
    
    df_query = pd.read_sql(query, con=connessione)
    df_query['DTRFSEC'] = pd.to_datetime(df_query['DTRFSEC'])
    df_query = df_query[['DTRFSEC', 'LON', 'LAT', 'INTENSITY', 'COMMT']]

    return df_query


# %%
area = (4.5, 20.4, 35.0, 47.8) # italia
sovrascrivi = True

adesso_0_UTC = pd.to_datetime(datetime.now(timezone.utc)).tz_localize(None).floor('5min')
# I fulmini hanno bisogno di qualche minuto per essere caricati, quindi aspetto 10 minuti
# che è circa il tempo di ritardo di una scansione radar
adesso_0_UTC = adesso_0_UTC - pd.Timedelta(minutes=10)

# lista_tempi = [adesso_0_UTC]
# lista_tempi = pd.date_range('2026-09-01 00:00:00', adesso_0_UTC + pd.Timedelta(hours=1), freq='5min')
lista_tempi = pd.date_range('2025-09-01 00:00:00', '2025-09-03 00:00:00', freq='5min')

for adesso_0_UTC in lista_tempi:
    print(f"\n----------------\nSono le {datetime.now(timezone.utc).strftime('%H:%M:%S UTC del %Y-%m-%d')}")
    print(f'{cartella_destinazione=}')
    
    adesso_1_UTC = adesso_0_UTC - pd.Timedelta(minutes=5)
    
    print(f'{adesso_1_UTC=}')
    print(f'{adesso_0_UTC=}')
    
    cartella_file_csv = f"{cartella_destinazione}/{adesso_0_UTC.strftime(format='%Y/%m/%d')}"
    os.makedirs(cartella_file_csv, exist_ok=True)
    
    nome_file_csv = f"fulmini_{adesso_0_UTC.strftime(format='%Y-%m-%d_%H%M')}.csv"
    print(f'{nome_file_csv=}')
    
    # if os.path.exists(f'{cartella_file_csv}/{nome_file_csv}') and not sovrascrivi:
    #     print('Esiste già il file. Esco.')
    #     continue

    df_query = f_query(area, adesso_1_UTC, adesso_0_UTC)

    # Converto il tempo in secondi dall'1970-01-01. Uso la differenza da
    # pd.Timestamp("1970-01-01") diviso per pd.Timedelta("1s") invece di
    # astype("int64") // 10**9: quest'ultimo assume che il dtype interno
    # sia datetime64[ns] (nanosecondi), ma pandas puo' restituire una
    # risoluzione diversa (es. datetime64[us], microsecondi, capitato qui),
    # nel qual caso "// 10**9" divide per un fattore sbagliato di 1000 e
    # schiaccia tutta la precisione sotto i ~16 minuti. Il metodo con
    # Timedelta da' i secondi corretti indipendentemente dalla risoluzione.
    df_query["DTRFSEC"] = (
        df_query["DTRFSEC"] - pd.Timestamp("1970-01-01")
    ) // pd.Timedelta("1s")
    df_query[['DTRFSEC', 'LON', 'LAT', 'INTENSITY']] = (df_query[['DTRFSEC', 'LON', 'LAT', 'INTENSITY']] * 10000).astype(int)

    df_query.to_csv(f'{cartella_file_csv}/{nome_file_csv}', index=True, header=True, mode='w')

print('Done\n')

# %% Plot di controllo

# import matplotlib.pyplot as plt
# import cartopy.crs as ccrs
# import cartopy.feature as cfeature

# cartella = f'{cartella_destinazione}/2026/07/02'
# for i in sorted(os.listdir(cartella)):
#     df_query = pd.read_csv(f'{cartella}/{i}', index_col=0) / 10000
    
#     fig, ax = plt.subplots(figsize=(8, 10), subplot_kw={'projection': ccrs.PlateCarree()})
    
#     ax.coastlines(resolution='10m', lw=0.75)
#     ax.add_feature(cfeature.BORDERS, lw=0.75)
#     ax.set_extent(area, crs=ccrs.PlateCarree()) # lig
    
#     ax.scatter(
#         df_query["LON"],
#         df_query["LAT"],
#         s=2,
#         # ---
#         # c=df_query["INTENSITY"],
#         # vmin=1000,
#         # vmax=200000,
#         # ---
#         c=df_query["DTRFSEC"],
#         vmax=df_query["DTRFSEC"].max(),
#         vmin=df_query["DTRFSEC"].min(),
#         # ---
#         cmap="jet",
#         alpha=0.7,
#         edgecolors='none',
#         transform=ccrs.PlateCarree()
#     )
    
#     adesso_0_UTC = pd.to_datetime(df_query["DTRFSEC"].max(), unit="s")
#     adesso_1_UTC = pd.to_datetime(df_query["DTRFSEC"].min(), unit="s")
    
#     ax.set_title("Fulmini nei passati 5 minuti", loc='left', fontsize=10)
#     ax.set_title(f"{adesso_1_UTC.strftime('%Y-%m-%d %H:%M:%S')} - {adesso_0_UTC.strftime('%Y-%m-%d %H:%M:%S')}", loc='right', fontsize=10)
    
#     plt.show()
#     plt.close()

# %% Plot della colorbar

# import numpy as np
#
# import matplotlib.pyplot as plt
# import matplotlib.colors as mcolors
# import matplotlib.patheffects as path_effects
#
# livelli = np.arange(255)
# lista_finestre_minuti = [5, 30, 60, 180, 720, 1440]
#
# dict_tempi_labels = {
#     5: {'tempi': [0, 1, 2, 3, 4, 5], 'labels': ['', '1min', '2min', '3min', '4min', '5min']},
#     30: {'tempi': [0, 5, 10, 15, 20, 25, 30], 'labels': ['', '5min', '10min', '15min', '20min', '25min', '30min']},
#     60: {'tempi': [0, 10, 20, 30, 40, 50, 60], 'labels': ['', '10min', '20min', '30min', '40min', '50min', '1h']},
#     180: {'tempi': [0, 30, 60, 90, 120, 150, 180], 'labels': ['', '30min', '1h', '1:30h', '2h', '2:30h', '3h']},
#     360: {'tempi': [0, 60, 120, 180, 240, 300, 360], 'labels': ['', '1h', '2h', '3h', '4h', '5h', '6h']},
#     1440: {'tempi': [0, 240, 480, 720, 960, 1200, 1440], 'labels': ['', '4h', '8h', '12h', '16h', '20h', '24h']},
#     }
#
# for finestra_minuti in dict_tempi_labels.keys():
#
#     tempi = np.array(dict_tempi_labels[finestra_minuti]['tempi']) / finestra_minuti * 255
#     labels = dict_tempi_labels[finestra_minuti]['labels']
#
#     cmap = plt.get_cmap('plasma', 256)
#     norm = mcolors.BoundaryNorm(livelli, cmap.N)
#
#     ###################
#
#     fig, ax = plt.subplots(figsize=(10, 0.3))
#
#     sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
#     sm.set_array([])
#
#     cbar = plt.colorbar(
#         sm,
#         cax=ax,
#         orientation="horizontal",
#     )
#
#     # niente ticks
#     cbar.ax.set_xticks([])                 # major ticks OFF
#     cbar.ax.set_xticks([], minor=True)     # minor ticks OFF
#     cbar.ax.tick_params(which='both', length=0)
#     cbar.ax.minorticks_off()
#
#     label_fontsize = 9
#     unit_fontsize = 11
#
#     # label valori (bold)
#     for tempo, lab in zip(tempi, labels):
#         x = 1 - tempo / 255
#         cbar.ax.text(
#             x, -0.25, lab,
#             transform=cbar.ax.transAxes,
#             ha='center',
#             va='top',
#             fontsize=label_fontsize,
#             fontweight='bold',
#             color='black',
#             path_effects=[
#                 path_effects.withStroke(linewidth=3, foreground="white")
#             ]
#         )
#
#     # # unità a destra (bold)
#     # cbar.ax.text(
#     #     1.06, 0.5, "mm/h",
#     #     transform=cbar.ax.transAxes,
#     #     ha='left',
#     #     va='center',
#     #     fontsize=unit_fontsize,
#     #     fontweight='bold',
#     #     color='black',
#     #     path_effects=[
#     #         path_effects.withStroke(linewidth=3, foreground="white")
#     #     ]
#     # )
#
#     # estetica pulita
#     cbar.outline.set_visible(True)
#     cbar.outline.set_edgecolor("black")
#     cbar.outline.set_linewidth(1.0)
#     fig.patch.set_alpha(0)
#     ax.patch.set_alpha(0)
#
#     plt.savefig(
#         f"./static/icone/colorbar_fulmini_{finestra_minuti}.png",
#         dpi=600,
#         transparent=True,
#         bbox_inches="tight",
#         pad_inches=0.1
#     )
#
#     plt.show()
#     plt.close()
