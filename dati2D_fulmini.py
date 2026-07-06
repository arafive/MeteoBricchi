
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
    df_query = df_query[['DTRFSEC', 'LON', 'LAT', 'INTENSITY']]

    return df_query


# %%
area = (4.5, 20.4, 35.0, 47.8) # italia
sovrascrivi = True

adesso_0_UTC = pd.to_datetime(datetime.now(timezone.utc)).tz_localize(None).floor('5min')
# I fulmini hanno bisogno di qualche minuto per essere caricati, quindi aspetto 10 minuti
# che è circa il tempo di ritardo di una scansione radar
adesso_0_UTC = adesso_0_UTC - pd.Timedelta(minutes=10)

lista_tempi = [adesso_0_UTC]
# lista_tempi = pd.date_range('2026-07-03 16:00:00', adesso_0_UTC + pd.Timedelta(hours=1), freq='5min')

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
    
    if os.path.exists(f'{cartella_file_csv}/{nome_file_csv}') and not sovrascrivi:
        print('Esiste già il file. Esco.')
        try:
            exit()
        except NameError:
            continue

    df_query = f_query(area, adesso_1_UTC, adesso_0_UTC)
            
    # Converto il tempo in secondi dall'1970-01-01
    df_query["DTRFSEC"] = df_query["DTRFSEC"].astype("int64") // 10**9
    df_query = (df_query * 10000).astype(int)
    
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
