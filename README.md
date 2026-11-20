# MyFeed

Tu red social personal para **aprender en vez de hacer scroll infinito**. Un feed vertical, como el de las apps de vídeos cortos, pero solo con contenido de tus 6 temas:

| | Categoría |
|---|---|
| ⚽ | Fútbol y rendimiento (fútbol sala, velocidad, fuerza, nutrición, recuperación) |
| 🛡️ | Ciberseguridad |
| 🤖 | Inteligencia artificial |
| 💻 | Programación y tecnología |
| 🧠 | Psicología y filosofía |
| 🔭 | Ciencia y mundo (sin política) |

Los vídeos se reproducen con el **reproductor oficial** (YouTube, TikTok, Instagram y Vimeo). Nada se descarga ni se vuelve a subir, y no se hace scraping: solo se usan APIs oficiales, RSS públicos y embeds.

---

## Índice

1. [Qué hace](#qué-hace)
2. [Arrancarlo en tu PC (5 minutos)](#arrancarlo-en-tu-pc)
3. [Usarlo en el iPhone](#usarlo-en-el-iphone)
4. [Claves de API (opcionales)](#claves-de-api-opcionales)
5. [Cómo funciona por dentro](#cómo-funciona-por-dentro)
6. [Consumo de recursos](#consumo-de-recursos)
7. [Comandos útiles y solución de problemas](#comandos-útiles-y-solución-de-problemas)
8. [Desarrollo y pruebas](#desarrollo-y-pruebas)

---

## Qué hace

**El feed**
- Desliza hacia arriba como en cualquier app de vídeos verticales. Puedes mezclar vídeos **cortos y largos** o filtrar por tipo (Todo, Cortos, Largos, Artículos).
- Cada tarjeta lleva **Me gusta**, **Guardar** (en colecciones), **Nota** («¿qué te llevas de esto?») y **Más** (no me interesa, silenciar creador, ver menos de este tema, vídeo roto).
- **«¿Por qué veo esto?»** te explica cada recomendación, por ejemplo «Te gusta ciberseguridad · Fuente fiable · Reciente».
- Incluye 30 **microlecciones** originales en español, de 1 minuto, para que el feed nunca esté vacío.

**Comandos escritos** (botón ✨ del feed). Le escribes lo que quieres y el feed cambia durante un rato:
- «hoy quiero solo fútbol sala y velocidad»
- «más ciberseguridad pero nada de noticias, por 2 horas»
- «vídeos cortos de IA para principiantes»
- «nada de filosofía esta semana»

**Pestañas**
- **Inicio:** el feed.
- **Hoy:** los destacados del día (8, repartidos entre tus temas) y un resumen diario.
- **Explorar:** búsqueda y peso de cada categoría (Poco, Normal, Más o Prioridad), con subtemas que puedes activar o desactivar.
- **Biblioteca:** guardados, colecciones, me gusta, notas e historial.
- **Yo:** minutos de hoy, racha, gráfica de 7 días, tiempo por tema y accesos a:
  - **Repaso:** tarjetas con las ideas clave de lo que guardaste.
  - **Lo que aprendí de ti:** tus gustos, que puedes borrar uno a uno.
  - **Creadores:** apruebas o descartas lo que sugiere la IA y puedes seguir a alguien pegando su enlace.
  - **Agentes:** qué hizo cada agente y cuándo.
  - **Ajustes**.

**Bienestar** (lo que la app hace para no engancharte)
- **Límite diario:** 45 minutos por defecto. Al llegar, la app te propone parar, y puedes pedir 10 minutos más.
- **Pausa consciente** cada 20 minutos.
- Una pregunta opcional al abrir la app: «¿Qué quieres aprender hoy?».
- **Huecos de exploración** para no encerrarte en una burbuja.
- Cuando se acaba lo nuevo, la app te lo dice en vez de rellenar con cualquier cosa.

**Añadir cualquier enlace:** en Inicio pulsa ＋ y pega un enlace de TikTok, Instagram, YouTube, Vimeo o un artículo. Quedará en tu feed y en Guardados.

---

## Arrancarlo en tu PC

Solo necesitas **Docker Desktop** (Windows o Mac) o Docker Engine (Linux).

```bash
git clone https://github.com/JuanpaSzn/my-feed.git
cd my-feed
cp .env.example .env        # opcional: aquí van las claves (ver más abajo)
docker compose --profile web up -d --build
```

La primera vez tarda unos minutos en construir. Luego:

- App web: **http://localhost:8080**
- API: http://localhost:8000. Documentación interactiva en http://localhost:8000/docs

Si tu PC va justo de recursos, usa el **modo lite**: un solo contenedor con SQLite (~100 MB de RAM). No incluye la app web, así que tendrás que usar Expo (más abajo).

```bash
docker compose -f docker-compose.lite.yml up -d --build
```

Para pararlo: `docker compose --profile web down`. Tus datos se conservan en un volumen de Docker.

---

## Usarlo en el iPhone

El iPhone y el PC deben estar **en la misma wifi**. Primero averigua la IP local del PC:
- Windows: `ipconfig`, buscando «Dirección IPv4», algo como `192.168.1.50`.
- Mac: `ipconfig getifaddr en0`.

### Opción A · Safari (la más fácil, no necesitas instalar nada)

1. Arranca el stack con `--profile web`, como se explica arriba.
2. En el iPhone abre Safari y entra en `http://192.168.1.50:8080`, cambiando la IP por la de tu PC.
3. Pulsa Compartir y luego **«Añadir a pantalla de inicio»**. Te queda un icono de MyFeed como si fuera una app.

### Opción B · Expo Go (app nativa, con vibración y mejor reproductor)

1. Instala **Expo Go** desde la App Store.
2. En el PC necesitas **Node.js 20 o superior**:
   ```bash
   cd mobile
   npm install
   npx expo start
   ```
3. Escanea el código QR con la **cámara del iPhone** y se abrirá en Expo Go.
4. La app detecta sola la IP del servidor (puerto 8000). Si no conecta, ve a **Yo → Ajustes → Servidor**, escribe `http://192.168.1.50:8000` y pulsa **Conectar**.

> **Si Windows bloquea la conexión:** la primera vez, el firewall preguntará si Docker o Node pueden usar la red. Acepta en **redes privadas**.

---

## Claves de API (opcionales)

**MyFeed funciona sin ninguna clave.** Sin claves, se nutre de los RSS públicos de los ~30 creadores y 20 fuentes que vienen preconfigurados, y clasifica todo con reglas propias. Las claves lo hacen más listo.

Ponlas en el archivo `.env`, en la raíz del proyecto, y reinicia con `docker compose --profile web up -d`.

| Clave | Para qué sirve | Dónde conseguirla | Coste |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Resúmenes en español, ideas clave, mejor clasificación y calidad, comandos escritos más finos y resumen diario | [console.anthropic.com](https://console.anthropic.com/) → API Keys | De pago por uso. `CLAUDE_DAILY_ITEM_LIMIT=300` pone un tope diario |
| `YOUTUBE_API_KEY` | Duraciones exactas (cortos o largos), búsquedas por tema y **descubrimiento de creadores nuevos** que luego apruebas tú | [Google Cloud Console](https://console.cloud.google.com/) → crea un proyecto → «APIs y servicios» → habilita **YouTube Data API v3** → Credenciales → Crear clave de API | Gratis (10 000 unidades al día; MyFeed usa unas 2 000) |
| `APP_TOKEN` | Contraseña de la API. Solo hace falta si la abres fuera de tu casa | Invéntala: una frase larga | — |

Otros ajustes del `.env`:
- `CLAUDE_MODEL`: por defecto `claude-opus-5-5`.
- `CLAUDE_EFFORT`: `low` es más barato.
- `TIMEZONE`: `America/Bogota`.
- `DISCOVERY_INTERVAL_MINUTES`: cada cuánto busca contenido nuevo; 90 por defecto.

Para comprobar qué está activo, mira **Yo → Ajustes → Estado**.

---

## Cómo funciona por dentro

```
iPhone (Expo / Safari)  ──HTTP──▶  FastAPI  ──▶  PostgreSQL (datos)
                                     │      └─▶  Redis (caché del feed, bloqueos)
                                     │
                     Planificador (cada 90 min y diario)
     ┌──────────────┬───────────────┼──────────────┬──────────────┐
  Explorador     Analista     Recomendador     Preferencias     Curador
```

| Agente | Qué hace |
|---|---|
| **Explorador** | Lee los RSS de tus creadores y fuentes. Usa peticiones condicionales con ETag, así que si nada cambió no se descarga nada. Con la clave de YouTube, hace búsquedas rotativas por subtema y propone creadores que aparecen varias veces con buen contenido. Además comprueba con oEmbed que los vídeos siguen existiendo. |
| **Analista** | Clasifica cada contenido en categoría y subtema, y detecta clickbait, política y noticias. Puntúa la calidad educativa. Con Claude, también escribe un resumen y las ideas clave. |
| **Recomendador** | Puntúa cada contenido así: **relevancia 34 %, calidad 26 %, actualidad 16 %, credibilidad 14 %, novedad 10 %**. Las visualizaciones o la viralidad **no** cuentan. Después reordena para mezclar temas, sin más de dos seguidos del mismo, y deja un hueco de exploración cada 8. |
| **Preferencias** | Aprende de tus me gusta, guardados, descartes, saltos rápidos y vídeos vistos enteros. Los gustos se desvanecen poco a poco cada día, para que el feed evolucione contigo. |
| **Curador** | Cada mañana elige los 8 destacados del día y escribe el resumen. |

**Decisiones tomadas (puedes cambiarlas):**
- Vídeos cortos y largos mezclados, con filtro.
- El contenido se actualiza continuamente y además hay destacados diarios.
- La IA **sugiere** creadores, pero **tú los apruebas**: nada entra en tu feed sin tu permiso.

**Stack:**
- Backend: FastAPI y SQLAlchemy async, con PostgreSQL 17, Redis 7 y Claude API (opcional).
- App: React Native, Expo SDK 58 y expo-router.
- Web: el mismo código compilado y servido con nginx.

```
backend/   API, agentes, planificador y pruebas (pytest)
mobile/    App Expo (iPhone y web)
e2e/       Pruebas de extremo a extremo con Playwright (emulando un iPhone 14)
```

---

## Consumo de recursos

Pensado para un PC modesto que además ejecuta otros proyectos:

| Contenedor | RAM en reposo | Límite |
|---|---|---|
| api | ~80 MB | 384 MB |
| db (Postgres) | ~50 MB | 256 MB |
| redis | ~4 MB | 64 MB |
| web (nginx) | ~5 MB | 32 MB |
| **Total** | **~140 MB** | |

- La API corre en un único proceso.
- Postgres está ajustado para memoria baja, y Redis no guarda nada en disco.
- Los logs están limitados a 5 MB por contenedor.
- El explorador hace como máximo 4 conexiones a la vez.
- El modo lite baja todo a ~100 MB.

---

## Comandos útiles y solución de problemas

```bash
docker compose ps                         # ¿está todo en marcha?
docker compose logs -f api                # ver qué hacen los agentes
curl -X POST localhost:8000/api/agents/run -H 'content-type: application/json' -d '{"agent":"explorer","force":true}'   # buscar contenido ya
docker compose --profile web down -v      # borrar TODO (datos incluidos) y empezar de cero
```

| Problema | Solución |
|---|---|
| El iPhone no conecta | Comprueba que esté en la misma wifi, que la IP sea la correcta y el firewall de Windows (acepta en redes privadas). Prueba a abrir `http://IP:8000/health` en Safari |
| El feed muestra pocas cosas nuevas | Espera a la primera exploración (unos minutos tras arrancar) o lánzala desde **Yo → Agentes** |
| Un vídeo no se reproduce | Algunos creadores bloquean el embed. Usa **Más → Vídeo roto** y desaparecerá. También puedes abrirlo en la app original |
| Detrás de un proxy corporativo con certificado propio | `docker compose build --secret id=ca,src=/ruta/ca.crt` |

---

## Desarrollo y pruebas

```bash
# Backend (Python 3.12+)
cd backend && python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q                                   # 32 pruebas, SQLite
TEST_DATABASE_URL=postgresql+asyncpg://... pytest -q   # también pasan con Postgres

# App
cd mobile && npm install && npx tsc --noEmit && npx expo start

# Extremo a extremo (con el stack levantado con --profile web)
cd e2e && npm i playwright && node flows.spec.js
```

---

*MyFeed · hecho para aprender, no para engancharte.*
