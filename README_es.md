![BabelChat](https://github.com/Yumash/BabelChat/raw/main/assets/icon.png)

# BabelChat

**Rompe la barrera del idioma en World of Warcraft**  
Traducción de chat en tiempo real — app acompañante + addon de WoW

[English version](https://github.com/Yumash/BabelChat/blob/main/README.md) | [Русская версия](https://github.com/Yumash/BabelChat/blob/main/README_ru.md)

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/Yumash/BabelChat/blob/main/LICENSE) [![Python](https://img.shields.io/badge/Python-3.12+-yellow.svg)](https://python.org) [![Release](https://img.shields.io/github/v/release/Yumash/BabelChat?include_prereleases)](https://github.com/Yumash/BabelChat/releases) [![CurseForge](https://img.shields.io/curseforge/dt/1491616?logo=curseforge&logoColor=white&label=CurseForge&color=F16436)](https://www.curseforge.com/wow/addons/babelchat) [![Wago](https://img.shields.io/badge/Wago-Addons-C1272D?logo=wago&logoColor=white)](https://addons.wago.io/addons/96d2BEGO)

---

![BabelChat Demo](https://github.com/Yumash/BabelChat/raw/main/assets/demo.webp)

*El overlay se abre, se pliega, se arrastra, el inglés se vuelve ruso — y abajo el addon glosa la misma línea en el chat. [Calidad original](https://github.com/Yumash/BabelChat/raw/main/assets/demo.mp4).*

## El Problema

Entras a una banda PUG. El tanque explica tácticas — en ruso. El sanador pregunta algo — en alemán. Tú hablas español (o inglés, o francés). Nadie se entiende. Comienza el pull, la gente muere, y alguien escribe "gg noob" — la única frase que todos conocen.

**Esto pasa constantemente** en los grupos cross-realm y cross-región de WoW. La barrera del idioma arruina la coordinación, causa wipes y hace el juego menos divertido.

## La Solución

BabelChat traduce el chat de WoW **en tiempo real**. Un pequeño addon captura los mensajes del juego; una app acompañante los envía a un proveedor de traducción y muestra el resultado en un elegante overlay sobre WoW.

**Ves el mensaje original al instante. La traducción aparece 0.5–2 segundos después.**

Frases comunes como "gg", "ty", "ready?", "pull" se traducen al instante desde un frasario integrado — sin llamada API, sin demora. Las oraciones completas van al proveedor y llegan en 1–2 segundos. El mismo mensaje nunca se traduce dos veces (caché).

### ¿Cuándo es útil BabelChat?

- **PUGs cross-realm** — entiende las tácticas del tanque ruso, las preguntas del sanador alemán
- **Hermandades internacionales** — sigue el chat de hermandad en tu idioma sin pedir "english pls"
- **Jugando en servidores extranjeros** — ¿entraste a un realm francés o coreano? El chat ahora es legible
- **Liderando bandas** — da comandos en tu idioma, los jugadores los ven en el suyo
- **Susurros de desconocidos** — entiende ese mensaje aleatorio en portugués

## Características

- **Traducción streaming** — el original aparece al instante, la traducción sigue 0.5–2s después
- **Detección automática de idioma** — offline, ~1ms por mensaje (lingua-py)
- **22 idiomas** — EN, RU, DE, FR, ES, IT, PT, PL, NL, SV, DA, FI, CS, RO, HU, BG, EL, TR, UK, JA, KO, ZH
- **Overlay inteligente** — tema oscuro WoW, colores de canal, transparente al clic, arrastrable
- **Traducción bidireccional** — traduce chat entrante Y compone mensajes salientes en cualquier idioma
- **Frasario integrado** — 53 frases + 75 abreviaturas gaming sin API
- **Glosario WoW** — 436 términos gaming (lfm, wts, dps, tank, etc.) en 14 idiomas
- **Filtros de canal** — Grupo, Banda, Hermandad, Decir, Grito, Susurro, Mazmorra, Comercio, General, Servicios, Buscar grupo, Canales propios, Emotes
- **Cuatro proveedores de traducción** — GigaChat (el predeterminado), MyMemory, DeepL, Microsoft. Si el preferido falla o agota su cuota, el siguiente configurado toma el mensaje
- **Caché de traducciones** — SQLite thread-safe + LRU, el mismo texto nunca se traduce dos veces
- **Teclas de acceso rápido** — activa/desactiva sin salir del juego
- **Multiplataforma** — compatible con Windows y Linux (via Proton/Wine)

## Proveedores de traducción

La app incluye cuatro. La cadena se prueba en este orden, y el proveedor que
falla o agota su cuota pasa el mensaje al siguiente:

| Proveedor | Cuánto cuesta | Qué necesita |
| --- | --- | --- |
| **GigaChat** (Sber) — el predeterminado | Gratis para particulares: 1M de tokens al año, unos 50.000–70.000 mensajes | Un Sber ID. Sin tarjeta. Funciona desde Rusia sin VPN — [cómo obtener la clave](https://github.com/Yumash/BabelChat/blob/main/docs/user/gigachat.md) |
| **MyMemory** | Gratis | Nada en absoluto. Funciona desde el primer arranque, antes de configurar nada. La calidad es menor, así que va por debajo de los demás en la cadena |
| **DeepL** | Plan gratuito: 500K caracteres al mes (~10K mensajes) | El registro pide una tarjeta solo para verificar la identidad; nunca se cobra |
| **Microsoft Translator** | Plan gratuito: 2M de caracteres al mes, sin tarjeta | Una cuenta de Azure |

GigaChat va primero porque de los cuatro es el único al que un jugador en Rusia
puede registrarse sin tarjeta extranjera ni VPN. Cualquiera de ellos puede ser
el preferido en *Configuración → General*, y el asistente lo pregunta en el
primer arranque.

## ¿Por qué la traducción tarda 0.5–2 segundos?

BabelChat usa **renderizado progresivo** (streaming):

1. **Ves el mensaje original inmediatamente** (0ms de demora)
2. **La traducción se añade a la misma línea**, tras una flecha, cuando el proveedor responde (0.5–2s)

La demora viene del round-trip a los servidores del proveedor — tu texto viaja, se traduce por una red neuronal y vuelve. Es la misma latencia que Google Translate o cualquier servicio de traducción en la nube.

**Instantáneo (sin demora):**
- Abreviaturas gaming: `gg`, `ty`, `brb`, `afk`, `wp`, `lol` — del frasario
- Frases comunes: "hello", "thanks", "ready?", "good game" — del frasario
- Mensajes repetidos — del caché
- Mensajes en tu propio idioma — se muestran sin traducción

**0.5–2s:**
- Oraciones completas en idiomas extranjeros — requieren una llamada API al proveedor
- Primera aparición de cualquier frase — luego se cachea

## Cómo funciona

```
┌──────────────────────────────────────────────────────────┐
│  World of Warcraft                                       │
│                                                          │
│  Addon BabelChat                                         │
│  ├── Intercepta eventos CHAT_MSG_* via WoW API           │
│  ├── Buffer circular (50 mensajes, flush cada 250ms)     │
│  └── Escribe en BabelChatDB.wctbuf (Lua SavedVariable)  │
└──────────┬───────────────────────────────────────────────┘
           │  Lectura de memoria (cada 250ms) por un puntero que el
           │  addon deja para eso — sin búsqueda, ~0,1% de un núcleo
           │  Windows: ReadProcessMemory / Linux: process_vm_readv
           ▼
┌──────────────────────────────────────────────────────────┐
│  App acompañante (Python + Rust)                         │
│                                                          │
│  Escáner Rust ──→ Parser ──→ Detector de idioma          │
│       │                           │                      │
│       │    Frasario (instantáneo) ┤                      │
│       │    Caché (instantáneo) ───┤                      │
│       │    API proveedor (0.5-2s) ┤                      │
│       │                           ▼                      │
│       └──────────→ Overlay (PyQt6 / GTK4)                │
└──────────────────────────────────────────────────────────┘
```

### ¿Por qué una app acompañante?

El sandbox Lua de WoW **no puede hacer peticiones HTTP**. El addon captura el chat pero no puede llamar a una API de traducción. La app acompañante resuelve esto leyendo el buffer del addon desde la memoria del proceso.

BabelChat solo **lee** memoria — nunca escribe, inyecta ni automatiza nada. Warden (anti-cheat de WoW) no detecta acceso de solo lectura.

> **¿Por qué no leer WoWChatLog.txt?** Lo intentamos. WoW almacena el log de chat con un buffer de ~4KB y lo vacía de forma impredecible — retrasos de 1 a 5+ minutos. Nuestro addon escribe en una cadena Lua en memoria, y la app la lee cada 250ms — latencia inferior a un segundo.

## Actualización desde ChatTranslatorHelper

Si usabas nuestro addon anterior (ChatTranslatorHelper, era TWW), BabelChat migra automáticamente tus ajustes. Solo instala BabelChat y elimina la carpeta `ChatTranslatorHelper` de `Interface/AddOns/`.

## Instalación

### Windows — Inicio rápido

1. Descarga `BabelChat.zip` de [Releases](https://github.com/Yumash/BabelChat/releases)
2. Extrae y ejecuta `BabelChat.exe` — **no** hacen falta permisos de administrador
3. Sigue el asistente (elige un traductor, configura la ruta de WoW, instala el addon). GigaChat es gratis para particulares y no pide tarjeta; también puedes saltarte este paso y quedarte solo con el diccionario en el juego.
4. Abre WoW, entra a un grupo — las traducciones aparecerán automáticamente

### Linux (Proton/Wine) — Inicio rápido

1. Descarga el `.AppImage`, el `.deb` o el `.rpm` de [Releases](https://github.com/Yumash/BabelChat/releases) — el AppImage no necesita instalación, los paquetes se instalan como `babelchat`
2. Ejecútalo (`chmod +x BabelChat-*.AppImage && ./BabelChat-*.AppImage`, o `babelchat` una vez instalado el paquete)
3. Sigue el asistente (elige un traductor, configura la ruta de WoW, instala el addon). GigaChat es gratis para particulares y no pide tarjeta; también puedes saltarte este paso y quedarte solo con el diccionario en el juego.
4. Abre WoW, entra a un grupo — las traducciones aparecerán automáticamente

El addon por separado es `BabelChat-Addon.zip` en la misma release — descomprímelo
en `Interface/AddOns/` si solo quieres el diccionario dentro del juego.

### Desde el código fuente (Windows)

```bash
git clone https://github.com/Yumash/BabelChat.git
cd BabelChat
pip install -r requirements.txt
python -m app.main
```

### Desde el código fuente (Linux)

```bash
git clone https://github.com/Yumash/BabelChat.git
cd BabelChat
echo 0 | sudo tee /proc/sys/kernel/yama/ptrace_scope

# Compilar el escáner Rust (requerido en Linux)
cargo build --release --manifest-path babelchat_scanner_linux/Cargo.toml
cp babelchat_scanner_linux/target/release/libbabelchat_scanner.so app/

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.main_gtk
```

El addon no escribe su buffer en memoria hasta que actives el acompañante: en
WoW, `/babel config` → **App Acompañante** → marca la casilla. Sin ella el
diccionario del juego funciona y el overlay se queda vacío.

### Addon WoW (manual)

Copia `addon/BabelChat/` a `World of Warcraft/_retail_/Interface/AddOns/BabelChat/`

## Glosario WoW

BabelChat incluye un diccionario de **436 términos gaming** en **14 idiomas**:

| Categoría        | Ejemplos                             | Cantidad |
| ---------------- | ------------------------------------ | -------- |
| Social           | ty, thx, np, gj, lol, gg, brb, omw   | 83       |
| Banda y mazmorra | trash, wipe, nerf, ninja, boe, cd    | 63       |
| Clases y specs   | warrior, dk, ret, bm, disc, resto    | 59       |
| Jerga            | glhf, copium, pug, brez, kite, diff  | 49       |
| Combate          | aggro, aoe, cc, dps, heal, tank, dot | 39       |
| Grupos           | lfm, lf1m, lf2m, premade             | 36       |
| Contenido final  | delve, keystone, affix, warband, ksm | 26       |
| Estadísticas     | hp, mana, crit, haste, mastery       | 25       |
| Profesiones      | jc, bs, enchant, herb, alch, tailor  | 17       |
| Estado           | afk, oom, brb, omw                   | 14       |
| Roles            | tank, healer, dps                    | 11       |
| Comercio         | wtb, wts, wtt, cod, mats, bis        | 9        |
| Hermandad        | gm, officer, recruit, gbank          | 5        |

Otras dos categorías no tienen archivo de datos propio: los nombres de zonas y
los de conjuntos de objetos vienen de LibBabble, y cada una tiene su casilla en
las opciones del addon.

Los términos se anotan en gris en la misma línea del mensaje, como pares
`término = significado` separados por un punto medio — tres como máximo, y luego
un contador. Mantenerlo en una línea es lo que hace legible un canal de Comercio
concurrido, y deja funcionando la copia del chat. Mientras la app acompañante
está en marcha el addon se calla y deja hablar al overlay, para que un mismo
mensaje no se traduzca dos veces con palabras distintas.

### Contribuir términos

Edita el archivo `addon/BabelChat/Data/*.lua` correspondiente:

```lua
["newterm"] = {
    enUS = "English translation",
    esES = "Traducción española",
    ruRU = "Русский перевод",
    deDE = "Deutsche Übersetzung",
    frFR = "Traduction française",
    -- ... (14 idiomas)
},
```

## Cumplimiento con ToS de Blizzard

| Aspecto            | Estado                                                           |
| ------------------ | ---------------------------------------------------------------- |
| Lectura de memoria | Solo lectura. Sin escritura, sin inyección. Warden no lo detecta |
| Overlay            | Permitido. Como Discord Overlay                                  |
| API del addon      | Hooks estándar CHAT\_MSG\_\*. Usado por todos los addons de chat |
| Sin inyección      | Sin DLL injection, sin hooking, sin escritura en memoria de WoW  |
| Sin automatización | Traducción saliente via portapapeles (pegado manual Ctrl+V)      |

## Privacidad — qué sale de tu máquina

BabelChat traduce enviando el texto de los mensajes a un proveedor de
traducción. Eso significa que **los mensajes de otros jugadores van a un
tercero**, susurros y chat de hermandad incluidos, y esos jugadores nunca lo
aceptaron. Conviene saberlo antes de activar canales:

- **Qué se envía:** el texto de los mensajes de los canales que hayas activado,
  y nada más. Un canal desmarcado se descarta antes de que salga ninguna petición.
- **Quién lo recibe:** el proveedor que hayas configurado — GigaChat (Sber),
  MyMemory, DeepL o Microsoft. Cada uno tiene su propia política de privacidad.
- **Qué se guarda localmente:** las traducciones se cachean siete días, con el
  texto original incluido, para no pagar dos veces por la misma línea.
  *Configuración → Borrar caché de traducciones* lo elimina todo.
- **Qué no se guarda:** no se escribe nada en disco sobre el chat capturado a
  menos que actives *Guardar el chat capturado en un archivo* para diagnosticar
  un problema. Ese archivo contiene los mensajes enteros — desactívalo al terminar.
- **Los susurros** son el canal más sensible y están activados por defecto. Si
  compartes máquina, o traduces en una hermandad que no lo esperaría, desmárcalos.

El diccionario del juego por sí solo no envía nada a ninguna parte: funciona
enteramente dentro de WoW, así que una instalación sin la app no genera tráfico
alguno.

## Limitaciones

- **Lee la memoria del proceso** — sin permisos elevados en Windows; `ptrace_scope=0` en Linux
- **Compositor de Linux** — el overlay se pone por encima de un juego a pantalla completa solo donde existe layer-shell. En X11 recurre a una ventana siempre visible; en GNOME Wayland no hay ninguna de las dos y la app se abre en una ventana normal, cosa que avisa al arrancar
- **Límites de los planes gratuitos** — todos los proveedores tienen uno (ver la tabla de arriba). Cuando uno se agota, la cadena pasa al siguiente
- **Mensajes salientes** — copiar → pegar en chat WoW (por diseño, cumplimiento ToS)

## Tecnologías

| Componente          | Tecnología                                                              |
| ------------------- | ----------------------------------------------------------------------- |
| App                 | Python 3.12, PyQt6 (Windows) / GTK4 + layer-shell (Linux)               |
| Lectura de memoria  | Biblioteca en Rust; lee por un puntero del addon, no buscando           |
| Escáner Rust        | Ancla y pulso; barrido completo solo de respaldo; prioridad de fondo     |
| Detección de idioma | lingua-py (offline)                                                     |
| Traducción          | GigaChat, MyMemory, DeepL, Microsoft — en ese orden                     |
| Caché               | SQLite + LRU                                                            |
| Compilación         | PyInstaller → .exe (Windows) / AppImage, .deb, .rpm (Linux)             |
| Addon               | Lua 5.1, WoW API                                                        |
| Tests               | 1146 tests (pytest)                                                      |

## Desarrollo

```bash
python -m app.main        # Ejecutar (Windows)
python -m app.main_gtk    # Ejecutar (Linux)
pytest                    # Tests
ruff check .              # Linter

# Linux: compilar escáner Rust antes de ejecutar
cargo build --release --manifest-path babelchat_scanner_linux/Cargo.toml
cp babelchat_scanner_linux/target/release/libbabelchat_scanner.so app/

# Compilar binarios
pyinstaller build.spec          # Windows .exe
pyinstaller build-linux.spec    # Linux binario
```

## Apoyar el proyecto

Proyecto creado por tres autores:

| Componente                                                                     | Autor               | Apoyar                                                  |
| ------------------------------------------------------------------------------ | ------------------- | ------------------------------------------------------- |
| **Origen del glosario** — 314 de los 436 términos y la idea de glosar el chat  | **Pirson**          | [Buy Me a Coffee](https://buymeacoffee.com/franciscorb) |
| **App acompañante** — overlay, proveedores de traducción, lectura de memoria, streaming | **Andrey Yumashev** | [Donate](https://yumatech.ru/donate/)          |

## Documentación

- **[Guía de usuario](https://github.com/Yumash/BabelChat/blob/main/docs/user/README.md)** — inicio rápido, configuración, FAQ
- **[Documentación técnica](https://github.com/Yumash/BabelChat/blob/main/docs/tech/README.md)** — arquitectura, lector de memoria, pipeline, interioridades del addon

## Apoyar el desarrollo

BabelChat es gratis y seguirá siéndolo. Si te ha salvado un pug, aquí es donde
va el apoyo: cubre las cuotas de traducción que los planes gratuitos no llegan a
cubrir, y el tiempo de desarrollo.

[**Apoyar con tarjeta — SBP, Visa, Mastercard**](https://pay.cloudtips.ru/p/ea5537e6)

| | |
| --- | --- |
| USDT TRC20 | `TGaUz963ZaCoHrfoDDgy1sCvSrK1wsZvcx` |
| BTC | `1BkYvFT8iBVG3GfTqkR2aBkABNkTrhYuja` |
| TON | `UQDFaHBN1pcQZ7_9-w1E_hS_JNfGf3d0flS_467w7LOQ7xbK` |

## Reconocimientos

- **[WoW Translator](https://www.curseforge.com/wow/addons/wow-translator)** de **Pirson** (licencia MIT) — glosario de términos WoW en 14 idiomas. El diccionario de BabelChat está basado en los datos de este addon.

## Autores

- **Andrey Yumashev** — [@Yumash](https://github.com/Yumash) — app acompañante, overlay, lectura de memoria
- **Pirson** — [CurseForge](https://www.curseforge.com/wow/addons/wow-translator) — diccionario WoW y motor de traducción
- **AhegaoZKun** — [@AhegaoZKun](https://github.com/AhegaoZKun) — soporte Linux/Wayland, escáneres de memoria en Rust, backend de Microsoft Translator
- **Claude** (Anthropic) — Co-autor IA

## Licencia

[MIT License](https://github.com/Yumash/BabelChat/blob/main/LICENSE)
