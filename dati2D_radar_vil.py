
import os
import json
import configparser
import rasterio

import numpy as np
import pandas as pd
from scipy.ndimage import binary_dilation
from pyproj import CRS
from datetime import datetime, timezone
from rasterio.warp import calculate_default_transform, reproject, Resampling
from PIL import Image

os.chdir('/run/media/daniele.carnevale/Daniele2TB/repo/MeteoBricchi')
# os.chdir('/media/daniele/Daniele2TB/repo/MeteoBricchi')
config = configparser.ConfigParser()
config.read('./config.ini')

cartella_destinazione = f"{config.get('DATI2D', 'cartella')}/radar_vil"

# %%
sovrascrivi = False

adesso_0_UTC = pd.to_datetime(datetime.now(timezone.utc)).tz_localize(None)

# lista_tempi = [adesso_0_UTC]
lista_tempi = pd.date_range('2026-06-28 00:00:00', adesso_0_UTC + pd.Timedelta(hours=1), freq='5min')

for adesso_0_UTC in lista_tempi:
    print(f"\n----------------\nSono le {datetime.now(timezone.utc).strftime('%H:%M:%S UTC del %Y-%m-%d')}")
    print(f'{cartella_destinazione=}')
    
    adesso_1_UTC = adesso_0_UTC - pd.Timedelta(hours=1)
    
    for t in pd.date_range(adesso_0_UTC - pd.Timedelta(hours=1), adesso_0_UTC):
        percorso = f"/mnt/ARC_STORICO/RADAR/ARCHIVIO_RADAR_VIL/{t.strftime(format='%Y/%m/%d')}/VIL{t.strftime(format='%Y%m%d%H%M')}.tif"

        if os.path.exists(percorso):
            with rasterio.open(percorso) as f:
                raster = f.read(1)
                
                raster[raster == -9999.0] = np.nan
                # raster[raster < 1 and raster != -1] = 0
            
                transform = f.transform
                crs_raster = f.crs
                altezza, larghezza = f.shape
                
                ### Prendo gli indici di ogni cella
                righe, colonne = np.meshgrid(np.arange(altezza), np.arange(larghezza), indexing='ij')
            
                ### Converto questi indici in coordinate
                lon, lat = rasterio.transform.xy(transform, righe, colonne, offset='center')
                lon, lat = np.reshape(lon, (altezza, larghezza)), np.reshape(lat, (altezza, larghezza))
                
            print(f'trovata {t}')
            break
    
    cartella_file = f"{cartella_destinazione}/{t.strftime(format='%Y/%m/%d')}"
    os.makedirs(cartella_file, exist_ok=True)
    nome_file_webp = f"radar_vil_{t.strftime(format='%Y-%m-%d_%H%M')}.webp"
    print(f'{nome_file_webp=}')

    if os.path.exists(f'{cartella_file}/{nome_file_webp}') and not sovrascrivi:
        print('Esiste già il file. Esco.')
        continue
    
    mask_valid = ~np.isnan(raster)
    mask_bordo = binary_dilation(mask_valid) & np.isnan(raster)
    raster[mask_bordo] = -1

    # np.save("raster.npy", raster)
    
    # %% Plot di controllo
    # import matplotlib.pyplot as plt
    # import matplotlib.colors as mcolors
    # import cartopy.crs as ccrs
    # import cartopy.feature as cfeature
    
    # livelli = [-1.5, -0.5, 1, 3, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75]
    # labels = livelli
    # colori = ['#ffffff', 'none', '#2c0c3e', '#3d40a4', '#436ce3', '#3d95fa', '#23bdea', '#15ddc3', '#32f197', '#6cfc63', '#a3fa3d', '#cdeb32', '#ecd035', '#fbad2e', '#fa801b', '#ec5107', '#d22c00', '#ac1000', '#7b0000']
    
    # cmap = mcolors.ListedColormap(colori[:-1])
    # cmap.set_over(colori[-1])
    # norm = mcolors.BoundaryNorm(livelli, cmap.N)
    
    # crs = ccrs.PlateCarree()
    
    # fig, ax = plt.subplots(figsize=(8, 10), subplot_kw={'projection': crs})
    
    # ax.coastlines(resolution='10m', lw=0.75)
    # ax.add_feature(cfeature.BORDERS, lw=0.75)
    # ax.set_extent((lon.min(), lon.max(), lat.min(), lat.max()), crs=ccrs.PlateCarree())

    # plot_shaded = ax.contourf(
    #     lon,
    #     lat,
    #     raster,
    #     levels=livelli,
    #     cmap=cmap,
    #     norm=norm,
    #     extend="max",
    #     transform=ccrs.PlateCarree()
    # )
    
    # ax.set_title("VIL [kg/m²]]", loc='left')
    # ax.set_title(str(t), loc='right')
    
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

    # %% Plot della colorbar
    
    # import matplotlib.pyplot as plt
    # import matplotlib.colors as mcolors
    # import matplotlib.patheffects as path_effects
    
    # livelli = [1, 3, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75]
    # labels = livelli
    # colori = ['#2c0c3e', '#3d40a4', '#436ce3', '#3d95fa', '#23bdea', '#15ddc3', '#32f197', '#6cfc63', '#a3fa3d', '#cdeb32', '#ecd035', '#fbad2e', '#fa801b', '#ec5107', '#d22c00', '#ac1000', '#7b0000']
    
    # cmap = mcolors.ListedColormap(colori[:-1])
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
    #     extend="max"
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
    #     1.06, 0.5, "kg/m²",
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
    #     "./static/icone/colorbar_radar_vil.png",
    #     dpi=600,
    #     transparent=True,
    #     bbox_inches="tight",
    #     pad_inches=0.1
    # )
    
    # plt.show()
    # plt.close()

    # %%
    # Questa va adattata
    crs_wkt = CRS.from_wkt(crs_raster.to_wkt())
    
    # !!! Uesto NODATA non ha valore perché nel plot è sempre ignorato
    NODATA = -999  # coerente col formato gia' usato in app.py / index.html
    
    dato = raster  # (y, x), NaN sui missing (già con bordo=-5)
    
    # west/north/res_x/res_y presi da transform (già spigoli, non centri:
    # nessun offset di mezzo pixel da applicare, a differenza di da["x"]/da["y"])
    west = transform.c
    north = transform.f
    res_x = transform.a
    res_y = -transform.e
    
    out = np.where(np.isnan(dato), NODATA, dato * 10).astype(int)
        
    ### CLAUDE
    ### Riproiezione EPSG:3857 + colormap, generati qui invece che a runtime in
    # app.py: numpy vettorizzato una volta sola, invece che ad ogni richiesta web.
    R_TERRA = 6378137.0  # raggio sferico Web Mercator (EPSG:3857), stesso di Leaflet
    
    # !!! LIVELLI e COLORI_HEX definiti con il Plot di controllo
    LIVELLI = np.array(
        [-1.5, -0.5, 1, 3, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75]
    )
    
    COLORI_HEX = ['#ffffff', 'none', '#2c0c3e', '#3d40a4', '#436ce3', '#3d95fa', '#23bdea', '#15ddc3', '#32f197', '#6cfc63', '#a3fa3d', '#cdeb32', '#ecd035', '#fbad2e', '#fa801b', '#ec5107', '#d22c00', '#ac1000', '#7b0000']
    
    def _hex_to_rgb(h):
        if h == "none":
            return (0, 0, 0)  # placeholder RGB, reso trasparente via ALPHA_LIVELLI
        h = h.lstrip("#")
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    
    COLORI_RGB = np.array([_hex_to_rgb(c) for c in COLORI_HEX], dtype=np.uint8)
    # Indice per indice, allineato 1:1 a COLORI_RGB (vedi idx piu' sotto):
    # 0 (bordo, banda [-1.5,-0.5)) resta opaco - e' il contorno bianco.
    ALPHA_LIVELLI = np.array([0 if c == "none" else 255 for c in COLORI_HEX], dtype=np.uint8)
    
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
    # -1: BoundaryNorm di matplotlib assegna il valore che cade in
    # [livelli[i], livelli[i+1]) al colore colori[i] (bin 0-indicizzato),
    # mentre searchsorted "right" da solo restituisce i+1 - senza il -1 ogni
    # valore prendeva il colore della banda successiva a quella giusta
    # (bordo -> 'none' invece che bianco, sotto-soglia -> colore vero
    # invece che trasparente).
    idx = np.searchsorted(LIVELLI, v, side="right") - 1
    idx = np.clip(idx, 0, len(COLORI_RGB) - 1)
    rgb = COLORI_RGB[idx]
    alpha = ALPHA_LIVELLI[idx]  # trasparenza legata al colore vero, non a una soglia scollegata
    alpha[mancanti] = 0
    rgba = np.dstack([rgb, alpha]).astype(np.uint8)
    
    nome_base = os.path.splitext(nome_file_webp)[0]
    Image.fromarray(rgba, mode="RGBA").save(f"{cartella_file}/{nome_base}.webp")
    
    with open(f"{cartella_file}/{nome_base}.json", "w") as f:
        json.dump({
            "bounds": [
                [float(lat_3857[0]), float(lon_3857[0])],
                [float(lat_3857[-1]), float(lon_3857[-1])],
            ],
        }, f)
    
print('Done\n')
