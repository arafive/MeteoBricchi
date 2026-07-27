
    LENOVO ARPAL <------------- METEO-DEV
        |   ^  ^                  |  
        |   |  | _________________/
        |   |  |/
        |   |  | 
        |   |  |\________________
        |   |  |                  \
        v   |  v                  |
    DANIELE 2TB <------------- METEO-PROD



METEO-DEV -> LENOVO ARPAL : sync_meteodev2arpal.sh
METEO-PROD -> LENOVO ARPAL : sync_meteoprod2arpal.sh

METEO-DEV -> DANIELE 2TB : sync_meteodev2daniele.sh
METEO-PROD -> DANIELE 2TB : sync_meteoprod2daniele.sh

LENOVO ARPAL -> DANIELE 2TB : sync_lenovo2daniele.sh
DANIELE 2TB -> LENOVO ARPAL: sync_daniele2lenovo.sh

