# Guida Installazione WallpaperChanger su Nuovo PC

## Prerequisiti

1. **Python 3.8 o superiore**
   - Scarica da: https://www.python.org/downloads/
   - Durante l'installazione, **seleziona "Add Python to PATH"**

2. **Verifica installazione Python**
   ```cmd
   python --version
   ```
   Dovrebbe mostrare: `Python 3.x.x`

## Installazione

### Passo 1: Estrai l'archivio
Estrai `WallpaperChanger_Portable.zip` in una cartella, esempio:
```
C:\Users\TuoNome\Documents\WallpaperChanger\
```

### Passo 2: Installa le dipendenze
Apri il **Prompt dei comandi** (cmd) o **PowerShell** nella cartella del progetto e esegui:

**Opzione 1 - Usa requirements.txt (raccomandato):**
```cmd
pip install -r requirements.txt
```

**Opzione 2 - Installa manualmente:**
```cmd
pip install pillow requests pystray keyboard python-dotenv
```

Oppure se hai problemi con `pip`, prova:
```cmd
python -m pip install -r requirements.txt
```

### Passo 3: Configura le API Keys (Opzionale)
Se vuoi usare provider esterni (Unsplash, Pexels, ecc.), modifica il file `.env`:

```
OPENWEATHER_API_KEY=tua_chiave_qui
UNSPLASH_ACCESS_KEY=tua_chiave_qui
PEXELS_API_KEY=tua_chiave_qui
```

### Passo 4: Test manuale
Prima di usare gli script VBS, testa manualmente:

```cmd
cd C:\Users\TuoNome\Documents\WallpaperChanger
python gui_config.py
```

Se funziona, vedrai la GUI aprirsi.

### Passo 5: Avvio con script VBS

Ora puoi usare gli script nella cartella `launchers\`:

- **`start_config_gui.vbs`** - Apre solo la GUI di configurazione
- **`start_wallpaper_changer.vbs`** - Avvia il servizio principale (tray icon + hotkey)
- **`start_wallpaper_with_gui.vbs`** - Avvia entrambi (servizio + GUI)
- **`stop_wallpaper_changer.vbs`** - Ferma il servizio

## Problemi Comuni

### Lo script VBS non fa nulla

**Causa**: Python non è nel PATH o `pythonw.exe` non è trovato

**Soluzione**:
1. Apri cmd e digita `python --version`
2. Se dice "comando non trovato", reinstalla Python con "Add to PATH"
3. Oppure modifica gli script VBS con il percorso completo di Python:

Modifica `start_config_gui.vbs` da:
```vbs
objShell.Run "pythonw ..."
```
A:
```vbs
objShell.Run "C:\Users\TuoNome\AppData\Local\Programs\Python\Python312\pythonw.exe ..."
```

### Errore "No module named 'PIL'" o "No module named 'dotenv'"

**Causa**: Dipendenze non installate

**Soluzione**:
```cmd
pip install -r requirements.txt
```

Oppure installa tutte le dipendenze manualmente:
```cmd
pip install pillow requests pystray keyboard python-dotenv
```

### La hotkey non funziona

**Causa**: Il servizio principale (main.py) non è in esecuzione

**Soluzione**:
- Usa `launchers\start_wallpaper_changer.vbs`
- Oppure `launchers\start_wallpaper_with_gui.vbs`
- Verifica che appaia l'icona nella system tray

### Errore di Permessi (PermissionError) sulla cartella cache

**Causa**: Il percorso della cache nel config.py punta a un utente diverso

**Soluzione**: Apri `config.py` e modifica la sezione `CacheSettings`:
```python
CacheSettings = {
    "directory": "",  # Lascia vuoto per usare il percorso predefinito
    "max_items": 60,
    "enable_offline_rotation": True,
}
```

Se vuoi specificare un percorso personalizzato, usa:
```python
"directory": r"C:\Users\TuoUsername\WallpaperChangerCache",
```

### Errore API Keys

**Causa**: File `.env` mancante o chiavi non valide

**Soluzione**:
- Copia il file `.env.example` in `.env`
- Aggiungi le tue API keys
- Oppure usa solo provider che non richiedono API (LocalFolder, Reddit)

## Verifica Installazione

Dopo l'installazione, verifica che:

1. ✅ La GUI si apra con `python gui_config.py`
2. ✅ Il servizio si avvii con `launchers\start_wallpaper_changer.vbs`
3. ✅ Appaia l'icona "W C" nella system tray
4. ✅ La hotkey (default: Ctrl+Alt+W) cambi il wallpaper
5. ✅ Click destro sulla tray icon mostri il menu completo

## Avvio Automatico all'Accesso Windows

Per avviare automaticamente WallpaperChanger all'avvio di Windows:

1. Premi `Win + R`
2. Digita `shell:startup` e premi Invio
3. Copia `launchers\start_wallpaper_changer.vbs` in questa cartella
4. Al prossimo avvio di Windows, il servizio partirà automaticamente

## Supporto

Se hai problemi:
1. Controlla i log in `wallpaperchanger.log`
2. Esegui manualmente `python main.py` per vedere eventuali errori
3. Verifica che tutte le dipendenze siano installate
