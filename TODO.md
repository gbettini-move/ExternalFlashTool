# TODO - ExternalFlashTool

## Features da implementare

- gestire i pacchetti degli altri tipi di sensori. In apertura leggere il tipo di sensore collegato
- inserire grafica di aggiornamento: NB è verosimile che tutti i sensori avranno riempito la memoria! Altrimenti inserisci la barra di aggiornamento solo per la generazione del CSV. -> perlomeno dare un feedback visivo all'utente che il programma non si è piantato. Aggiorna la pagina letta ma sempre sulla stessa riga del terminale.
- struttura try, finally per assicurarsi di chiudere la comunicazione
- inserire controllo sulla pagina massima: 32768. NB: sembrerebbe che le ultime pagine sono per la diagnostica (ad esempio la 31427)

## Bug

- capire il problema su firmware

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

- inserire json file di configurazione del tool: attivazione modalità debug con print, attivazione decodifica ...
