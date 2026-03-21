"""Internationalization — RU/EN/ES UI translations."""

from __future__ import annotations

from typing import ClassVar

# All translatable strings keyed by ID
_STRINGS: dict[str, dict[str, str]] = {
    # ── Setup Wizard ──────────────────────────────────────────
    "wizard.title": {
        "RU": "Настройка BabelChat",
        "EN": "BabelChat Setup",
        "ES": "Configuración de BabelChat",
    },
    "wizard.steps": {
        "RU": "Добро пожаловать|API Ключ|Путь к WoW|Язык|Готово",
        "EN": "Welcome|API Key|WoW Path|Language|Ready",
        "ES": "Bienvenida|Clave API|Ruta de WoW|Idioma|Listo",
    },
    "wizard.step_of": {
        "RU": "Шаг {current} из {total} — {name}",
        "EN": "Step {current} of {total} — {name}",
        "ES": "Paso {current} de {total} — {name}",
    },
    "wizard.cancel": {
        "RU": "Отмена",
        "EN": "Cancel",
        "ES": "Cancelar",
    },
    "wizard.back": {
        "RU": "\u2190 Назад",
        "EN": "\u2190 Back",
        "ES": "\u2190 Atrás",
    },
    "wizard.next": {
        "RU": "Далее \u2192",
        "EN": "Next \u2192",
        "ES": "Siguiente \u2192",
    },
    "wizard.start": {
        "RU": "Запуск \u2713",
        "EN": "Start \u2713",
        "ES": "Iniciar \u2713",
    },

    # Welcome page
    "wizard.welcome.title": {
        "RU": "Добро пожаловать в BabelChat!",
        "EN": "Welcome to BabelChat!",
        "ES": "¡Bienvenido a BabelChat!",
    },
    "wizard.welcome.desc": {
        "RU": (
            "BabelChat — приложение-компаньон, которое\n"
            "переводит чат World of Warcraft в реальном времени.\n\n"
            "Как это работает:\n"
            "1. Мини-аддон включает логирование чата в WoW\n"
            "2. Приложение мониторит файл лога чата\n"
            "3. Сообщения определяются и переводятся через DeepL\n"
            "4. Переводы появляются в оверлее поверх WoW\n\n"
            "Давайте настроим!"
        ),
        "EN": (
            "BabelChat is a companion app that translates\n"
            "World of Warcraft chat in real time.\n\n"
            "How it works:\n"
            "1. A tiny WoW addon enables chat logging\n"
            "2. This app monitors the chat log file\n"
            "3. Messages are auto-detected and translated via DeepL\n"
            "4. Translations appear in a smart overlay on top of WoW\n\n"
            "Let's set it up!"
        ),
        "ES": (
            "BabelChat es una aplicación complementaria que traduce\n"
            "el chat de World of Warcraft en tiempo real.\n\n"
            "Cómo funciona:\n"
            "1. Un pequeño addon de WoW activa el registro del chat\n"
            "2. Esta aplicación monitorea el archivo de registro\n"
            "3. Los mensajes se detectan y traducen automáticamente vía DeepL\n"
            "4. Las traducciones aparecen en una superposición sobre WoW\n\n"
            "¡Vamos a configurarlo!"
        ),
    },
    "wizard.welcome.ui_lang": {
        "RU": "Язык интерфейса:",
        "EN": "Interface language:",
        "ES": "Idioma de interfaz:",
    },

    # API Key page
    "wizard.api.title": {
        "RU": "Ключ DeepL API",
        "EN": "DeepL API Key",
        "ES": "Clave API de DeepL",
    },
    "wizard.api.explain": {
        "RU": (
            "BabelChat использует DeepL — один из лучших сервисов "
            "перевода.\nБесплатный план включает 500 000 символов "
            "в месяц (это ОЧЕНЬ много чата)."
        ),
        "EN": (
            "BabelChat uses DeepL — one of the best translation "
            "services available.\nThe free plan includes 500,000 characters "
            "per month (that's a LOT of chat)."
        ),
        "ES": (
            "BabelChat usa DeepL — uno de los mejores servicios de "
            "traducción disponibles.\nEl plan gratuito incluye 500.000 caracteres "
            "al mes (es MUCHO chat)."
        ),
    },
    "wizard.api.steps": {
        "RU": (
            "Чтобы получить бесплатный API ключ:\n\n"
            "  1. Нажмите ссылку ниже для регистрации на DeepL\n"
            "  2. Создайте бесплатный аккаунт (DeepL API Free)\n"
            "  3. После регистрации откройте страницу API Keys\n"
            "     (нажмите вторую ссылку ниже)\n"
            "  4. Скопируйте ключ (выглядит как: xxxxxxxx-xxxx-...:fx)\n"
            "  5. Вставьте в поле ниже"
        ),
        "EN": (
            "To get your free API key:\n\n"
            "  1. Click the link below to sign up at DeepL\n"
            "  2. Create a free account (DeepL API Free plan)\n"
            "  3. After signup, go to your API Keys page\n"
            "     (click the second link below)\n"
            "  4. Copy your key (looks like: xxxxxxxx-xxxx-...:fx)\n"
            "  5. Paste it in the field below"
        ),
        "ES": (
            "Para obtener su clave API gratuita:\n\n"
            "  1. Haga clic en el enlace de abajo para registrarse en DeepL\n"
            "  2. Cree una cuenta gratuita (plan DeepL API Free)\n"
            "  3. Después de registrarse, vaya a la página de API Keys\n"
            "     (haga clic en el segundo enlace de abajo)\n"
            "  4. Copie su clave (tiene este formato: xxxxxxxx-xxxx-...:fx)\n"
            "  5. Péguela en el campo de abajo"
        ),
    },
    "wizard.api.signup": {
        "RU": "\u2192 1. Зарегистрироваться на DeepL (бесплатно)",
        "EN": "\u2192 1. Sign up at DeepL (free)",
        "ES": "\u2192 1. Registrarse en DeepL (gratis)",
    },
    "wizard.api.keys_link": {
        "RU": "\u2192 2. Открыть страницу API Keys (после регистрации)",
        "EN": "\u2192 2. Open API Keys page (after signup)",
        "ES": "\u2192 2. Abrir página de API Keys (después de registrarse)",
    },
    "wizard.api.placeholder": {
        "RU": "Вставьте ваш DeepL API ключ...",
        "EN": "Paste your DeepL API key here...",
        "ES": "Pegue su clave API de DeepL aquí...",
    },
    "wizard.api.show": {
        "RU": "Показать",
        "EN": "Show",
        "ES": "Mostrar",
    },
    "wizard.api.hide": {
        "RU": "Скрыть",
        "EN": "Hide",
        "ES": "Ocultar",
    },
    "wizard.api.validate": {
        "RU": "Проверить",
        "EN": "Validate Key",
        "ES": "Validar clave",
    },
    "wizard.api.validating": {
        "RU": "Проверка...",
        "EN": "Validating...",
        "ES": "Validando...",
    },
    "wizard.api.no_key": {
        "RU": "API ключ не введён",
        "EN": "No API key entered",
        "ES": "No se ha introducido la clave API",
    },
    "wizard.api.valid": {
        "RU": "Ключ валиден!",
        "EN": "API key valid!",
        "ES": "¡Clave API válida!",
    },
    "wizard.api.valid_usage": {
        "RU": "Ключ валиден! Использование: {count} / {limit} ({pct}%)",
        "EN": "Key valid! Usage: {count} / {limit} ({pct}%)",
        "ES": "¡Clave válida! Uso: {count} / {limit} ({pct}%)",
    },
    "wizard.api.invalid": {
        "RU": "Неверный API ключ",
        "EN": "Invalid API key",
        "ES": "Clave API no válida",
    },
    "wizard.api.error": {
        "RU": "Ошибка подключения: {e}",
        "EN": "Connection error: {e}",
        "ES": "Error de conexión: {e}",
    },

    # WoW Path page
    "wizard.wow.title": {
        "RU": "Расположение World of Warcraft",
        "EN": "World of Warcraft Location",
        "ES": "Ubicación de World of Warcraft",
    },
    "wizard.wow.explain": {
        "RU": (
            "Нужно найти папку WoW для мониторинга\n"
            "файла чат-лога. Попробуем определить автоматически."
        ),
        "EN": (
            "We need to find your WoW installation to monitor\n"
            "the chat log file. We'll try to detect it automatically."
        ),
        "ES": (
            "Necesitamos encontrar su instalación de WoW para monitorear\n"
            "el archivo de registro del chat. Intentaremos detectarlo automáticamente."
        ),
    },
    "wizard.wow.browse": {
        "RU": "Обзор...",
        "EN": "Browse...",
        "ES": "Examinar...",
    },
    "wizard.wow.browse_title": {
        "RU": "Выберите папку WoW",
        "EN": "Select WoW Directory",
        "ES": "Seleccione la carpeta de WoW",
    },
    "wizard.wow.found": {
        "RU": "\u2713 Установка WoW найдена!",
        "EN": "\u2713 WoW installation found!",
        "ES": "\u2713 ¡Instalación de WoW encontrada!",
    },
    "wizard.wow.not_found": {
        "RU": (
            "\u26A0 WoW не найден автоматически. "
            "Укажите путь вручную или пропустите и настройте позже."
        ),
        "EN": (
            "\u26A0 WoW not found automatically. "
            "Please browse to your installation, "
            "or skip and configure later."
        ),
        "ES": (
            "\u26A0 WoW no se encontró automáticamente. "
            "Por favor, busque su instalación manualmente "
            "u omita este paso y configúrelo después."
        ),
    },
    "wizard.wow.path_set": {
        "RU": "\u2713 Путь задан",
        "EN": "\u2713 Path set",
        "ES": "\u2713 Ruta establecida",
    },
    "wizard.wow.skip_hint": {
        "RU": "Можно пропустить и настроить позже\nв Настройках.",
        "EN": "You can skip this step and configure it later\nin Settings.",
        "ES": "Puede omitir este paso y configurarlo después\nen Configuración.",
    },

    # Language page
    "wizard.lang.title": {
        "RU": "Выберите языки",
        "EN": "Choose Your Languages",
        "ES": "Elija sus idiomas",
    },
    "wizard.lang.own": {
        "RU": "На каком языке вы говорите?",
        "EN": "What language do you speak?",
        "ES": "¿Qué idioma habla usted?",
    },
    "wizard.lang.target": {
        "RU": "Переводить сообщения на:",
        "EN": "Translate messages to:",
        "ES": "Traducir mensajes a:",
    },
    "wizard.lang.hint": {
        "RU": (
            "Сообщения на вашем языке не будут переводиться.\n"
            "Всё остальное будет переведено на целевой язык."
        ),
        "EN": (
            "Messages in your language won't be translated.\n"
            "Everything else will be translated to your target language."
        ),
        "ES": (
            "Los mensajes en su idioma no se traducirán.\n"
            "Todo lo demás se traducirá al idioma de destino."
        ),
    },

    # Ready page
    "wizard.ready.title": {
        "RU": "\u2713 Всё готово!",
        "EN": "\u2713 You're all set!",
        "ES": "\u2713 ¡Todo listo!",
    },
    "wizard.ready.addon_group": {
        "RU": "Аддон WoW",
        "EN": "WoW Addon",
        "ES": "Addon de WoW",
    },
    "wizard.ready.addon_text": {
        "RU": (
            "Мини-аддон автоматически включает логирование чата, "
            "чтобы переводчик мог читать сообщения."
        ),
        "EN": (
            "The tiny addon auto-enables chat logging so the "
            "translator can read your messages."
        ),
        "ES": (
            "El pequeño addon activa automáticamente el registro del chat "
            "para que el traductor pueda leer los mensajes."
        ),
    },
    "wizard.ready.install_addon": {
        "RU": "Установить аддон",
        "EN": "Install Addon",
        "ES": "Instalar addon",
    },
    "wizard.ready.reinstall_addon": {
        "RU": "Переустановить аддон",
        "EN": "Reinstall Addon",
        "ES": "Reinstalar addon",
    },
    "wizard.ready.addon_no_path": {
        "RU": "\u2717 Путь к WoW не задан — вернитесь и настройте",
        "EN": "\u2717 WoW path not set — go back and configure it",
        "ES": "\u2717 Ruta de WoW no establecida — vuelva atrás y configúrela",
    },
    "wizard.ready.addon_path_not_found": {
        "RU": "\u2717 Путь не найден: {path}",
        "EN": "\u2717 Path not found: {path}",
        "ES": "\u2717 Ruta no encontrada: {path}",
    },
    "wizard.ready.addon_files_missing": {
        "RU": "\u2717 Файлы аддона не найдены",
        "EN": "\u2717 Addon files not found in app directory",
        "ES": "\u2717 Archivos del addon no encontrados en el directorio de la aplicación",
    },
    "wizard.ready.addon_installed": {
        "RU": "\u2713 Установлен в {dest}",
        "EN": "\u2713 Installed to {dest}",
        "ES": "\u2713 Instalado en {dest}",
    },
    "wizard.ready.closing": {
        "RU": (
            "Оверлей появится поверх WoW.\n"
            "ПКМ по иконке в трее — Настройки и О программе."
        ),
        "EN": (
            "The overlay will appear on top of WoW.\n"
            "Right-click the tray icon to access Settings and About."
        ),
        "ES": (
            "La superposición aparecerá sobre WoW.\n"
            "Haga clic derecho en el icono de la bandeja para acceder a Configuración y Acerca de."
        ),
    },
    "wizard.ready.api_key": {
        "RU": "API Ключ:",
        "EN": "API Key:",
        "ES": "Clave API:",
    },
    "wizard.ready.wow_path": {
        "RU": "Путь к WoW:",
        "EN": "WoW Path:",
        "ES": "Ruta de WoW:",
    },
    "wizard.ready.own_lang": {
        "RU": "Ваш язык:",
        "EN": "Your language:",
        "ES": "Su idioma:",
    },
    "wizard.ready.target_lang": {
        "RU": "Переводить на:",
        "EN": "Translate to:",
        "ES": "Traducir a:",
    },
    "wizard.ready.not_configured": {
        "RU": "(не настроено)",
        "EN": "(not configured)",
        "ES": "(no configurado)",
    },

    # ── Settings Dialog ───────────────────────────────────────
    "settings.title": {
        "RU": "Настройки BabelChat",
        "EN": "BabelChat Settings",
        "ES": "Configuración de BabelChat",
    },
    "settings.tab.general": {
        "RU": "Основные",
        "EN": "General",
        "ES": "General",
    },
    "settings.tab.overlay": {
        "RU": "Оверлей",
        "EN": "Overlay",
        "ES": "Overlay",
    },
    "settings.tab.hotkeys": {
        "RU": "Горячие клавиши",
        "EN": "Hotkeys",
        "ES": "Atajos de teclado",
    },
    "settings.tab.about": {
        "RU": "О программе",
        "EN": "About",
        "ES": "Acerca de",
    },
    "settings.save": {
        "RU": "Сохранить",
        "EN": "Save",
        "ES": "Guardar",
    },

    # General tab
    "settings.api_group": {
        "RU": "DeepL API",
        "EN": "DeepL API",
        "ES": "DeepL API",
    },
    "settings.api.placeholder": {
        "RU": "Введите ваш DeepL API ключ...",
        "EN": "Enter your DeepL API key...",
        "ES": "Introduzca su clave API de DeepL...",
    },
    "settings.api.show": {
        "RU": "Показать",
        "EN": "Show",
        "ES": "Mostrar",
    },
    "settings.api.hide": {
        "RU": "Скрыть",
        "EN": "Hide",
        "ES": "Ocultar",
    },
    "settings.api.validate": {
        "RU": "Проверить",
        "EN": "Validate Key",
        "ES": "Validar clave",
    },
    "settings.api.validating": {
        "RU": "Проверка...",
        "EN": "Validating...",
        "ES": "Validando...",
    },
    "settings.api.get_key": {
        "RU": "Получить ключ",
        "EN": "Get API key",
        "ES": "Obtener clave API",
    },
    "settings.api.usage": {
        "RU": "Использование символов",
        "EN": "Character Usage",
        "ES": "Uso de caracteres",
    },
    "settings.api.valid": {
        "RU": "Ключ валиден",
        "EN": "API key valid",
        "ES": "Clave API válida",
    },
    "settings.api.valid_no_data": {
        "RU": "Ключ валиден (нет данных об использовании)",
        "EN": "API key valid (no usage data)",
        "ES": "Clave API válida (sin datos de uso)",
    },
    "settings.api.invalid": {
        "RU": "Неверный API ключ",
        "EN": "Invalid API key",
        "ES": "Clave API no válida",
    },
    "settings.api.error": {
        "RU": "Ошибка подключения: {e}",
        "EN": "Connection error: {e}",
        "ES": "Error de conexión: {e}",
    },
    "settings.api.no_key": {
        "RU": "API ключ не введён",
        "EN": "No API key entered",
        "ES": "No se ha introducido la clave API",
    },
    "settings.api.saved_hint": {
        "RU": "Ключ сохранён — нажмите Проверить",
        "EN": "Key saved — click Validate to check",
        "ES": "Clave guardada — haga clic en Validar para comprobar",
    },
    "settings.api.not_configured": {
        "RU": "API ключ не настроен",
        "EN": "No API key configured",
        "ES": "Clave API no configurada",
    },

    "settings.wow_group": {
        "RU": "World of Warcraft",
        "EN": "World of Warcraft",
        "ES": "World of Warcraft",
    },
    "settings.wow.path": {
        "RU": "Путь к WoW:",
        "EN": "WoW Path:",
        "ES": "Ruta de WoW:",
    },
    "settings.wow.browse": {
        "RU": "Обзор",
        "EN": "Browse",
        "ES": "Examinar",
    },
    "settings.wow.auto": {
        "RU": "Авто",
        "EN": "Auto",
        "ES": "Auto",
    },
    "settings.wow.browse_title": {
        "RU": "Выберите папку WoW",
        "EN": "Select WoW Directory",
        "ES": "Seleccione la carpeta de WoW",
    },
    "settings.wow.chatlog": {
        "RU": "Файл лога:",
        "EN": "Chat Log:",
        "ES": "Registro del chat:",
    },
    "settings.wow.chatlog_placeholder": {
        "RU": "Определяется автоматически из пути WoW",
        "EN": "Auto-detected from WoW path",
        "ES": "Detectado automáticamente desde la ruta de WoW",
    },
    "settings.wow.install_addon": {
        "RU": "Установить аддон в WoW",
        "EN": "Install Addon to WoW",
        "ES": "Instalar addon en WoW",
    },
    "settings.wow.reinstall_addon": {
        "RU": "Переустановить аддон",
        "EN": "Reinstall Addon",
        "ES": "Reinstalar addon",
    },
    "settings.wow.addon_no_path": {
        "RU": "\u2717 Укажите путь к WoW",
        "EN": "\u2717 Set WoW path first",
        "ES": "\u2717 Establezca primero la ruta de WoW",
    },
    "settings.wow.addon_not_found": {
        "RU": "\u2717 Не найден: {path}",
        "EN": "\u2717 Not found: {path}",
        "ES": "\u2717 No encontrado: {path}",
    },
    "settings.wow.addon_files_missing": {
        "RU": "\u2717 Файлы аддона не найдены",
        "EN": "\u2717 Addon files not found",
        "ES": "\u2717 Archivos del addon no encontrados",
    },
    "settings.wow.addon_installed": {
        "RU": "\u2713 Установлен!",
        "EN": "\u2713 Installed!",
        "ES": "\u2713 ¡Instalado!",
    },

    "settings.lang_group": {
        "RU": "Языки",
        "EN": "Languages",
        "ES": "Idiomas",
    },
    "settings.lang.own": {
        "RU": "Мой язык:",
        "EN": "My language:",
        "ES": "Mi idioma:",
    },
    "settings.lang.target": {
        "RU": "Переводить на:",
        "EN": "Translate to:",
        "ES": "Traducir a:",
    },
    "settings.lang.ui": {
        "RU": "Интерфейс:",
        "EN": "Interface:",
        "ES": "Interfaz:",
    },

    "settings.channels_group": {
        "RU": "Каналы для перевода",
        "EN": "Channels to translate",
        "ES": "Canales a traducir",
    },
    "settings.ch.party": {
        "RU": "Группа",
        "EN": "Party",
        "ES": "Grupo",
    },
    "settings.ch.raid": {
        "RU": "Рейд",
        "EN": "Raid",
        "ES": "Banda",
    },
    "settings.ch.guild": {
        "RU": "Гильдия",
        "EN": "Guild",
        "ES": "Hermandad",
    },
    "settings.ch.say": {
        "RU": "Сказать / Крик",
        "EN": "Say / Yell",
        "ES": "Decir / Gritar",
    },
    "settings.ch.whisper": {
        "RU": "Шёпот",
        "EN": "Whisper",
        "ES": "Susurro",
    },
    "settings.ch.instance": {
        "RU": "Подземелье",
        "EN": "Instance",
        "ES": "Mazmorra",
    },

    # Overlay tab
    "settings.appearance_group": {
        "RU": "Внешний вид",
        "EN": "Appearance",
        "ES": "Apariencia",
    },
    "settings.overlay.opacity": {
        "RU": "Прозрачность:",
        "EN": "Opacity:",
        "ES": "Opacidad:",
    },
    "settings.overlay.font_size": {
        "RU": "Размер шрифта:",
        "EN": "Font size:",
        "ES": "Tamaño de fuente:",
    },
    "settings.behavior_group": {
        "RU": "Поведение",
        "EN": "Behavior",
        "ES": "Comportamiento",
    },
    "settings.overlay.translate_default": {
        "RU": "Перевод ВКЛ по умолчанию",
        "EN": "Translation ON by default",
        "ES": "Traducción activada por defecto",
    },
    "settings.overlay.skip_own_messages": {
        "RU": "Не переводить свои сообщения",
        "EN": "Don't translate own messages",
        "ES": "No traducir mis mensajes",
    },
    "settings.overlay.show_console": {
        "RU": "Показывать окно отладки (консоль)",
        "EN": "Show debug console",
        "ES": "Mostrar consola de depuración",
    },

    # Hotkeys tab
    "settings.hk_group": {
        "RU": "Горячие клавиши",
        "EN": "Hotkeys",
        "ES": "Atajos de teclado",
    },
    "settings.hk.toggle_translate": {
        "RU": "Перевод вкл/выкл:",
        "EN": "Toggle translate:",
        "ES": "Activar/desactivar traducción:",
    },
    "settings.hk.toggle_translate_hint": {
        "RU": "Показать/скрыть переводы в оверлее",
        "EN": "Show/hide translations in the overlay",
        "ES": "Mostrar/ocultar traducciones en el overlay",
    },
    "settings.hk.toggle_interactive": {
        "RU": "Интерактивный режим:",
        "EN": "Toggle interactive:",
        "ES": "Modo interactivo:",
    },
    "settings.hk.toggle_interactive_hint": {
        "RU": "Переключить оверлей между прозрачным и интерактивным режимом",
        "EN": "Switch overlay between click-through and interactive mode",
        "ES": "Cambiar overlay entre modo transparente e interactivo",
    },
    "settings.hk.clipboard": {
        "RU": "Перевод из буфера:",
        "EN": "Clipboard translate:",
        "ES": "Traducir portapapeles:",
    },
    "settings.hk.clipboard_hint": {
        "RU": "Перевести текст из буфера обмена и скопировать результат",
        "EN": "Translate clipboard text and copy result back",
        "ES": "Traducir texto del portapapeles y copiar el resultado",
    },
    "settings.hk.change": {
        "RU": "Изменить",
        "EN": "Change",
        "ES": "Cambiar",
    },
    "settings.hk.cancel": {
        "RU": "Отмена",
        "EN": "Cancel",
        "ES": "Cancelar",
    },
    "settings.hk.clear": {
        "RU": "Сброс",
        "EN": "Clear",
        "ES": "Borrar",
    },
    "settings.hk.press_keys": {
        "RU": "Нажмите клавиши...",
        "EN": "Press keys...",
        "ES": "Pulse las teclas...",
    },
    "settings.hk.none": {
        "RU": "(нет)",
        "EN": "(none)",
        "ES": "(ninguno)",
    },

    # ── Tray ──────────────────────────────────────────────────
    "tray.hide_overlay": {
        "RU": "Скрыть оверлей",
        "EN": "Hide Overlay",
        "ES": "Ocultar overlay",
    },
    "tray.show_overlay": {
        "RU": "Показать оверлей",
        "EN": "Show Overlay",
        "ES": "Mostrar overlay",
    },
    "tray.toggle_translation": {
        "RU": "Перевод вкл/выкл",
        "EN": "Toggle Translation",
        "ES": "Activar/desactivar traducción",
    },
    "tray.lock_overlay": {
        "RU": "Закрепить оверлей",
        "EN": "Lock Overlay",
        "ES": "Bloquear overlay",
    },
    "tray.unlock_overlay": {
        "RU": "Открепить оверлей",
        "EN": "Unlock Overlay",
        "ES": "Desbloquear overlay",
    },
    "tray.settings": {
        "RU": "Настройки",
        "EN": "Settings",
        "ES": "Configuración",
    },
    "tray.about": {
        "RU": "О программе",
        "EN": "About",
        "ES": "Acerca de",
    },
    "tray.quit": {
        "RU": "Выход",
        "EN": "Quit",
        "ES": "Salir",
    },

    # ── Overlay ───────────────────────────────────────────────
    "overlay.settings": {
        "RU": "\u2699 Настройки",
        "EN": "\u2699 Settings",
        "ES": "\u2699 Configuración",
    },
    "overlay.opacity": {
        "RU": "Прозрачность:",
        "EN": "Opacity:",
        "ES": "Opacidad:",
    },
    "overlay.lock": {
        "RU": "\U0001F512 Закрепить",
        "EN": "\U0001F512 Lock",
        "ES": "\U0001F512 Bloquear",
    },
    "overlay.unlock": {
        "RU": "\U0001F513 Открепить",
        "EN": "\U0001F513 Unlock",
        "ES": "\U0001F513 Desbloquear",
    },
    "overlay.quit": {
        "RU": "\u2716 Выход",
        "EN": "\u2716 Quit",
        "ES": "\u2716 Salir",
    },
    "overlay.locked": {
        "RU": "ЗАКРЕПЛЁН",
        "EN": "LOCKED",
        "ES": "BLOQUEADO",
    },
    "overlay.unlocked": {
        "RU": "СВОБОДНЫЙ",
        "EN": "UNLOCKED",
        "ES": "DESBLOQUEADO",
    },
    "overlay.filter.all": {
        "RU": "Все",
        "EN": "All",
        "ES": "Todos",
    },
    "overlay.filter.party": {
        "RU": "Группа",
        "EN": "Party",
        "ES": "Grupo",
    },
    "overlay.filter.raid": {
        "RU": "Рейд",
        "EN": "Raid",
        "ES": "Banda",
    },
    "overlay.filter.guild": {
        "RU": "Гильдия",
        "EN": "Guild",
        "ES": "Hermandad",
    },
    "overlay.filter.say": {
        "RU": "Сказать",
        "EN": "Say",
        "ES": "Decir",
    },
    "overlay.filter.whisper": {
        "RU": "Шёпот",
        "EN": "Whisper",
        "ES": "Susurro",
    },
    "overlay.filter.instance": {
        "RU": "Подземелье",
        "EN": "Instance",
        "ES": "Mazmorra",
    },

    # Reply translator
    "overlay.reply.toggle": {
        "RU": "Перевести",
        "EN": "Translate",
        "ES": "Traducir",
    },
    "overlay.reply.placeholder": {
        "RU": "Введите сообщение...",
        "EN": "Type message...",
        "ES": "Escriba un mensaje...",
    },
    "overlay.reply.copy": {
        "RU": "Копировать",
        "EN": "Copy",
        "ES": "Copiar",
    },
    "overlay.reply.copied": {
        "RU": "Скопировано!",
        "EN": "Copied!",
        "ES": "¡Copiado!",
    },
    "overlay.reply.translating": {
        "RU": "Перевод...",
        "EN": "Translating...",
        "ES": "Traduciendo...",
    },
    "overlay.reply.error": {
        "RU": "Ошибка перевода",
        "EN": "Translation error",
        "ES": "Error de traducción",
    },
    "overlay.reply.input_hint": {
        "RU": "Введите сообщение... (Enter — перевести)",
        "EN": "Type message... (Enter to translate)",
        "ES": "Escriba un mensaje... (Enter para traducir)",
    },

    # ── About Dialog ──────────────────────────────────────────
    "about.title": {
        "RU": "О программе",
        "EN": "About BabelChat",
        "ES": "Acerca de BabelChat",
    },
    "about.subtitle": {
        "RU": "Переводчик чата WoW в реальном времени",
        "EN": "Real-time WoW chat translator",
        "ES": "Traductor de chat de WoW en tiempo real",
    },
    "about.developer": {
        "RU": "Разработчик:",
        "EN": "Developer:",
        "ES": "Desarrollador:",
    },
    "about.license": {
        "RU": "Лицензия: MIT",
        "EN": "License: MIT",
        "ES": "Licencia: MIT",
    },
    "about.glossary_credit": {
        "RU": 'Глоссарий терминов: <a href="https://www.curseforge.com/wow/addons/wow-translator" style="color: #FFD200;">WoW Translator</a> by Pirson',
        "EN": 'Term glossary: <a href="https://www.curseforge.com/wow/addons/wow-translator" style="color: #FFD200;">WoW Translator</a> by Pirson',
        "ES": 'Glosario de términos: <a href="https://www.curseforge.com/wow/addons/wow-translator" style="color: #FFD200;">WoW Translator</a> by Pirson',
    },
    "about.close": {
        "RU": "Закрыть",
        "EN": "Close",
        "ES": "Cerrar",
    },
    "about.donate": {
        "RU": "Поддержать проект",
        "EN": "Support the project",
        "ES": "Apoyar el proyecto",
    },
    "about.donate_dictionary": {
        "RU": "Словарь WoW терминов — Pirson",
        "EN": "WoW Term Dictionary — Pirson",
        "ES": "Diccionario de términos WoW — Pirson",
    },
    "about.donate_dictionary_desc": {
        "RU": "Идея внутриигрового перевода и словарь 314 терминов на 14 языках",
        "EN": "In-game translation idea and dictionary of 314 terms in 14 languages",
        "ES": "Idea de traducción en el juego y diccionario de 314 términos en 14 idiomas",
    },
    "about.donate_app": {
        "RU": "Приложение-компаньон — Andrey Yumashev",
        "EN": "Companion App — Andrey Yumashev",
        "ES": "Aplicación acompañante — Andrey Yumashev",
    },
    "about.donate_app_desc": {
        "RU": "Оверлей, перевод DeepL, чтение памяти, стриминг",
        "EN": "Overlay, DeepL translation, memory reader, streaming",
        "ES": "Overlay, traducción DeepL, lectura de memoria, streaming",
    },
    "overlay.session_start": {
        "RU": "новая сессия",
        "EN": "new session",
        "ES": "nueva sesión",
    },
}

# UI language options
UI_LANGUAGES = {"RU": "Русский", "EN": "English", "ES": "Español"}


class tr:
    """Simple translation helper. Call tr("key") to get localized string."""

    _lang: ClassVar[str] = "RU"

    @classmethod
    def set_language(cls, lang: str) -> None:
        cls._lang = lang if lang in ("RU", "EN", "ES") else "RU"

    @classmethod
    def get_language(cls) -> str:
        return cls._lang

    @classmethod
    def __class_getitem__(cls, key: str) -> str:
        """Allow tr["key"] syntax."""
        return cls(key)

    def __new__(cls, key: str, **kwargs: object) -> str:  # type: ignore[misc]
        entry = _STRINGS.get(key)
        if not entry:
            return key
        text = entry.get(cls._lang, entry.get("EN", key))
        if kwargs:
            text = text.format(**kwargs)
        return text
