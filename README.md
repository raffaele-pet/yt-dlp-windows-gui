# yt-dlp Windows GUI

Interfaccia grafica non ufficiale per [yt-dlp](https://github.com/yt-dlp/yt-dlp), pensata per scaricare video, audio e playlist su Windows senza utilizzare manualmente il terminale.

## Funzionalità

- download video in MP4;
- download alla massima qualità disponibile;
- rilevamento automatico delle risoluzioni disponibili e scelta della qualità video;
- estrazione audio in MP3 o M4A;
- supporto alle playlist;
- scelta della cartella di destinazione;
- barra di avanzamento e annullamento del download;
- aggiornamento di yt-dlp direttamente dall'interfaccia;
- verifica del file realmente creato;
- gestione dei nomi con caratteri accentati;
- tema scuro ispirato ai colori di yt-dlp.

## Requisiti

- Windows 10 o Windows 11;
- connessione Internet;
- Python 3.11 o successivo già installato; se manca, l'installer propone Python 3.13;
- [WinGet](https://learn.microsoft.com/windows/package-manager/winget/), normalmente incluso nelle versioni moderne di Windows tramite **App Installer**.

Gli altri componenti possono essere installati automaticamente:

- yt-dlp, isolato nella cartella locale `.venv`;
- FFmpeg;
- Deno.

## Installazione

1. Scarica la repository come file ZIP da GitHub.
2. Estrai l'intera cartella.
3. Fai doppio clic su `INSTALL.bat`.
4. Segui l'avanzamento mostrato nel terminale.

L'installer riutilizza qualsiasi Python di sistema compatibile senza installarne o aggiornarne un secondo. Crea quindi `.venv` dentro il progetto e vi installa il pacchetto stabile ufficiale di yt-dlp; a ogni nuova esecuzione controlla e applica gli aggiornamenti soltanto in questo ambiente isolato. FFmpeg e Deno restano gestiti tramite WinGet. Al termine verifica le versioni e crea un collegamento **YT-DLP** sul Desktop con l'[icona richiesta](https://img.icons8.com/?size=100&id=cLcs1xqp7qTl&format=png&color=000000).

Per eseguire soltanto un controllo, senza installare o modificare nulla:

```bat
INSTALL.bat --check
```

## Avvio

Fai doppio clic su `RUN.vbs` per aprire l'interfaccia senza mostrare il terminale.

Se l'applicazione non parte, utilizza `RUN_DEBUG.cmd` per visualizzare eventuali errori.

Il pulsante **Aggiorna yt-dlp** aggiorna esclusivamente la copia contenuta nella `.venv`, mostra i dettagli dell'operazione nella finestra e non modifica Python o pacchetti globali.

Incolla il link con **Ctrl+V**: l'app legge le risoluzioni in background, senza scaricare il video. Dopo la lettura, scegli **Risoluzione** e premi **Scarica**. Il menu elenca le qualità H.264 compatibili con il formato selezionato, mantenendo la compatibilità video del programma; **Massima disponibile** conserva il comportamento automatico. La scelta non si applica ai formati solo audio. Se il sito non permette di rilevare le qualità, resta possibile tentare il download alla qualità massima.

Per le playlist il menu usa le qualità del video nel link, oppure del primo elemento se il link identifica soltanto la playlist. La risoluzione scelta diventa il limite massimo per ciascun elemento, permettendo di scaricare anche i video disponibili soltanto a qualità inferiori. Per un video singolo viene richiesta la risoluzione esatta, senza passare silenziosamente a una qualità diversa.

La barra di scorrimento dei **Dettagli** compare soltanto quando il testo supera lo spazio visibile e segue il tema scuro dell'app.

Per eseguire i test dell'interfaccia e della selezione delle risoluzioni su Windows:

```bat
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Struttura del progetto

```text
app.py          Interfaccia grafica e gestione dei download
INSTALL.bat     Installazione e verifica dei requisiti
RUN.vbs         Avvio normale senza terminale
RUN_DEBUG.cmd   Avvio diagnostico con terminale
requirements.txt Pacchetti installati nella .venv locale
assets/         Icona della finestra e del collegamento Desktop
```

## Aggiornamenti

Esegui nuovamente `INSTALL.bat` per controllare e aggiornare tutti i componenti. Per aggiornare soltanto yt-dlp, usa il pulsante dedicato nell'interfaccia.

## Note

Alcuni siti o contenuti possono richiedere autenticazione, cookie del browser oppure applicare limitazioni proprie. Utilizza il programma soltanto per contenuti che hai il diritto di scaricare e nel rispetto dei termini del servizio interessato.

Questo progetto non è affiliato né approvato dal progetto ufficiale yt-dlp.
