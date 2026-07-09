
import os
import json
import configparser

import numpy as np
import pandas as pd
import xarray as xr
from pyproj import CRS
from datetime import datetime, timezone
from rasterio.transform import from_origin
from rasterio.warp import calculate_default_transform, reproject, Resampling
from PIL import Image

username = "Daniele_Carnevale"
access_key = "15fcff78d4194bc4beacda6173861e6d"
dataset = "italian-radar-dpc-sri.zarr"

dataset_url = f"https://{username}:{access_key}@api.arcodatahub.com/S3/{dataset}"
ds_tot = xr.open_dataset(dataset_url, engine="zarr")

os.chdir('/run/media/daniele.carnevale/Daniele2TB/repo/MeteoBricchi')
# os.chdir('/media/daniele/Daniele2TB/repo/MeteoBricchi')
config = configparser.ConfigParser()
config.read('./config.ini')

cartella_destinazione = f"{config.get('DATI2D', 'cartella')}/radar_sri"


def f_prendi_ultimo_istante_buono(ds):
    # Trovo il primo istante di tempo con dei dati
    for i in range(ds.time.shape[0] - 1, -1, -1):
        a = ds.isel(time=i).RR.values
        t = pd.to_datetime(ds.isel(time=i).time.values)
        
        if not np.all(np.isnan(a)):
            print(f'trovata {t}')
            return t
        else:
            print(f'Tutti NaN per {t}')
        
# %%
area = (4.5, 20.4, 35.0, 47.8) # italia
sovrascrivi = False

adesso_0_UTC = pd.to_datetime(datetime.now(timezone.utc)).tz_localize(None)

# lista_tempi = [adesso_0_UTC]
lista_tempi = pd.date_range('2026-07-09 10:00:00', adesso_0_UTC + pd.Timedelta(hours=1), freq='5min')

