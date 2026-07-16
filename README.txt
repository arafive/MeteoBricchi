README.txt

:Author: daniele
:Email: daniele@skaftafell
:Date: 2026-05-08 08:53

########### TODO
--- Grafici 1D
    Risolvi problema IQR della temperatura.
    Aggiungi previsioni di pioggia.
    Comincia ad impostare che ogni previsione è fatta da feature di un modello specifico.
    Apri il plot a pop up con CTRL e il mouse sopra il pallino.
    In produzione, colora i pallini se superano certe soglie.

--- Grafici 2D
    Fulmini: adesso è a finestra di 5 min ogni 5 min. Meglio a finestra di 30 min?
    Aggiungi EPT (tempi strani di arrivo, forse non ha senso).
    Aggiungi IRENE.
    Aggiungi un controllo sulla velocità della Animazione.
    Gerarchia: Satellite sempre sotto e radar sempre sopra. Gli altri non importa.

--- Altro
    Logo meteobricchi.

--- Bachi
    In run_operativo.py di vento e temperatura, riguarda il config che può essere impostato in ecsyn o df_coordinate_estere
    Sulla meteo-dev devo per forza mettere meteopy a 3.12 perché VMI non funziona con la 3.9 in quanto ha zarr

###########

Avviare flask in background:
nohup flask run --host=0.0.0.0 --port=5009 > log/log_web.log 2>&1 &
nohup flask run --host=0.0.0.0 --port=5010 > log/log_web_casa.log 2>&1 &

ip di questo computer ARPAL: 10.24.50.225 (trovato con >>> hostname -I)
Link: http://10.24.50.225:5009

>>> Cosa ho fatto per far vedere il link anche con la VPN <<<
sudo systemctl status firewalld
sudo firewall-cmd --permanent --add-port=5009/tcp
sudo firewall-cmd --reload
sudo firewall-cmd --list-ports

Maggiori dettagli su questa chat: https://chatgpt.com/c/688f02a0-cebc-8326-8022-c757edab1687

######## Visualizzare il sito da telefono con il WiFi di casa
hostname -I
192.168.0.8 10.24.182.1 2a07:7e81:79d6:0:2d1e:662c:3aad:be37

Da telefono >>> http://192.168.0.8:5009
Da telefono >>> http://skaftafell.local:5009
