# CLAUDE.md — Jorge Alba / Distrito Digital

## Quién soy

Jorge Alba Valadez — Fundador y Director de Distrito Digital, agencia de marketing
digital en Aguascalientes, México. Trabajo con múltiples proyectos simultáneos.

---

## ⚡ PRINCIPIOS — Pensar antes de actuar (Karpathy)

1. **Leer completo antes de empezar** — nunca asumir, siempre verificar
2. **Plan antes de código** — definir qué, dónde y por qué antes de tocar archivos
3. **Minimal footprint** — solo modificar lo necesario, no tocar lo que no se pidió
4. **Verificar antes de modificar** — revisar qué existe antes de crear o cambiar
5. **Preguntar si hay duda** — una pregunta concreta, no múltiples
6. **No inventar datos** — si no encuentras algo, decirlo
7. **Commits con intención** — mensajes descriptivos: "feat:", "fix:", "refactor:"

---

## 🚀 Proyectos activos

### FuchoMX
App de Fantasy y Quiniela de Liga MX. 100% social, sin apuestas ni dinero.
- **Repo:** `Zero-Snake-hunter/FuchoMX`
- **Stack:** React Native (frontend) + FastAPI (backend) + MongoDB
- **Deploy:** Railway
- **Módulos principales:**
  - FuchoQuiniela — predicción de resultados por jornada
  - FuchoOnce — fantasy lineup semanal
  - Rankings, logros, notificaciones push
- **Regla crítica:** NUNCA tocar jornadas activas sin confirmación de Jorge

### Árbol de Sefirot
Bot de acompañamiento espiritual cristiano interdenominacional vía WhatsApp.
- **Repo:** `Zero-Snake-hunter/-arbol-de-Sefirot`
- **Stack:** Node.js + Claude Haiku + WhatsApp Cloud API
- **Deploy:** Railway
- **Estado:** Pendiente verificación Meta para acceso público

### Distrito Digital (DD)
Agencia de marketing digital para PyMEs en Aguascalientes.
- **Servicios:** Presencia Activa ($6k) | Atracción ($9k) | Conversión Total ($14k)
- **Add-ons:** Meta Ads, Google Ads, TikTok, YouTube, WhatsApp Bot
- **Correo:** contacto@distrito.digital (Hostinger SMTP)

---

## 🖥️ Infraestructura

### Cortana (servidor local)
- **IP Tailscale:** `100.82.165.47`
- **SSH:** `ssh jorge@100.82.165.47` (sin contraseña)
- **WSL:** Ubuntu 24.04 en Windows 10
- **OpenClaw:** puerto 18789 (bot de Telegram + WhatsApp)
- **Drive montado:** `/mnt/g/Mi unidad/`

### Railway
- FuchoMX API (FastAPI)
- Árbol de Sefirot (Node.js)
- n8n (pendiente instalar)

### Google Drive estructura
```
/mnt/g/Mi unidad/Cortana_Documentos/
├── Agents/          ← Skills de OpenClaw
├── Excel/           ← Prospectos_DD.xlsx, Prospectos_FuchoMX.xlsx
├── Templates/       ← Templates de correo
├── Materiales_Envio/FuchoMX/  ← PDF + video demo
└── Prospectos_DD/   ← Fichas de análisis
```

---

## 🔧 Comandos frecuentes

### Cortana via SSH
```bash
# Conectar
ssh jorge@100.82.165.47

# Recargar OpenClaw
ssh jorge@100.82.165.47 "systemctl --user restart openclaw-gateway"

# Copiar skill a Cortana
scp SKILL.md jorge@100.82.165.47:/home/jorge/.openclaw/skills/[nombre]/SKILL.md

# Ver logs de Cortana
ssh jorge@100.82.165.47 "systemctl --user status openclaw-gateway"
```

### FuchoMX
```bash
# Clonar repo
gh repo clone Zero-Snake-hunter/FuchoMX

# Ver issues abiertos
gh issue list --repo Zero-Snake-hunter/FuchoMX

# Crear issue
gh issue create --repo Zero-Snake-hunter/FuchoMX --title "título" --body "descripción"

# Push y deploy
git add . && git commit -m "feat: descripción" && git push
# Railway despliega automáticamente
```

### Árbol de Sefirot
```bash
gh repo clone Zero-Snake-hunter/-arbol-de-Sefirot
```

---

## 🔴 Reglas críticas

- **NUNCA** hacer push a main sin revisar que no hay jornadas activas en FuchoMX
- **NUNCA** modificar variables de entorno en Railway sin confirmación
- **NUNCA** borrar archivos — mover a carpeta backup o usar git
- **NUNCA** enviar correos o mensajes sin confirmación explícita de Jorge
- **NUNCA** commitear credenciales, tokens o contraseñas
- Si una tarea afecta usuarios activos → ALERTAR antes de proceder

---

## 📧 Credenciales y accesos (referencias, no valores)

- API Keys en Railway → variables de entorno del proyecto
- Anthropic API Key → variable `ANTHROPIC_API_KEY`
- GitHub token → `gh auth status` para verificar
- Hostinger SMTP → `/home/jorge/send_email.py` en Cortana

---

## 🤝 Cómo trabajamos

1. Jorge describe qué quiere lograr
2. Claude Code lee el código relevante primero
3. Propone plan con archivos a modificar
4. Jorge aprueba
5. Claude Code implementa y commitea
6. Verifica que funciona antes de reportar listo

**Formato de reporte:**
```
✅ Hecho: [qué se hizo]
📁 Archivos modificados: [lista]
🔗 Commit: [hash/mensaje]
⚠️ Pendiente: [si hay algo]
```