for adesso_0_UTC in lista_tempi:
    print(f"\n----------------\nSono le {datetime.now(timezone.utc).strftime('%H:%M:%S UTC del %Y-%m-%d')}")
    print(f'{cartella_destinazione=}')
    
    adesso_1_UTC = adesso_0_UTC - pd.Timedelta(hours=3)
    
    ds = ds_tot.sel(time=slice(adesso_1_UTC, adesso_0_UTC))
    
    tempo_buono = f_prendi_ultimo_istante_buono(ds)
    try:
        cartella_file = f"{cartella_destinazione}/{tempo_buono.strftime(format='%Y/%m/%d')}"
    except AttributeError:
        break
        
    os.makedirs(cartella_file, exist_ok=True)
    nome_file_png = f"radar_sri_{tempo_buono.strftime(format='%Y-%m-%d_%H%M')}.png"
    print(f'{nome_file_png=}')

    if os.path.exists(f'{cartella_file}/{nome_file_png}') and not sovrascrivi:
        print('Esiste già il file. Esco.')
        continue
    
    da = ds.sel(time=tempo_buono)
    
    # %% Plot di controllo
    # import matplotlib.pyplot as plt
    # import matplotlib.colors as mcolors
    # import cartopy.crs as ccrs
    # import cartopy.feature as cfeature
    
    # livelli = [0.2, 0.5, 1, 2, 3, 5, 7, 10, 15, 20, 25, 35, 45, 60, 75, 90, 120, 150, 180, 210]
    # labels = [str(x) for x in [0.2, 0.5, 1, 2, 3, 5, 7, 10, 15, 20, 25, 35, 45, 60, 75, 90, 120, 150, 180, 210]]
    # colori = ['#ffffff', '#e0ebff', '#b5c9ff', '#8eb2ff', '#7f96ff', '#6370f7', '#009f1e', '#3cbc3d', '#b9f96e', '#fff914', '#fac81e', '#eb9628', '#fa3c3c', '#cd005a', '#b400b4', '#9600c8', '#a064dc', '#be8cc8', '#e1afc3', '#e1c8be', '#f0dce1']
    
    # cmap = mcolors.ListedColormap(colori[1:-1])
    # cmap.set_under(colori[0])
    # cmap.set_over(colori[-1])
    # norm = mcolors.BoundaryNorm(livelli, cmap.N)
    
    # crs = ccrs.TransverseMercator(
    #     central_longitude=12.5,
    #     central_latitude=42.0,
    #     scale_factor=1.0,
    #     false_easting=0.0,
    #     false_northing=0.0,
    # )
    
    # fig, ax = plt.subplots(figsize=(8, 10), subplot_kw={'projection': crs})
    
    # ax.coastlines(resolution='10m', lw=0.75)
    # ax.add_feature(cfeature.BORDERS, lw=0.75)
    # ax.set_extent(area, crs=ccrs.PlateCarree())
       
    # plot_shaded = ax.contourf(
    #     da.lon,
    #     da.lat,
    #     da['RR'],
    #     levels=livelli,
    #     cmap=cmap,
    #     norm=norm,
    #     extend="both",
    #     transform=ccrs.PlateCarree()
    # )
    
    # # count_shaded = ax.contour(
    # #     da.lon,
    # #     da.lat,
    # #     da['RR'],
    # #     levels=livelli,
    # #     colors='black',
    # #     linewidths=0.15,
    # #     transform=ccrs.PlateCarree()
    # # )
    
    # ax.set_title(f"{da['RR'].long_name} [mm]", loc='left')
    # ax.set_title(str(pd.to_datetime(da.time.values)), loc='right')
    
    # # cbar = plt.colorbar(
    # #     plot_shaded,
    # #     ticks=livelli,
    # #     orientation='vertical',
    # #     extend='both',
    # #     drawedges=True,
    # #     shrink=0.45,
    # #     pad=0.01,
    # #     fraction=0.1,
    # # )
    
    # plt.show()
    # plt.close()
    
    # %% Plot della colorbar
    
    # import matplotlib.pyplot as plt
    # import matplotlib.colors as mcolors
    # import matplotlib.patheffects as path_effects
    
    # livelli = [0.2, 0.5, 1, 2, 3, 5, 7, 10, 15, 20, 25, 35, 45, 60, 75, 90, 120, 150, 180, 210]
    # labels = [str(x) for x in livelli]
    
    # colori = ['#ffffff', '#e0ebff', '#b5c9ff', '#8eb2ff', '#7f96ff', '#6370f7',
    #           '#009f1e', '#3cbc3d', '#b9f96e', '#fff914', '#fac81e', '#eb9628',
    #           '#fa3c3c', '#cd005a', '#b400b4', '#9600c8', '#a064dc', '#be8cc8',
    #           '#e1afc3', '#e1c8be', '#f0dce1']
    
    # cmap = mcolors.ListedColormap(colori[1:-1])
    # cmap.set_under(colori[0])
    # cmap.set_over(colori[-1])
    
    # norm = mcolors.BoundaryNorm(livelli, cmap.N)
    
    # ###################
    
    # fig, ax = plt.subplots(figsize=(10, 0.3))
    
    # sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    # sm.set_array([])
    
    # cbar = plt.colorbar(
    #     sm,
    #     cax=ax,
    #     orientation="horizontal",
    #     extend="both"
    # )
    
    # # niente ticks
    # cbar.ax.set_xticks([])                 # major ticks OFF
    # cbar.ax.set_xticks([], minor=True)     # minor ticks OFF
    # cbar.ax.tick_params(which='both', length=0)
    # cbar.ax.minorticks_off()
    
    # label_fontsize = 9
    # unit_fontsize = 11
    
    # # label valori (bold)
    # for i, (val, lab) in enumerate(zip(livelli, labels)):
    #     x = i / (len(livelli) - 1)
    #     cbar.ax.text(
    #         x, -0.25, lab,
    #         transform=cbar.ax.transAxes,
    #         ha='center',
    #         va='top',
    #         fontsize=label_fontsize,
    #         fontweight='bold',
    #         color='black',
    #         path_effects=[
    #             path_effects.withStroke(linewidth=3, foreground="white")
    #         ]
    #     )
    
    # # unità a destra (bold)
    # cbar.ax.text(
    #     1.06, 0.5, "mm/h",
    #     transform=cbar.ax.transAxes,
    #     ha='left',
    #     va='center',
    #     fontsize=unit_fontsize,
    #     fontweight='bold',
    #     color='black',
    #     path_effects=[
    #         path_effects.withStroke(linewidth=3, foreground="white")
    #     ]
    # )
    
    # # estetica pulita
    # cbar.outline.set_visible(True)
    # cbar.outline.set_edgecolor("black")
    # cbar.outline.set_linewidth(1.0)
    # fig.patch.set_alpha(0)
    # ax.patch.set_alpha(0)
    
    # plt.savefig(
    #     "./static/icone/colorbar_radar_sri.png",
    #     dpi=600,
    #     transparent=True,
    #     bbox_inches="tight",
    #     pad_inches=0.1
    # )
    
    # plt.show()
    # plt.close()
    
    # %%
    
    crs_wkt = CRS.from_wkt(da.crs.attrs["crs_wkt"]) # Data a ChatGPT
    
    # !!! Uesto NODATA non ha valore perché nel plot è sempre ignorato
    NODATA = -999  # coerente col formato gia' usato in app.py / index.html
    
    x = da["x"].values  # crescente, metri
    y = da["y"].values  # decrescente, metri (nord -> sud)
    dato = da.RR.values  # (y, x), NaN sui missing
    
    res_x = x[1] - x[0] # positivo
    res_y = y[0] - y[1] # positivo (passo assoluto, y decresce)
    
    # angolo top-left nello spazio proiettato (i valori x/y sono centri
    # pixel, quindi sposto di mezzo passo per ottenere il bordo)
    west = x[0] - res_x / 2
    north = y[0] + res_y / 2
    transform = from_origin(west, north, res_x, res_y)
    
    out = np.where(np.isnan(dato), NODATA, dato * 10).astype(int)
    
    ### Salvataggio in Geotiff compresso (NON PIU NECESSARIO)
    # import rasterio
    # with rasterio.open(
    #     f'{cartella_file}/{nome_file_png}', "w", # TODO modifica nome file in tif
    #     driver="GTiff",
    #     height=out.shape[0],
    #     width=out.shape[1],
    #     count=1,
    #     dtype=dato.dtype,
    #     crs=crs_wkt,
    #     transform=transform,
    #     nodata=NODATA,
    #     compress="deflate",
    #     zlevel=9
    # ) as dst:
    #     dst.write(out, 1)
        
    ### CLAUDE
    ### Riproiezione EPSG:3857 + colormap, generati qui invece che a runtime in
    # app.py: numpy vettorizzato una volta sola, invece che ad ogni richiesta web.
    R_TERRA = 6378137.0  # raggio sferico Web Mercator (EPSG:3857), stesso di Leaflet
    
    # !!! LIVELLI e COLORI_HEX definiti con il Plot di controllo
    LIVELLI = np.array(
        [0.2, 0.5, 1, 2, 3, 5, 7, 10, 15, 20, 25, 35, 45, 60, 75, 90, 120, 150, 180, 210]
        )
    
    COLORI_HEX = [
        "#ffffff", "#e0ebff", "#b5c9ff", "#8eb2ff", "#7f96ff",
        "#6370f7", "#009f1e", "#3cbc3d", "#b9f96e", "#fff914",
        "#fac81e", "#eb9628", "#fa3c3c", "#cd005a", "#b400b4",
        "#9600c8", "#a064dc", "#be8cc8", "#e1afc3", "#e1c8be",
        "#f0dce1",
    ]
    
    def _hex_to_rgb(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    
    
    COLORI_RGB = np.array([_hex_to_rgb(c) for c in COLORI_HEX], dtype=np.uint8)
    
    dst_crs = "EPSG:3857"
    transform_3857, width_3857, height_3857 = calculate_default_transform(
        crs_wkt, dst_crs, out.shape[1], out.shape[0],
        west, north - res_y * out.shape[0], west + res_x * out.shape[1], north,
        resolution=500,
    )
    banda_3857 = np.full((height_3857, width_3857), NODATA, dtype="float64")
    reproject(
        source=out.astype("float64"),
        destination=banda_3857,
        src_transform=transform,
        src_crs=crs_wkt,
        src_nodata=NODATA,
        dst_transform=transform_3857,
        dst_crs=dst_crs,
        dst_nodata=NODATA,
        resampling=Resampling.bilinear,
    )
    
    cols = np.arange(width_3857)
    rows = np.arange(height_3857)
    x_3857 = transform_3857.c + (cols + 0.5) * transform_3857.a
    y_3857 = transform_3857.f + (rows + 0.5) * transform_3857.e
    lon_3857 = np.degrees(x_3857 / R_TERRA)
    lat_3857 = np.degrees(2 * np.arctan(np.exp(y_3857 / R_TERRA)) - np.pi / 2)
    
    mancanti = (banda_3857 == NODATA)
    v = banda_3857 / 10.0
    idx = np.searchsorted(LIVELLI, v, side="right")
    idx = np.clip(idx, 0, len(COLORI_RGB) - 1)
    rgb = COLORI_RGB[idx]
    alpha = np.where(idx == 0, 0, 255).astype(np.uint8)
    alpha[mancanti] = 0
    rgba = np.dstack([rgb, alpha]).astype(np.uint8)
    
    nome_base = os.path.splitext(nome_file_png)[0]
    Image.fromarray(rgba, mode="RGBA").save(f"{cartella_file}/{nome_base}.png")
    
    with open(f"{cartella_file}/{nome_base}.json", "w") as f:
        json.dump({
            "bounds": [
                [float(lat_3857[0]), float(lon_3857[0])],
                [float(lat_3857[-1]), float(lon_3857[-1])],
            ],
        }, f)
    
print('Done\n')

# %%
"""
Lavorando mi sono accorto che tutto il regrid non serve a niente. Ma lo lascio
qui sotto comunque.
"""

# # %% Rigriglio in lat/lon regolare
# from scipy.interpolate import griddata

# dlon, dlat = 0.01, 0.01
# lons = np.arange(area[0], area[1] + dlon / 2, dlon)
# lats = np.arange(area[2], area[3] + dlat / 2, dlat)
# LON, LAT = np.meshgrid(lons, lats)

# def f_rigrigliatura(da, lat_dest, lon_dest):
#     lon2D, lat2D = da['lon'].values, da['lat'].values
#     punti_sorgente = np.column_stack([lon2D.ravel(), lat2D.ravel()])
#     output = np.empty((lat_dest.shape[0], lat_dest.shape[1]), dtype="float32")
#     print('Rigriglio...')
#     output = griddata(punti_sorgente, da.RR.values.ravel(), (lon_dest, lat_dest), method='linear')
    
#     return output

# dato_rigrigliato = f_rigrigliatura(da, LAT, LON)
# dato_rigrigliato = np.nan_to_num(dato_rigrigliato, nan=-999)
# dato_rigrigliato = (dato_rigrigliato * 10).astype(int)

# # %% Plot dato rigrigliato

# fig, ax = plt.subplots(figsize=(8, 10), subplot_kw={'projection': crs})

# ax.coastlines(resolution='10m', lw=0.75)
# ax.add_feature(cfeature.BORDERS, lw=0.75)
   
# plot_shaded = ax.contourf(
#     LON,
#     LAT,
#     dato_rigrigliato,
#     levels=livelli,
#     cmap=cmap,
#     norm=norm,
#     extend="both",
#     transform=ccrs.PlateCarree()
# )

# count_shaded = ax.contour(
#     LON,
#     LAT,
#     dato_rigrigliato,
#     levels=livelli,
#     colors='black',
#     linewidths=0.15,
#     transform=ccrs.PlateCarree()
# )

# ax.set_title(f"{da['RR'].long_name} [mm] interpolato", loc='left')
# ax.set_title(str(pd.to_datetime(da.time.values)), loc='right')

# cbar = plt.colorbar(
#     plot_shaded,
#     ticks=livelli,
#     orientation='vertical',
#     extend='both',
#     drawedges=True,
#     shrink=0.45,
#     pad=0.01,
#     fraction=0.1,
# )

# plt.show()
# plt.close()

