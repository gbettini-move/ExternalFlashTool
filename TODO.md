# TODO - ExternalFlashTool

## Features da implementare

- Gestire i pacchetti degli altri tipi di sensori. In apertura leggere il tipo di sensore collegato
- inserire grafica di aggiornamento

## Bug 

## Migliorie

- Implementare **lettura più veloce** con **AT+BUART = 460800**. Disponibile solo per release t.4.11 (non so sugli altri sensori).

    Segui il seguente ordine:
    1. reset device
    2. AT+TST
    3. AT+BUART = 460800
    4. chiudi seriale
    5. apri seriale nuova
    6. scarica
    7. chiudi seriale e resetta (ritorna il boudrate di default, ossia 115200)

  Secondo Marco devo implementarla senza usare la classe


## Idee e altro