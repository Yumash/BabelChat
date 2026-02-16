"""Internationalization — RU/EN UI translations."""

from __future__ import annotations

from typing import ClassVar

# All translatable strings keyed by ID
_STRINGS: dict[str, dict[str, str]] = {
    # ── Setup Wizard ──────────────────────────────────────────
    "wizard.title": {
        "RU": "Настройка WoWTranslator",
        "EN": "WoWTranslator Setup",
    },
    "wizard.steps": {
        "RU": "Добро пожаловать|API Ключ|Путь к WoW|Язык|Готово",
        "EN": "Welcome|API Key|WoW Path|Language|Ready",
    },
    "wizard.step_of": {
        "RU": "Шаг {current} из {total} — {name}",
        "EN": "Step {current} of {total} — {name}",
    },
    "wizard.cancel": {"RU": "Отмена", "EN": "Cancel"},
    "wizard.back": {"RU": "\u2190 Назад", "EN": "\u2190 Back"},
    "wizard.next": {"RU": "Далее \u2192", "EN": "Next \u2192"},
    "wizard.start": {"RU": "Запуск \u2713", "EN": "Start \u2713"},

    # Welcome page
    "wizard.welcome.title": {
        "RU": "Добро пожаловать в WoWTranslator!",
        "EN": "Welcome to WoWTranslator!",
    },
    "wizard.welcome.desc": {
        "RU": (
            "WoWTranslator — приложение-компаньон, которое\n"
            "переводит чат World of Warcraft в реальном времени.\n\n"
            "Как это работает:\n"
            "1. Мини-аддон включает логирование чата в WoW\n"
            "2. Приложение мониторит файл лога чата\n"
            "3. Сообщения определяются и переводятся через DeepL\n"
            "4. Переводы появляются в оверлее поверх WoW\n\n"
            "Давайте настроим!"
        ),
        "EN": (
            "WoWTranslator is a companion app that translates\n"
            "World of Warcraft chat in real time.\n\n"
            "How it works:\n"
            "1. A tiny WoW addon enables chat logging\n"
            "2. This app monitors the chat log file\n"
            "3. Messages are auto-detected and translated via DeepL\n"
            "4. Translations appear in a smart overlay on top of WoW\n\n"
            "Let's set it up!"
        ),
    },
    "wizard.welcome.ui_lang": {
        "RU": "Язык интерфейса:",
        "EN": "Interface language:",
    },

    # API Key page
    "wizard.api.title": {"RU": "Ключ DeepL API", "EN": "DeepL API Key"},
    "wizard.api.explain": {
        "RU": (
            "WoWTranslator использует DeepL — один из лучших сервисов "
            "перевода.\nБесплатный план включает 500 000 символов "
            "в месяц (это ОЧЕНЬ много чата)."
        ),
        "EN": (
            "WoWTranslator uses DeepL — one of the best translation "
            "services available.\nThe free plan includes 500,000 characters "
            "per month (that's a LOT of chat)."
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
    },
    "wizard.api.signup": {
        "RU": "\u2192 1. Зарегистрироваться на DeepL (бесплатно)",
        "EN": "\u2192 1. Sign up at DeepL (free)",
    },
    "wizard.api.keys_link": {
        "RU": "\u2192 2. Открыть страницу API Keys (после регистрации)",
        "EN": "\u2192 2. Open API Keys page (after signup)",
    },
    "wizard.api.placeholder": {
        "RU": "Вставьте ваш DeepL API ключ...",
        "EN": "Paste your DeepL API key here...",
    },
    "wizard.api.show": {"RU": "Показать", "EN": "Show"},
    "wizard.api.hide": {"RU": "Скрыть", "EN": "Hide"},
    "wizard.api.validate": {"RU": "Проверить", "EN": "Validate Key"},
    "wizard.api.validating": {"RU": "Проверка...", "EN": "Validating..."},
    "wizard.api.no_key": {"RU": "API ключ не введён", "EN": "No API key entered"},
    "wizard.api.valid": {"RU": "Ключ валиден!", "EN": "API key valid!"},
    "wizard.api.valid_usage": {
        "RU": "Ключ валиден! Использование: {count} / {limit} ({pct}%)",
        "EN": "Key valid! Usage: {count} / {limit} ({pct}%)",
    },
    "wizard.api.invalid": {"RU": "Неверный API ключ", "EN": "Invalid API key"},
    "wizard.api.error": {
        "RU": "Ошибка подключения: {e}",
        "EN": "Connection error: {e}",
    },

    # WoW Path page
    "wizard.wow.title": {
        "RU": "Расположение World of Warcraft",
        "EN": "World of Warcraft Location",
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
    },
    "wizard.wow.browse": {"RU": "Обзор...", "EN": "Browse..."},
    "wizard.wow.browse_title": {
        "RU": "Выберите папку WoW",
        "EN": "Select WoW Directory",
    },
    "wizard.wow.found": {
        "RU": "\u2713 Установка WoW найдена!",
        "EN": "\u2713 WoW installation found!",
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
    },
    "wizard.wow.path_set": {"RU": "\u2713 Путь задан", "EN": "\u2713 Path set"},
    "wizard.wow.skip_hint": {
        "RU": "Можно пропустить и настроить позже\nв Настройках.",
        "EN": "You can skip this step and configure it later\nin Settings.",
    },

    # Language page
    "wizard.lang.title": {"RU": "Выберите языки", "EN": "Choose Your Languages"},
    "wizard.lang.own": {
        "RU": "На каком языке вы говорите?",
        "EN": "What language do you speak?",
    },
    "wizard.lang.target": {
        "RU": "Переводить сообщения на:",
        "EN": "Translate messages to:",
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
    },

    # Ready page
    "wizard.ready.title": {
        "RU": "\u2713 Всё готово!",
        "EN": "\u2713 You're all set!",
    },
    "wizard.ready.addon_group": {"RU": "Аддон WoW", "EN": "WoW Addon"},
    "wizard.ready.addon_text": {
        "RU": (
            "Мини-аддон автоматически включает логирование чата, "
            "чтобы переводчик мог читать сообщения."
        ),
        "EN": (
            "The tiny addon auto-enables chat logging so the "
            "translator can read your messages."
        ),
    },
    "wizard.ready.install_addon": {
        "RU": "Установить аддон",
        "EN": "Install Addon",
    },
    "wizard.ready.reinstall_addon": {
        "RU": "Переустановить аддон",
        "EN": "Reinstall Addon",
    },
    "wizard.ready.addon_no_path": {
        "RU": "\u2717 Путь к WoW не задан — вернитесь и настройте",
        "EN": "\u2717 WoW path not set — go back and configure it",
    },
    "wizard.ready.addon_path_not_found": {
        "RU": "\u2717 Путь не найден: {path}",
        "EN": "\u2717 Path not found: {path}",
    },
    "wizard.ready.addon_files_missing": {
        "RU": "\u2717 Файлы аддона не найдены",
        "EN": "\u2717 Addon files not found in app directory",
    },
    "wizard.ready.addon_installed": {
        "RU": "\u2713 Установлен в {dest}",
        "EN": "\u2713 Installed to {dest}",
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
    },
    "wizard.ready.api_key": {"RU": "API Ключ:", "EN": "API Key:"},
    "wizard.ready.wow_path": {"RU": "Путь к WoW:", "EN": "WoW Path:"},
    "wizard.ready.own_lang": {"RU": "Ваш язык:", "EN": "Your language:"},
    "wizard.ready.target_lang": {"RU": "Переводить на:", "EN": "Translate to:"},
    "wizard.ready.not_configured": {
        "RU": "(не настроено)",
        "EN": "(not configured)",
    },

    # ── Settings Dialog ───────────────────────────────────────
    "settings.title": {
        "RU": "Настройки WoWTranslator",
        "EN": "WoWTranslator Settings",
    },
    "settings.tab.general": {"RU": "Основные", "EN": "General"},
    "settings.tab.overlay": {"RU": "Оверлей", "EN": "Overlay"},
    "settings.tab.hotkeys": {"RU": "Горячие клавиши", "EN": "Hotkeys"},
    "settings.save": {"RU": "Сохранить", "EN": "Save"},

    # General tab
    "settings.api_group": {"RU": "DeepL API", "EN": "DeepL API"},
    "settings.api.placeholder": {
        "RU": "Введите ваш DeepL API ключ...",
        "EN": "Enter your DeepL API key...",
    },
    "settings.api.show": {"RU": "Показать", "EN": "Show"},
    "settings.api.hide": {"RU": "Скрыть", "EN": "Hide"},
    "settings.api.validate": {"RU": "Проверить", "EN": "Validate Key"},
    "settings.api.validating": {"RU": "Проверка...", "EN": "Validating..."},
    "settings.api.get_key": {"RU": "Получить ключ", "EN": "Get API key"},
    "settings.api.usage": {"RU": "Использование символов", "EN": "Character Usage"},
    "settings.api.valid": {"RU": "Ключ валиден", "EN": "API key valid"},
    "settings.api.valid_no_data": {
        "RU": "Ключ валиден (нет данных об использовании)",
        "EN": "API key valid (no usage data)",
    },
    "settings.api.invalid": {"RU": "Неверный API ключ", "EN": "Invalid API key"},
    "settings.api.error": {
        "RU": "Ошибка подключения: {e}",
        "EN": "Connection error: {e}",
    },
    "settings.api.no_key": {
        "RU": "API ключ не введён",
        "EN": "No API key entered",
    },
    "settings.api.saved_hint": {
        "RU": "Ключ сохранён — нажмите Проверить",
        "EN": "Key saved — click Validate to check",
    },
    "settings.api.not_configured": {
        "RU": "API ключ не настроен",
        "EN": "No API key configured",
    },

    "settings.wow_group": {"RU": "World of Warcraft", "EN": "World of Warcraft"},
    "settings.wow.path": {"RU": "Путь к WoW:", "EN": "WoW Path:"},
    "settings.wow.browse": {"RU": "Обзор", "EN": "Browse"},
    "settings.wow.auto": {"RU": "Авто", "EN": "Auto"},
    "settings.wow.browse_title": {
        "RU": "Выберите папку WoW",
        "EN": "Select WoW Directory",
    },
    "settings.wow.chatlog": {"RU": "Файл лога:", "EN": "Chat Log:"},
    "settings.wow.chatlog_placeholder": {
        "RU": "Определяется автоматически из пути WoW",
        "EN": "Auto-detected from WoW path",
    },
    "settings.wow.install_addon": {
        "RU": "Установить аддон в WoW",
        "EN": "Install Addon to WoW",
    },
    "settings.wow.reinstall_addon": {
        "RU": "Переустановить аддон",
        "EN": "Reinstall Addon",
    },
    "settings.wow.addon_no_path": {
        "RU": "\u2717 Укажите путь к WoW",
        "EN": "\u2717 Set WoW path first",
    },
    "settings.wow.addon_not_found": {
        "RU": "\u2717 Не найден: {path}",
        "EN": "\u2717 Not found: {path}",
    },
    "settings.wow.addon_files_missing": {
        "RU": "\u2717 Файлы аддона не найдены",
        "EN": "\u2717 Addon files not found",
    },
    "settings.wow.addon_installed": {
        "RU": "\u2713 Установлен!",
        "EN": "\u2713 Installed!",
    },

    "settings.lang_group": {"RU": "Языки", "EN": "Languages"},
    "settings.lang.own": {"RU": "Мой язык:", "EN": "My language:"},
    "settings.lang.target": {"RU": "Переводить на:", "EN": "Translate to:"},
    "settings.lang.ui": {"RU": "Интерфейс:", "EN": "Interface:"},

    "settings.channels_group": {
        "RU": "Каналы для перевода",
        "EN": "Channels to translate",
    },
    "settings.ch.party": {"RU": "Группа", "EN": "Party"},
    "settings.ch.raid": {"RU": "Рейд", "EN": "Raid"},
    "settings.ch.guild": {"RU": "Гильдия", "EN": "Guild"},
    "settings.ch.say": {"RU": "Сказать / Крик", "EN": "Say / Yell"},
    "settings.ch.whisper": {"RU": "Шёпот", "EN": "Whisper"},
    "settings.ch.instance": {"RU": "Подземелье", "EN": "Instance"},

    # Overlay tab
    "settings.appearance_group": {"RU": "Внешний вид", "EN": "Appearance"},
    "settings.overlay.opacity": {"RU": "Прозрачность:", "EN": "Opacity:"},
    "settings.overlay.font_size": {"RU": "Размер шрифта:", "EN": "Font size:"},
    "settings.behavior_group": {"RU": "Поведение", "EN": "Behavior"},
    "settings.overlay.translate_default": {
        "RU": "Перевод ВКЛ по умолчанию",
        "EN": "Translation ON by default",
    },

    # Hotkeys tab
    "settings.hk_group": {"RU": "Горячие клавиши", "EN": "Hotkeys"},
    "settings.hk.toggle_translate": {
        "RU": "Перевод вкл/выкл:",
        "EN": "Toggle translate:",
    },
    "settings.hk.toggle_translate_hint": {
        "RU": "Показать/скрыть переводы в оверлее",
        "EN": "Show/hide translations in the overlay",
    },
    "settings.hk.toggle_interactive": {
        "RU": "Интерактивный режим:",
        "EN": "Toggle interactive:",
    },
    "settings.hk.toggle_interactive_hint": {
        "RU": "Переключить оверлей между прозрачным и интерактивным режимом",
        "EN": "Switch overlay between click-through and interactive mode",
    },
    "settings.hk.clipboard": {
        "RU": "Перевод из буфера:",
        "EN": "Clipboard translate:",
    },
    "settings.hk.clipboard_hint": {
        "RU": "Перевести текст из буфера обмена и скопировать результат",
        "EN": "Translate clipboard text and copy result back",
    },
    "settings.hk.change": {"RU": "Изменить", "EN": "Change"},
    "settings.hk.cancel": {"RU": "Отмена", "EN": "Cancel"},
    "settings.hk.clear": {"RU": "Сброс", "EN": "Clear"},
    "settings.hk.press_keys": {"RU": "Нажмите клавиши...", "EN": "Press keys..."},
    "settings.hk.none": {"RU": "(нет)", "EN": "(none)"},

    # ── Tray ──────────────────────────────────────────────────
    "tray.hide_overlay": {"RU": "Скрыть оверлей", "EN": "Hide Overlay"},
    "tray.show_overlay": {"RU": "Показать оверлей", "EN": "Show Overlay"},
    "tray.toggle_translation": {
        "RU": "Перевод вкл/выкл",
        "EN": "Toggle Translation",
    },
    "tray.lock_overlay": {"RU": "Закрепить оверлей", "EN": "Lock Overlay"},
    "tray.unlock_overlay": {"RU": "Открепить оверлей", "EN": "Unlock Overlay"},
    "tray.settings": {"RU": "Настройки", "EN": "Settings"},
    "tray.about": {"RU": "О программе", "EN": "About"},
    "tray.quit": {"RU": "Выход", "EN": "Quit"},

    # ── Overlay ───────────────────────────────────────────────
    "overlay.settings": {"RU": "\u2699 Настройки", "EN": "\u2699 Settings"},
    "overlay.opacity": {"RU": "Прозрачность:", "EN": "Opacity:"},
    "overlay.lock": {"RU": "\U0001F512 Закрепить", "EN": "\U0001F512 Lock"},
    "overlay.unlock": {"RU": "\U0001F513 Открепить", "EN": "\U0001F513 Unlock"},
    "overlay.quit": {"RU": "\u2716 Выход", "EN": "\u2716 Quit"},
    "overlay.locked": {"RU": "ЗАКРЕПЛЁН", "EN": "LOCKED"},
    "overlay.unlocked": {"RU": "СВОБОДНЫЙ", "EN": "UNLOCKED"},
    "overlay.filter.all": {"RU": "Все", "EN": "All"},
    "overlay.filter.party": {"RU": "Группа", "EN": "Party"},
    "overlay.filter.raid": {"RU": "Рейд", "EN": "Raid"},
    "overlay.filter.guild": {"RU": "Гильдия", "EN": "Guild"},
    "overlay.filter.say": {"RU": "Сказать", "EN": "Say"},
    "overlay.filter.whisper": {"RU": "Шёпот", "EN": "Whisper"},
    "overlay.filter.instance": {"RU": "Подземелье", "EN": "Instance"},

    # Reply translator
    "overlay.reply.toggle": {"RU": "Перевести", "EN": "Translate"},
    "overlay.reply.placeholder": {
        "RU": "Введите сообщение...",
        "EN": "Type message...",
    },
    "overlay.reply.copy": {"RU": "Копировать", "EN": "Copy"},
    "overlay.reply.copied": {"RU": "Скопировано!", "EN": "Copied!"},
    "overlay.reply.translating": {"RU": "Перевод...", "EN": "Translating..."},
    "overlay.reply.error": {"RU": "Ошибка перевода", "EN": "Translation error"},
    "overlay.reply.input_hint": {
        "RU": "Введите сообщение... (Enter — перевести)",
        "EN": "Type message... (Enter to translate)",
    },

    # ── About Dialog ──────────────────────────────────────────
    "about.title": {"RU": "О программе", "EN": "About WoWTranslator"},
    "about.subtitle": {
        "RU": "Переводчик чата WoW в реальном времени",
        "EN": "Real-time WoW chat translator",
    },
    "about.developer": {"RU": "Разработчик:", "EN": "Developer:"},
    "about.license": {"RU": "Лицензия: GPL-3.0", "EN": "License: GPL-3.0"},
    "about.guild_credit": {
        "RU": "\u2694 Сделано с любовью и поддержкой лучшей гильдии WoW",
        "EN": "\u2694 Made with love and support of the best WoW guild",
    },
    "about.close": {"RU": "Закрыть", "EN": "Close"},
    "overlay.session_start": {"RU": "новая сессия", "EN": "new session"},
}

# UI language options
UI_LANGUAGES = {"RU": "Русский", "EN": "English"}


class tr:
    """Simple translation helper. Call tr("key") to get localized string."""

    _lang: ClassVar[str] = "RU"

    @classmethod
    def set_language(cls, lang: str) -> None:
        cls._lang = lang if lang in ("RU", "EN") else "RU"

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
