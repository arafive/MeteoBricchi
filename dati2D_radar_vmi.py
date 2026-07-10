
import os
import json
import colorsys
import configparser

import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.patheffects as path_effects
import cartopy.crs as ccrs
import cartopy.feature as cfeature

from pyproj import CRS
from scipy.ndimage import binary_dilation
from datetime import datetime, timezone
from rasterio.transform import from_origin
from rasterio.warp import calculate_default_transform, reproject, Resampling
from PIL import Image

username = "Daniele_Carnevale"
access_key = "15fcff78d4194bc4beacda6173861e6d"
dataset = "italian-radar-dpc-vmi.zarr"

dataset_url = f"https://{username}:{access_key}@api.arcodatahub.com/S3/{dataset}"
ds_tot = xr.open_dataset(dataset_url, engine="zarr")

# os.chdir('/run/media/daniele.carnevale/Daniele2TB/repo/MeteoBricchi')
os.chdir('/media/daniele/Daniele2TB/repo/MeteoBricchi')
config = configparser.ConfigParser()
config.read('./config.ini')

cartella_destinazione = f"{config.get('DATI2D', 'cartella')}/radar_vmi"


def f_prendi_ultimo_istante_buono(ds):
    # Trovo il primo istante di tempo con dei dati
    for i in range(ds.time.shape[0] - 1, -1, -1):
        a = ds.isel(time=i).vmi.values
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
lista_tempi = pd.date_range('2026-06-28 00:00:00', adesso_0_UTC + pd.Timedelta(hours=1), freq='5min')

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
    nome_file_webp = f"radar_vmi_{tempo_buono.strftime(format='%Y-%m-%d_%H%M')}.webp"
    print(f'{nome_file_webp=}')
    
    if os.path.exists(f'{cartella_file}/{nome_file_webp}') and not sovrascrivi:
        print('Esiste già il file. Esco.')
        continue
    
    da = ds.sel(time=tempo_buono)
    
    crs_wkt = CRS.from_wkt(da.crs.attrs["crs_wkt"]) # Data a ChatGPT

    mask_valid = ~np.isnan(da.vmi.values)
    mask_bordo = binary_dilation(mask_valid) & np.isnan(da.vmi.values)
    da.vmi.values[mask_bordo] = -1
    da = da.vmi.where(da != -9998, 0)

    # # Controllo dei valori minimi. Voglio capire se ci sono dBZ negativi
    # a = da.vmi.values
    # a[a == -9998] = 0
    # print(pd.Series(a.ravel()).describe())
    # if pd.Series(a.ravel()).describe()['min'] < 0:
    #     stop
    # continue
    # # Ho verificato che non ci sono valori negativi.
    #############
    
    # %% Plot di controllo
    def generate_256_colorbar(hex_key_colors):
        """Genera i 256 campioni equispaziati"""
        rgb_list = [mcolors.to_rgb(c) for c in hex_key_colors]
        cmap = mcolors.LinearSegmentedColormap.from_list("bright_radar_from_0", rgb_list, N=256)
        return [mcolors.to_hex(cmap(i / 255.0)).upper() for i in range(256)]
    
    
    def generate_256_colors(hex_list):
        # Converte i colori HEX in RGB normalizzati (0-1)
        rgb_list = [mcolors.to_rgb(c) for c in hex_list]
        # Crea una colormap lineare
        cmap = mcolors.LinearSegmentedColormap.from_list("custom_colorbar", rgb_list, N=256)
        # Genera i 256 campioni
        samples = [cmap(i / 255.0) for i in range(256)]
        # Riconverte in formato HEX (#RRGGBB)
        return [mcolors.to_hex(rgb) for rgb in samples]
    
    
    def boost_brightness_and_saturation(hex_list, sat_boost=1.1, val_boost=1.1):
        """Mantiene i colori vividi e saturi come la colorbar originale"""
        boosted_hex = []
        for hex_color in hex_list:
            rgb = mcolors.to_rgb(hex_color)
            h, s, v = colorsys.rgb_to_hsv(*rgb)
            
            s = min(s * sat_boost, 1.0) if s > 0 else s
            v = min(v * val_boost, 1.0) if v > 0 else v
            
            if s > 0.2: 
                s = max(s, 0.9)
                v = max(v, 0.9)
                
            new_rgb = colorsys.hsv_to_rgb(h, s, v)
            boosted_hex.append(mcolors.to_hex(new_rgb).upper())
        return boosted_hex
    
    colori = ["#2A2A2A", "#555555", "#3C50B4", "#2278C8", "#28B446", "#DCD000", "#FF7800", "#E60000", "#7D1432", "#C832D2", "#FFFFFF", "#00D2D2", "#006428"]
    colori = generate_256_colors(colori)
    livelli = np.linspace(0, 80, len(colori))#.astype(int)
    
    # ### Per creare i bordi
    # colori = ['#ffffff', 'none'] + colori
    # livelli = [-1.5, -0.5] + list(livelli)
    
    # labels = [""] * len(colori)
    # values = list(range(0, 81, 10))
    # # posizioni equispaziate
    # positions = [round(i * (len(colori) - 1) / (len(values) - 1)) for i in range(len(values))]
    # for p, v in zip(positions, values):
    #     labels[p] = v
    
    # ##################

    # cmap = mcolors.ListedColormap(colori[:-1])
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
    
    # ax.coastlines(resolution='50m', lw=0.75)
    # ax.add_feature(cfeature.NaturalEarthFeature(
    #     'cultural',
    #     'admin_0_boundary_lines_land',
    #     '50m',
    #     facecolor='none'),
    # edgecolor='black',
    # lw=0.75
    # )
    # ax.set_extent(area, crs=ccrs.PlateCarree())
       
    # plot_shaded = ax.contourf(
    #     da.lon,
    #     da.lat,
    #     da['vmi'],
    #     levels=livelli,
    #     cmap=cmap,
    #     norm=norm,
    #     extend="max",
    #     transform=ccrs.PlateCarree()
    # )
    
    # ax.set_title(f"{da['vmi'].long_name} [dBZ]", loc='left')
    # ax.set_title(str(pd.to_datetime(da.time.values)), loc='right')
    
    # # cbar = plt.colorbar(
    # #     plot_shaded,
    # #     # ticks=livelli,
    # #     orientation='vertical',
    # #     extend='max',
    # #     # drawedges=True,
    # #     shrink=0.45,
    # #     pad=0.01,
    # #     fraction=0.1,
    # # )
    
    # plt.show()
    # plt.close()

    # %% Plot della colorbar

    # colori = [
    #     "#2A2A2A",  # Fondo scala inferiore (-10 / Grigio scuro)
    #     "#555555",  # Transizione verso lo 0 (Grigio medio)
    #     "#3C50B4",  # Intorno a 10 (Blu/Viola)
    #     "#2278C8",  # Intorno a 20 (Azzurro/Blu)
    #     "#28B446",  # Intorno a 30 (Verde brillante)
    #     "#DCD000",  # Intorno a 40 (Giallo)
    #     "#FF7800",  # Transizione 40-50 (Arancione)
    #     "#E60000",  # Intorno a 50 (Rosso)
    #     "#7D1432",  # Transizione 50-60 (Scuro/Bordeaux)
    #     "#C832D2",  # Intorno a 60 (Magenta/Viola)
    #     "#FFFFFF",  # Transizione 60-70 (Bianco)
    #     "#00D2D2",  # Intorno a 70 (Ciano)
    #     "#006428"   # In cima vicino a 80 (Verde scuro)
    # ]
    
    # # Applica la massima saturazione ai punti chiave partendo da 0
    # brightened_keys = boost_brightness_and_saturation(colori)
    
    # # Genera la lista finale di 256 colori luminosissimi
    # colori = generate_256_colorbar(brightened_keys)
    # livelli = np.linspace(0, 80, len(colori))#.astype(int)
    
    # labels = [""] * len(colori)
    # values = list(range(0, 81, 10))
    # # posizioni equispaziate
    # positions = [round(i * (len(colori) - 1) / (len(values) - 1)) for i in range(len(values))]
    # for p, v in zip(positions, values):
    #     labels[p] = v

    # ###################

    # cmap = mcolors.ListedColormap(colori[:-1])
    # cmap.set_over(colori[-1])
    # norm = mcolors.BoundaryNorm(livelli, cmap.N)
    
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
    #     1.06, 0.5, "dBZ",
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
    #     "./static/icone/colorbar_radar_vmi.png",
    #     dpi=600,
    #     transparent=True,
    #     bbox_inches="tight",
    #     pad_inches=0.1
    # )
    
    # plt.show()
    # plt.close()
    
    # %%
    
    # !!! Uesto NODATA non ha valore perché nel plot è sempre ignorato
    NODATA = -999  # coerente col formato gia' usato in app.py / index.html
    
    x = da["x"].values  # crescente, metri
    y = da["y"].values  # decrescente, metri (nord -> sud)
    dato = da.vmi.values  # (y, x), NaN sui missing
    dato[dato == 0] = np.nan
    
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
    #     f'{cartella_file}/{nome_file_webp}', "w", # TODO modifica nome file in tif
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
    
    LIVELLI = np.linspace(0, 80, len(colori)).astype(int)

    colori = ["#2A2A2A", "#555555", "#3C50B4", "#2278C8", "#28B446", "#DCD000", "#FF7800", "#E60000", "#7D1432", "#C832D2", "#FFFFFF", "#00D2D2", "#006428"]
    COLORI_HEX = generate_256_colors(colori)
    
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
    # unico caso in cui v puo' essere negativo: la cella sentinella -1 del
    # bordo, "sporcata" un po' dal resampling bilineare vicino al confine
    bordo = (~mancanti) & (v < 0)

    idx = np.searchsorted(LIVELLI, v, side="right") - 1
    idx = np.clip(idx, 0, len(COLORI_RGB) - 1)
    rgb = COLORI_RGB[idx]
    alpha = np.where(idx == 0, 0, 255).astype(np.uint8)

    rgb[bordo] = (255, 255, 255)  # contorno bianco, come nel plot di controllo
    alpha[bordo] = 255
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
