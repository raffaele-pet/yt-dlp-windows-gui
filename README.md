# yt-dlp Windows GUI

Interfaccia grafica non ufficiale per [yt-dlp](https://github.com/yt-dlp/yt-dlp), pensata per scaricare video, audio e playlist su Windows senza utilizzare manualmente il terminale.

## Funzionalità

- download video in MP4;
- download alla massima qualità disponibile;
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
