# 🐳 Setup Ollama in Docker per WallpaperChanger

## Opzione 1: Docker Run (Veloce)

### Windows/Linux
```bash
# 1. Avvia Ollama container
docker run -d --name ollama -p 11434:11434 ollama/ollama

# 2. Scarica un modello veloce
docker exec -it ollama ollama pull llama3.2:3b

# 3. Verifica
docker exec -it ollama ollama list

# 4. (Opzionale) Testa
curl http://localhost:11434/api/tags
```

### Output atteso:
```json
{
  "models": [
    {
      "name": "llama3.2:3b",
      "modified_at": "2024-...",
      "size": 2019393189
    }
  ]
}
```

---

## Opzione 2: Docker Compose (Raccomandato)

Crea `docker-compose.yml`:

```yaml
version: '3.8'

services:
  ollama:
    image: ollama/ollama:latest
    container_name: ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    restart: unless-stopped
    # Opzionale: GPU support
    # deploy:
    #   resources:
    #     reservations:
    #       devices:
    #         - driver: nvidia
    #           count: 1
    #           capabilities: [gpu]

volumes:
  ollama_data:
```

**Comandi:**
```bash
# Avvia
docker-compose up -d

# Scarica modello
docker-compose exec ollama ollama pull llama3.2:3b

# Verifica modelli
docker-compose exec ollama ollama list

# Logs
docker-compose logs -f ollama

# Stop
docker-compose down
```

---

## Configurazione WallpaperChanger

### Metodo 1: Variabile d'ambiente (Raccomandato)

**Windows PowerShell:**
```powershell
# Temporaneo (solo sessione corrente)
$env:OLLAMA_HOST = "http://localhost:11434"

# Permanente (utente)
[System.Environment]::SetEnvironmentVariable("OLLAMA_HOST", "http://localhost:11434", "User")

# Avvia WallpaperChanger
python gui_modern.py
```

**Windows CMD:**
```cmd
set OLLAMA_HOST=http://localhost:11434
python gui_modern.py
```

**Linux/Mac:**
```bash
export OLLAMA_HOST=http://localhost:11434
python gui_modern.py
```

### Metodo 2: File .env

Crea `.env` nella cartella WallpaperChanger:
```env
OLLAMA_HOST=http://localhost:11434
GEMINI_API_KEY=your_gemini_key_here
```

---

## Test Completo

### 1. Test manuale Docker
```bash
# Controlla container
docker ps | grep ollama

# Controlla API
curl http://localhost:11434/api/tags

# Test generazione
curl -X POST http://localhost:11434/api/generate -d '{
  "model": "llama3.2:3b",
  "prompt": "Say hello in 5 words",
  "stream": false
}'
```

### 2. Test con script Python
```bash
cd "E:\Docker image\WallpaperChanger_Portable\WallpaperChanger"
python test_ollama_fallback.py
```

Output atteso:
```
🧪 WALLPAPER CHANGER - OLLAMA FALLBACK TEST

============================================================
TESTING OLLAMA AUTO-DETECTION
============================================================

[OLLAMA] Configured host: http://localhost:11434

1️⃣  Checking Ollama availability...
✅ Ollama is running!
📦 Found 1 models:
   - llama3.2:3b

2️⃣  Testing model selection...
[OLLAMA] Selected model: llama3.2:3b
🎯 Selected model: llama3.2:3b

3️⃣  Testing Ollama generation...
Prompt: Describe a peaceful mountain wallpaper in 2 sentences.
[OLLAMA] Using local model 'llama3.2:3b' as fallback
✅ Generation successful!
Response: A serene mountain landscape at dawn...
```

### 3. Test quota exceeded nella GUI
```bash
# 1. Apri WallpaperChanger
python gui_modern.py

# 2. Vai su AI Assistant tab

# 3. Clicca "Detect Mood" 10-15 volte rapidamente

# 4. Output atteso nel terminale:
[OLLAMA] Configured host: http://localhost:11434
[AI] Gemini error: 429 You exceeded your current quota...
[AI] Quota exceeded, trying Ollama fallback...
[OLLAMA] Found 1 available models: llama3.2:3b
[OLLAMA] Selected model: llama3.2:3b
[OLLAMA] Using local model 'llama3.2:3b' as fallback
✅ Continua senza errori!
```

---

## Modelli Raccomandati per Docker

### Veloci e Piccoli (2-4 GB)
```bash
docker exec -it ollama ollama pull llama3.2:3b     # Raccomandato
docker exec -it ollama ollama pull llama3.2:1b     # Più veloce
docker exec -it ollama ollama pull phi3:mini       # Alternativa Microsoft
docker exec -it ollama ollama pull gemma:2b        # Google
```

### Bilanciati (4-8 GB)
```bash
docker exec -it ollama ollama pull llama3.1:8b
docker exec -it ollama ollama pull mistral:latest
docker exec -it ollama ollama pull gemma:7b
```

### Potenti (>10 GB) - Solo se hai GPU
```bash
docker exec -it ollama ollama pull llama3.1:70b
docker exec -it ollama ollama pull mixtral:8x7b
```

---

## Troubleshooting

### Container non parte
```bash
# Check logs
docker logs ollama

# Riavvia
docker restart ollama

# Rimuovi e ricrea
docker rm -f ollama
docker run -d --name ollama -p 11434:11434 ollama/ollama
```

### Port già in uso
```bash
# Usa porta diversa
docker run -d --name ollama -p 11435:11434 ollama/ollama

# Configura in .env
OLLAMA_HOST=http://localhost:11435
```

### Modello non si scarica
```bash
# Verifica connessione
docker exec -it ollama curl -I https://ollama.ai

# Scarica manualmente con verbose
docker exec -it ollama ollama pull llama3.2:3b --verbose
```

### WallpaperChanger non trova Ollama
```bash
# Verifica variabile d'ambiente
echo $OLLAMA_HOST    # Linux/Mac
echo %OLLAMA_HOST%   # Windows CMD
$env:OLLAMA_HOST     # Windows PowerShell

# Test connessione
curl http://localhost:11434/api/tags

# Riavvia WallpaperChanger con debug
python gui_modern.py
# Guarda il log: [OLLAMA] Configured host: ...
```

---

## Performance Tips

### 1. Usa volume per persistenza
```yaml
volumes:
  - ollama_data:/root/.ollama  # I modelli rimangono dopo riavvio
```

### 2. Limita RAM (opzionale)
```yaml
deploy:
  resources:
    limits:
      memory: 8G
```

### 3. GPU Support (Nvidia)
```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

---

## Quick Start Completo

```bash
# 1. Crea container
docker run -d --name ollama -p 11434:11434 ollama/ollama

# 2. Scarica modello
docker exec -it ollama ollama pull llama3.2:3b

# 3. Configura WallpaperChanger
echo OLLAMA_HOST=http://localhost:11434 > .env

# 4. Test
curl http://localhost:11434/api/tags

# 5. Avvia app
python gui_modern.py

# 6. Test nella GUI: clicca "Detect Mood" 15 volte
```

✅ Fatto! Ora hai AI locale illimitata via Docker!
