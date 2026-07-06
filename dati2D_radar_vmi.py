
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
dataset = "italian-radar-dpc-vmi.zarr"

dataset_url = f"https://{username}:{access_key}@api.arcodatahub.com/S3/{dataset}"
ds_tot = xr.open_dataset(dataset_url, engine="zarr")

os.chdir('/run/media/daniele.carnevale/Daniele2TB/repo/MeteoBricchi')
# os.chdir('/media/daniele/Daniele2TB/repo/MeteoBricchi')
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
        
# %%
area = (4.5, 20.4, 35.0, 47.8) # italia
sovrascrivi = True

adesso_0_UTC = pd.to_datetime(datetime.now(timezone.utc)).tz_localize(None)

lista_tempi = [adesso_0_UTC]
# lista_tempi = pd.date_range('2026-07-03 16:00:00', adesso_0_UTC + pd.Timedelta(hours=1), freq='5min')

for adesso_0_UTC in lista_tempi:
    print(f"\n----------------\nSono le {datetime.now(timezone.utc).strftime('%H:%M:%S UTC del %Y-%m-%d')}")
    print(f'{cartella_destinazione=}')
    
    adesso_1_UTC = adesso_0_UTC - pd.Timedelta(hours=1)
    
    ds = ds_tot.sel(time=slice(adesso_1_UTC, adesso_0_UTC))
    
    tempo_buono = f_prendi_ultimo_istante_buono(ds)
    try:
        cartella_file = f"{cartella_destinazione}/{tempo_buono.strftime(format='%Y/%m/%d')}"
    except AttributeError:
        break
        
    os.makedirs(cartella_file, exist_ok=True)
    nome_file_png = f"radar_vmi_{tempo_buono.strftime(format='%Y-%m-%d_%H%M')}.png"
    print(f'{nome_file_png=}')
    
    if os.path.exists(f'{cartella_file}/{nome_file_png}') and not sovrascrivi:
        print('Esiste già il file. Esco.')
        continue
    
    da = ds.sel(time=tempo_buono)
    
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
    # import colorsys
    # import matplotlib.pyplot as plt
    # import matplotlib.colors as mcolors
    # import cartopy.crs as ccrs
    # import cartopy.feature as cfeature
    
    
    # def generate_256_colorbar(hex_key_colors):
    #     """Genera i 256 campioni equispaziati"""
    #     rgb_list = [mcolors.to_rgb(c) for c in hex_key_colors]
    #     cmap = mcolors.LinearSegmentedColormap.from_list("bright_radar_from_0", rgb_list, N=256)
    #     return [mcolors.to_hex(cmap(i / 255.0)).upper() for i in range(256)]
    
    
    # def generate_256_colors(hex_list):
    #     # Converte i colori HEX in RGB normalizzati (0-1)
    #     rgb_list = [mcolors.to_rgb(c) for c in hex_list]
    #     # Crea una colormap lineare
    #     cmap = mcolors.LinearSegmentedColormap.from_list("custom_colorbar", rgb_list, N=256)
    #     # Genera i 256 campioni
    #     samples = [cmap(i / 255.0) for i in range(256)]
    #     # Riconverte in formato HEX (#RRGGBB)
    #     return [mcolors.to_hex(rgb) for rgb in samples]
    
    
    # def boost_brightness_and_saturation(hex_list, sat_boost=1.1, val_boost=1.1):
    #     """Mantiene i colori vividi e saturi come la colorbar originale"""
    #     boosted_hex = []
    #     for hex_color in hex_list:
    #         rgb = mcolors.to_rgb(hex_color)
    #         h, s, v = colorsys.rgb_to_hsv(*rgb)
            
    #         s = min(s * sat_boost, 1.0) if s > 0 else s
    #         v = min(v * val_boost, 1.0) if v > 0 else v
            
    #         if s > 0.2: 
    #             s = max(s, 0.9)
    #             v = max(v, 0.9)
                
    #         new_rgb = colorsys.hsv_to_rgb(h, s, v)
    #         boosted_hex.append(mcolors.to_hex(new_rgb).upper())
    #     return boosted_hex
    
    # palette_da_usare = 1 # 1, 2, 3
    
    # if palette_da_usare == 1:
    #     ## Palette 1 e 2 di ESSL RADAR fatta con Gemini (https://share.gemini.google/pjeoDXGCGjaP)
    #     colors_key = [
    #         "#2A2A2A",  # Fondo scala inferiore (-10 / Grigio scuro)
    #         "#555555",  # Transizione verso lo 0 (Grigio medio)
    #         "#3C50B4",  # Intorno a 10 (Blu/Viola)
    #         "#2278C8",  # Intorno a 20 (Azzurro/Blu)
    #         "#28B446",  # Intorno a 30 (Verde brillante)
    #         "#DCD000",  # Intorno a 40 (Giallo)
    #         "#FF7800",  # Transizione 40-50 (Arancione)
    #         "#E60000",  # Intorno a 50 (Rosso)
    #         "#7D1432",  # Transizione 50-60 (Scuro/Bordeaux)
    #         "#C832D2",  # Intorno a 60 (Magenta/Viola)
    #         "#FFFFFF",  # Transizione 60-70 (Bianco)
    #         "#00D2D2",  # Intorno a 70 (Ciano)
    #         "#006428"   # In cima vicino a 80 (Verde scuro)
    #     ]
        
    #     colori = generate_256_colors(colors_key)
    #     livelli = np.linspace(0, 80, len(colori))#.astype(int)
        
    #     labels = [""] * len(colori)
    #     values = list(range(0, 81, 10))
    #     # posizioni equispaziate
    #     positions = [round(i * (len(colori) - 1) / (len(values) - 1)) for i in range(len(values))]
    #     for p, v in zip(positions, values):
    #         labels[p] = v
    
    # elif palette_da_usare == 2:
    #     colors_from_0_key = [
    #         "#101040",  # Sotto lo 0 / Inizio della transizione blu scura
    #         "#4D31D7",  # 10 (Blu elettrico / Viola intenso)
    #         "#0088FF",  # 20 (Azzurro saturo)
    #         "#00CC36",  # 30 (Verde neon)
    #         "#FFFF00",  # 40 (Giallo intenso)
    #         "#FF7800",  # Transizione (Arancione)
    #         "#FF0000",  # 50 (Rosso radar)
    #         "#A00040",  # Transizione (Bordeaux)
    #         "#FF00FF",  # 60 (Magenta / Fucsia)
    #         "#FFFFFF",  # Transizione (Bianco)
    #         "#00FFFF",  # 70 (Ciano elettrico)
    #         "#008030"   # 80 (Verde scuro finale)
    #     ]
        
    #     # Applica la massima saturazione ai punti chiave partendo da 0
    #     brightened_keys = boost_brightness_and_saturation(colors_from_0_key)
        
    #     # Genera la lista finale di 256 colori luminosissimi
    #     colori = generate_256_colorbar(brightened_keys)
    #     livelli = np.linspace(0, 80, len(colori))#.astype(int)
        
    #     labels = [""] * len(colori)
    #     values = list(range(0, 81, 10))
    #     # posizioni equispaziate
    #     positions = [round(i * (len(colori) - 1) / (len(values) - 1)) for i in range(len(values))]
    #     for p, v in zip(positions, values):
    #         labels[p] = v
    
    # elif palette_da_usare == 3:
    #     dict_livelli_colori = {
    #         0: '#acacac', # grigio
    #         ####
    #         5: '#0024FF',
    #         10: '#0092FF',
    #         15: '#00C9FF',
    #         20: '#00FFFF',
    #         ####
    #         25: '#FFE600',
    #         30: '#FFA900',
    #         35: '#FF8B00',
    #         40: '#FF6C00',
    #         ####
    #         45: '#FF0000',
    #         50: '#E80476',
    #         55: '#DD06B1',
    #         60: '#D107EC',
    #         ####
    #         65: '#05d3d6',
    #         70: '#038687',
    #         }
        
    #     livelli = list(dict_livelli_colori.keys())
    #     labels = livelli
    #     colori = list(dict_livelli_colori.values())
    
    # ##################
    # ##################
    # ##################

    # cmap = mcolors.ListedColormap(colori[:-1])
    # cmap.set_over(colori[-1])
    # norm = mcolors.BoundaryNorm(livelli, cmap.N)
    
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
    # # ax.set_extent(area, crs=ccrs.PlateCarree())
    # ax.set_extent((7.45, 10.1, 43.75, 44.7), crs=ccrs.PlateCarree())
       
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
    
    # # count_shaded = ax.contour(
    # #     da.lon,
    # #     da.lat,
    # #     da['vmi'],
    # #     levels=livelli,
    # #     colors='black',
    # #     linewidths=0.15,
    # #     transform=ccrs.PlateCarree()
    # # )
    
    # ax.set_title(f"{da['vmi'].long_name} [dBZ]", loc='left')
    # ax.set_title(str(pd.to_datetime(da.time.values)), loc='right')
    
    # # cbar = plt.colorbar(
    # #     plot_shaded,
    # #     ticks=livelli,
    # #     orientation='vertical',
    # #     extend='max',
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
    
    # palette_da_usare = 2 # 1, 2, 3
    
    # if palette_da_usare == 1:
    #     ## Palette 1 e 2 di ESSL RADAR fatta con Gemini (https://share.gemini.google/pjeoDXGCGjaP)
    #     colors_key = [
    #         "#2A2A2A",  # Fondo scala inferiore (-10 / Grigio scuro)
    #         "#555555",  # Transizione verso lo 0 (Grigio medio)
    #         "#3C50B4",  # Intorno a 10 (Blu/Viola)
    #         "#2278C8",  # Intorno a 20 (Azzurro/Blu)
    #         "#28B446",  # Intorno a 30 (Verde brillante)
    #         "#DCD000",  # Intorno a 40 (Giallo)
    #         "#FF7800",  # Transizione 40-50 (Arancione)
    #         "#E60000",  # Intorno a 50 (Rosso)
    #         "#7D1432",  # Transizione 50-60 (Scuro/Bordeaux)
    #         "#C832D2",  # Intorno a 60 (Magenta/Viola)
    #         "#FFFFFF",  # Transizione 60-70 (Bianco)
    #         "#00D2D2",  # Intorno a 70 (Ciano)
    #         "#006428"   # In cima vicino a 80 (Verde scuro)
    #     ]
        
    #     colori = generate_256_colors(colors_key)
    #     livelli = np.linspace(0, 80, len(colori))#.astype(int)
        
    #     labels = [""] * len(colori)
    #     values = list(range(0, 81, 10))
    #     # posizioni equispaziate
    #     positions = [round(i * (len(colori) - 1) / (len(values) - 1)) for i in range(len(values))]
    #     for p, v in zip(positions, values):
    #         labels[p] = v
    
    # elif palette_da_usare == 2:
    #     colors_from_0_key = [
    #         "#101040",  # Sotto lo 0 / Inizio della transizione blu scura
    #         "#4D31D7",  # 10 (Blu elettrico / Viola intenso)
    #         "#0088FF",  # 20 (Azzurro saturo)
    #         "#00CC36",  # 30 (Verde neon)
    #         "#FFFF00",  # 40 (Giallo intenso)
    #         "#FF7800",  # Transizione (Arancione)
    #         "#FF0000",  # 50 (Rosso radar)
    #         "#A00040",  # Transizione (Bordeaux)
    #         "#FF00FF",  # 60 (Magenta / Fucsia)
    #         "#FFFFFF",  # Transizione (Bianco)
    #         "#00FFFF",  # 70 (Ciano elettrico)
    #         "#008030"   # 80 (Verde scuro finale)
    #     ]
        
    #     # Applica la massima saturazione ai punti chiave partendo da 0
    #     brightened_keys = boost_brightness_and_saturation(colors_from_0_key)
        
    #     # Genera la lista finale di 256 colori luminosissimi
    #     colori = generate_256_colorbar(brightened_keys)
    #     livelli = np.linspace(0, 80, len(colori))#.astype(int)
        
    #     labels = [""] * len(colori)
    #     values = list(range(0, 81, 10))
    #     # posizioni equispaziate
    #     positions = [round(i * (len(colori) - 1) / (len(values) - 1)) for i in range(len(values))]
    #     for p, v in zip(positions, values):
    #         labels[p] = v
    
    # elif palette_da_usare == 3:
    #     dict_livelli_colori = {
    #         0: '#acacac', # grigio
    #         ####
    #         5: '#0024FF',
    #         10: '#0092FF',
    #         15: '#00C9FF',
    #         20: '#00FFFF',
    #         ####
    #         25: '#FFE600',
    #         30: '#FFA900',
    #         35: '#FF8B00',
    #         40: '#FF6C00',
    #         ####
    #         45: '#FF0000',
    #         50: '#E80476',
    #         55: '#DD06B1',
    #         60: '#D107EC',
    #         ####
    #         65: '#05d3d6',
    #         70: '#038687',
    #         }
        
    #     livelli = list(dict_livelli_colori.keys())
    #     labels = livelli
    #     colori = list(dict_livelli_colori.values())
    
    # cmap = mcolors.ListedColormap(colori[:-1])
    # cmap.set_over(colori[-1])
    # norm = mcolors.BoundaryNorm(livelli, cmap.N)
    
    # # ###################
    
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
    
    crs_wkt = CRS.from_wkt(da.crs.attrs["crs_wkt"]) # Data a ChatGPT
    
    # !!! Uesto NODATA non ha valore perché nel plot è sempre ignorato
    NODATA = -999  # coerente col formato gia' usato in app.py / index.html
    
    x = da["x"].values  # crescente, metri
    y = da["y"].values  # decrescente, metri (nord -> sud)
    dato = da.vmi.values  # (y, x), NaN sui missing
    
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
    
    LIVELLI = np.array([ 0,  0,  0,  0,  1,  1,  1,  2,  2,  2,  3,  3,  3,  4,  4,  4,  5,
        5,  5,  5,  6,  6,  6,  7,  7,  7,  8,  8,  8,  9,  9,  9, 10, 10,
       10, 10, 11, 11, 11, 12, 12, 12, 13, 13, 13, 14, 14, 14, 15, 15, 15,
       16, 16, 16, 16, 17, 17, 17, 18, 18, 18, 19, 19, 19, 20, 20, 20, 21,
       21, 21, 21, 22, 22, 22, 23, 23, 23, 24, 24, 24, 25, 25, 25, 26, 26,
       26, 26, 27, 27, 27, 28, 28, 28, 29, 29, 29, 30, 30, 30, 31, 31, 31,
       32, 32, 32, 32, 33, 33, 33, 34, 34, 34, 35, 35, 35, 36, 36, 36, 37,
       37, 37, 37, 38, 38, 38, 39, 39, 39, 40, 40, 40, 41, 41, 41, 42, 42,
       42, 42, 43, 43, 43, 44, 44, 44, 45, 45, 45, 46, 46, 46, 47, 47, 47,
       48, 48, 48, 48, 49, 49, 49, 50, 50, 50, 51, 51, 51, 52, 52, 52, 53,
       53, 53, 53, 54, 54, 54, 55, 55, 55, 56, 56, 56, 57, 57, 57, 58, 58,
       58, 58, 59, 59, 59, 60, 60, 60, 61, 61, 61, 62, 62, 62, 63, 63, 63,
       64, 64, 64, 64, 65, 65, 65, 66, 66, 66, 67, 67, 67, 68, 68, 68, 69,
       69, 69, 69, 70, 70, 70, 71, 71, 71, 72, 72, 72, 73, 73, 73, 74, 74,
       74, 74, 75, 75, 75, 76, 76, 76, 77, 77, 77, 78, 78, 78, 79, 79, 79,
       80])

    COLORI_HEX = ['#2a2a2a',
    '#2c2c2c',
    '#2e2e2e',
    '#303030',
    '#323232',
    '#343434',
    '#363636',
    '#383838',
    '#3a3a3a',
    '#3c3c3c',
    '#3e3e3e',
    '#404040',
    '#424242',
    '#444444',
    '#464646',
    '#484848',
    '#4a4a4a',
    '#4c4c4c',
    '#4e4e4e',
    '#505050',
    '#525252',
    '#545454',
    '#545558',
    '#53555d',
    '#525461',
    '#515466',
    '#4f546a',
    '#4e546f',
    '#4d5373',
    '#4c5378',
    '#4b537c',
    '#4a5381',
    '#485285',
    '#47528a',
    '#46528e',
    '#455292',
    '#445297',
    '#42519b',
    '#4151a0',
    '#4051a4',
    '#3f51a9',
    '#3e50ad',
    '#3d50b2',
    '#3b51b4',
    '#3a53b5',
    '#3955b6',
    '#3857b7',
    '#3658b8',
    '#355ab9',
    '#345cba',
    '#335ebb',
    '#3260bc',
    '#3062bd',
    '#2f64be',
    '#2e66bf',
    '#2d68c0',
    '#2b69c1',
    '#2a6bc2',
    '#296dc3',
    '#286fc4',
    '#2771c4',
    '#2573c5',
    '#2475c6',
    '#2377c7',
    '#2279c6',
    '#227cc0',
    '#237eba',
    '#2381b4',
    '#2384ae',
    '#2387a8',
    '#248aa2',
    '#248c9c',
    '#248f96',
    '#25928f',
    '#259589',
    '#259883',
    '#259b7d',
    '#269d77',
    '#26a071',
    '#26a36b',
    '#27a665',
    '#27a95e',
    '#27ac58',
    '#27ae52',
    '#28b14c',
    '#28b446',
    '#30b543',
    '#39b73f',
    '#41b83c',
    '#4ab939',
    '#52bb36',
    '#5bbc32',
    '#63bd2f',
    '#6cbf2c',
    '#74c028',
    '#7dc125',
    '#85c222',
    '#8ec41e',
    '#96c51b',
    '#9fc618',
    '#a7c815',
    '#b0c911',
    '#b8ca0e',
    '#c0cc0b',
    '#c9cd07',
    '#d1ce04',
    '#dad001',
    '#ddcd00',
    '#dfc900',
    '#e1c500',
    '#e2c000',
    '#e4bc00',
    '#e5b800',
    '#e7b400',
    '#e9b000',
    '#eaac00',
    '#eca800',
    '#eea300',
    '#ef9f00',
    '#f19b00',
    '#f39700',
    '#f49300',
    '#f68f00',
    '#f88b00',
    '#f98600',
    '#fb8200',
    '#fd7e00',
    '#fe7a00',
    '#fe7500',
    '#fd7000',
    '#fc6a00',
    '#fb6400',
    '#fa5f00',
    '#f95900',
    '#f75300',
    '#f64e00',
    '#f54800',
    '#f44200',
    '#f33d00',
    '#f13700',
    '#f03100',
    '#ef2c00',
    '#ee2600',
    '#ed2000',
    '#ec1b00',
    '#ea1500',
    '#e91000',
    '#e80a00',
    '#e70400',
    '#e50001',
    '#e00103',
    '#db0205',
    '#d60308',
    '#d1040a',
    '#cc050c',
    '#c7060f',
    '#c20711',
    '#bd0813',
    '#b80916',
    '#b30a18',
    '#ae0b1a',
    '#a90c1d',
    '#a50c1f',
    '#a00d22',
    '#9b0e24',
    '#960f26',
    '#911029',
    '#8c112b',
    '#87122d',
    '#821330',
    '#7d1432',
    '#81153a',
    '#841741',
    '#881849',
    '#8b1a50',
    '#8f1b58',
    '#921c5f',
    '#961e67',
    '#991f6e',
    '#9d2176',
    '#a0227d',
    '#a42485',
    '#a7258c',
    '#ab2694',
    '#ae289b',
    '#b229a3',
    '#b52baa',
    '#b92cb2',
    '#bd2dba',
    '#c02fc1',
    '#c430c9',
    '#c732d0',
    '#ca39d4',
    '#cd43d6',
    '#cf4dd8',
    '#d256da',
    '#d460dc',
    '#d769de',
    '#d973e0',
    '#dc7de2',
    '#df86e5',
    '#e190e7',
    '#e49ae9',
    '#e6a3eb',
    '#e9aded',
    '#ecb7ef',
    '#eec0f1',
    '#f1caf3',
    '#f3d4f5',
    '#f6ddf8',
    '#f9e7fa',
    '#fbf1fc',
    '#fefafe',
    '#f9fefe',
    '#edfcfc',
    '#e1fafa',
    '#d5f8f8',
    '#c9f5f5',
    '#bdf3f3',
    '#b1f1f1',
    '#a5efef',
    '#99eded',
    '#8debeb',
    '#81e9e9',
    '#75e7e7',
    '#69e5e5',
    '#5de2e2',
    '#51e0e0',
    '#45dede',
    '#39dcdc',
    '#2ddada',
    '#21d8d8',
    '#15d6d6',
    '#09d4d4',
    '#00d1d0',
    '#00ccc8',
    '#00c6c0',
    '#00c1b8',
    '#00bcb0',
    '#00b7a8',
    '#00b2a0',
    '#00ac98',
    '#00a790',
    '#00a288',
    '#009d80',
    '#009878',
    '#009370',
    '#008d68',
    '#008860',
    '#008358',
    '#007e50',
    '#007948',
    '#007440',
    '#006e38',
    '#006930',
    '#006428']
    
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
