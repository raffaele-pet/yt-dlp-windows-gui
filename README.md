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
- [WinGet](https://learn.microsoft.com/windows/package-manager/winget/), normalmente incluso nelle versioni moderne di Windows tramite **App Installer**.

Gli altri componenti possono essere installati automaticamente:

- Python 3.12;
- yt-dlp;
- FFmpeg;
- Deno.

## Installazione

1. Scarica la repository come file ZIP da GitHub.
2. Estrai l'intera cartella.
3. Fai doppio clic su `INSTALL.bat`.
4. Segui l'avanzamento mostrato nel terminale.

L'installer controlla i componenti esistenti, installa quelli mancanti e cerca gli aggiornamenti disponibili. yt-dlp viene confrontato con `stable@latest` della [repository ufficiale](https://github.com/yt-dlp/yt-dlp) e, se necessario, aggiornato durante l'installazione; Python, FFmpeg e Deno vengono aggiornati tramite WinGet. Se Python è utilizzato da un altro programma, il suo aggiornamento viene rimandato in sicurezza e l'installer indica come completarlo in seguito. Al termine, configura il `PATH`, verifica le versioni e crea un collegamento **YT-DLP** sul Desktop con l'[icona richiesta](https://img.icons8.com/?size=100&id=cLcs1xqp7qTl&format=png&color=000000).

Per eseguire soltanto un controllo, senza installare o modificare nulla:

```bat
INSTALL.bat --check
```

## Avvio

Fai doppio clic su `RUN.vbs` per aprire l'interfaccia senza mostrare il terminale.

Se l'applicazione non parte, utilizza `RUN_DEBUG.cmd` per visualizzare eventuali errori.

Il pulsante **Aggiorna yt-dlp** controlla la release stabile ufficiale, mostra i dettagli dell'operazione nella finestra e installa l'aggiornamento quando necessario.

## Struttura del progetto

```text
app.py          Interfaccia grafica e gestione dei download
INSTALL.bat     Installazione e verifica dei requisiti
RUN.vbs         Avvio normale senza terminale
RUN_DEBUG.cmd   Avvio diagnostico con terminale
assets/         Icona della finestra e del collegamento Desktop
```

## Aggiornamenti

Esegui nuovamente `INSTALL.bat` per controllare e aggiornare tutti i componenti. Per aggiornare soltanto yt-dlp, usa il pulsante dedicato nell'interfaccia.

## Note

Alcuni siti o contenuti possono richiedere autenticazione, cookie del browser oppure applicare limitazioni proprie. Utilizza il programma soltanto per contenuti che hai il diritto di scaricare e nel rispetto dei termini del servizio interessato.

Questo progetto non è affiliato né approvato dal progetto ufficiale yt-dlp.
