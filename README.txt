README.txt

:Author: daniele
:Email: daniele@skaftafell
:Date: 2026-05-08 08:53

########### parte generazione immagini

Avviare flask in background:
nohup flask run --host=0.0.0.0 --port=5009 > log_web.log 2>&1 &

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
