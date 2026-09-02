# yt-dlp Windows GUI

Interfaccia grafica non ufficiale per [yt-dlp](https://github.com/yt-dlp/yt-dlp), pensata per scaricare video, audio e playlist su Windows senza utilizzare manualmente il terminale.

## Funzionalità

- download video in MP4;
- download alla massima qualità disponibile;
- estrazione audio in MP3 o M4A;
- supporto alle playlist;
- scelta della cartella di destinazione;
- barra di avanzamento e annullamento del download;
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

L'installer controlla i componenti esistenti, installa solo quelli mancanti, configura il `PATH`, verifica le versioni e crea un collegamento **YT-DLP** sul Desktop.

Per eseguire soltanto un controllo, senza installare o modificare nulla:

```bat
INSTALL.bat --check
```

## Avvio

Fai doppio clic su `RUN.vbs` per aprire l'interfaccia senza mostrare il terminale.

Se l'applicazione non parte, utilizza `RUN_DEBUG.cmd` per visualizzare eventuali errori.

## Struttura del progetto

```text
app.py          Interfaccia grafica e gestione dei download
INSTALL.bat     Installazione e verifica dei requisiti
RUN.vbs         Avvio normale senza terminale
RUN_DEBUG.cmd   Avvio diagnostico con terminale
```

## Aggiornamento dei componenti

```powershell
winget upgrade --id yt-dlp.yt-dlp
winget upgrade --id yt-dlp.FFmpeg
winget upgrade --id DenoLand.Deno
```

## Note

Alcuni siti o contenuti possono richiedere autenticazione, cookie del browser oppure applicare limitazioni proprie. Utilizza il programma soltanto per contenuti che hai il diritto di scaricare e nel rispetto dei termini del servizio interessato.

Questo progetto non è affiliato né approvato dal progetto ufficiale yt-dlp.
