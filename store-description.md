# BabelChat

**Chat in a language you don't read, translated where you're already looking.**

---

## What it does

Someone types this in Trade:

> `wtb gilded crest, cod`

BabelChat appends the meaning, in grey, on the same line:

> `wtb gilded crest, cod`&nbsp;&nbsp;`wtb = Куплю · gilded = Золочёная эмблема · crest = Эмблема +1`

No second line, no colour spam, no arrows. The original stays readable, copy-chat
still works, and a busy Trade channel stays a Trade channel.

That is the **addon on its own** — 436 gaming terms in 14 languages. No account,
no key, no companion app, nothing to configure.

Add the **free companion app** and whole sentences get translated too, in an
overlay above WoW.

---

## Install and you're done

1. Install the addon.
2. Play.

That's the whole setup. The gloss uses your WoW client's language automatically —
a Russian client gets Russian, a German client gets German.

Want to change something? `/babel config`.

---

## Full-sentence translation (optional)

Grab the companion app from [GitHub](https://github.com/Yumash/BabelChat). It
reads the addon's chat buffer out of the game's memory and shows translations in
an overlay. It only reads — nothing is written, injected or automated — but
reading the game's memory is not something Blizzard's EULA permits, and nobody
outside Blizzard can promise it will never be acted on. The README says exactly
[what it does to the game and what we can't promise](https://github.com/Yumash/BabelChat#what-it-does-to-the-game-and-what-we-cant-promise);
read that before you run it. The addon on its own is an ordinary add-on and
needs none of this.

It needs a translation service. **All four have a free tier**, and you only need
one:

| Service | What it asks for | Free allowance |
|---|---|---|
| **GigaChat** *(default)* | a Sber ID — no card, no VPN, works from Russia ([how to get one](https://github.com/Yumash/BabelChat/blob/main/docs/user/gigachat.md)) | 1M tokens / year |
| **MyMemory** | nothing at all | 5,000 words / day (50,000 with an email) |
| **DeepL** | a card to verify identity — never charged on Free | 500K characters / month |
| **Microsoft Translator** | an Azure account | 2M characters / month |

Configure more than one and they cover for each other: if your preferred service
is down, out of allowance, or declines to translate a particular message, the
next one is tried instead of the message being dropped.

The overlay keeps up with a busy Trade channel: messages appear in the poll they
were sent in, and the companion costs about a tenth of one percent of a core
while it does it. It reads the addon's buffer through a pointer the addon parks
for it, so nothing is scanned for and nothing competes with the game.

**You can also just not configure any of them.** MyMemory needs no account, so
sentence translation works on first launch, and the in-game glossary works
regardless.

---

## What's in the glossary

**436 terms across 13 categories, in 14 languages**, plus every zone and item-set
name from LibBabble.

| Category | Examples | Terms |
|---|---|---|
| Social | ty, gg, brb, wp, omw, cya, pls | 83 |
| Raid & dungeon | wipe, prog, soak, kite, brez, pull, adds | 63 |
| Classes & specs | dk, ret, bm, disc, resto | 59 |
| Slang | ez, copium, bricked, w2w, gogo | 49 |
| Combat | aggro, aoe, cc, dot, purge, arena | 39 |
| Groups | lfm, lf1m, inv, pug, mythic, heroic | 36 |
| Endgame & Midnight | delve, m+, keystone, catalyst, timed, chest | 26 |
| Stats | crit, haste, mastery, vers, mana, parse | 25 |
| Professions | jc, bs, enchant, herb, alch | 17 |
| Status | afk, oom, combat, ooc, bio | 14 |
| Roles | tank, healer, dps, melee, ranged | 11 |
| Trade | wtb, wts, bis, mats, cod, sold | 9 |
| Guild | gm, officer, recruit, gbank | 5 |

**Languages:** English, Russian, Spanish (ES/MX), German, French, Italian,
Portuguese, Polish, Swedish, Norwegian, Korean, Chinese (Simplified &
Traditional).

Each category has its own toggle, so you can switch off the ones you already
know.

---

## Details that matter in practice

- **A Mythic+ key silences chat, and the app says so.** From Midnight on, the
  game hands chat to addons as a secret value while a key is running — no addon
  can read it, this one included. The overlay tells you instead of looking
  broken, and translation returns when the key ends.
- **Item links survive.** Nothing inside a hyperlink or a colour block is ever
  touched, so a linked item name is never half-glossed.
- **Punctuation doesn't hide terms.** `dps/heal`, `gg,wp` and `brb/afk` all
  match — that's how people actually type.
- **Capital letters work.** A sentence starting with `Спс` finds the term `спс`.
- **One entry per term.** `ty ty ty` says `ty = спасибо` once, not three times.
- **In message order**, capped at three terms plus a count, so one chat line
  stays one chat line.
- **The addon goes quiet when the app is running**, so the same message isn't
  answered twice in different words. Override it in `/babel config` if you want
  both.

---

## Commands

| Command | What it does |
|---|---|
| `/babel` | help |
| `/babel config` | settings panel |
| `/babel on` / `off` | glossary on or off |
| `/babel test` | try it on a sample message |
| `/babel companion` | companion buffer status |

---

## Privacy

The addon stores nothing but your settings. The companion app sends message text
to whichever translation service you configured — that's what translation is —
and nothing else leaves your machine. It does not write chat to disk unless you
switch that on yourself, and the checkbox tells you the file will contain other
players' whispers.

Administrator rights are **not** required.

---

## Credits

The glossary began as [WoW Translator](https://www.curseforge.com/wow/addons/wow-translator)
by **Pirson** (MIT), which contributed 314 terms across 14 languages. BabelChat
added slang and a current Endgame/Midnight set, rewrote the matching engine and
the way the gloss reads, and built the companion app.

- **Pirson** — glossary data and the in-game translation idea — [Buy Me a Coffee](https://buymeacoffee.com/franciscorb)
- **Andrey Yumashev** — addon, companion app, translation engine
- **AhegaoZKun** — Linux/Wayland support, Microsoft Translator backend

MIT License.

---
---

# BabelChat · по-русски

**Переводит чат там, куда ты и так смотришь.**

## Как это выглядит

В Торговле пишут:

> `wtb gilded crest, cod`

BabelChat дописывает серым в той же строке:

> `wtb gilded crest, cod`&nbsp;&nbsp;`wtb = Куплю · gilded = Золочёная эмблема · crest = Эмблема +1`

Ни второй строки, ни радуги, ни стрелок. Сообщение читается по-прежнему, чат
копируется, Торговля остаётся Торговлей.

Так работает сам аддон: 436 игровых сокращений на 14 языках. Ему не нужны ни
аккаунт, ни ключи, ни настройка.

Поставь рядом бесплатное приложение-компаньон, и переводиться начнут целые
фразы. Их покажет оверлей поверх игры.

## Поставил и играешь

1. Поставь аддон.
2. Играй.

Язык подсказок аддон возьмёт у клиента сам: на русском клиенте подскажет
по-русски. Остальное настраивается командой `/babel config`.

## Целые фразы, если захочется

Компаньон лежит на [GitHub](https://github.com/Yumash/BabelChat). Он читает
буфер аддона из памяти игры и показывает перевод в оверлее. Только читает: ничего
не пишет, не внедряет и не делает за тебя — но чтение памяти игры лицензионное
соглашение Blizzard не разрешает, и никто снаружи Blizzard не пообещает, что за
это никогда не накажут. В README точно написано,
[что компаньон делает с игрой и чего мы не обещаем](https://github.com/Yumash/BabelChat/blob/main/README_ru.md#что-компаньон-делает-с-игрой-и-чего-мы-не-обещаем);
прочитай это до запуска. Аддон сам по себе — обычный аддон, и ничего из этого ему
не нужно.

Понадобится сервис перевода, любой один из четырёх. Бесплатный тариф есть у всех:

| Сервис | Что просит | Бесплатно |
|---|---|---|
| **GigaChat** *(по умолчанию)* | Sber ID, без карты и без VPN, работает из России ([как получить](https://github.com/Yumash/BabelChat/blob/main/docs/user/gigachat_ru.md)) | 1 млн токенов в год |
| **MyMemory** | ничего | 5 000 слов в день (50 000 с указанным e-mail) |
| **DeepL** | карту для подтверждения личности, на Free не списывает | 500 тыс. символов в месяц |
| **Microsoft Translator** | аккаунт Azure | 2 млн символов в месяц |

Настроишь несколько — подстрахуют друг друга. Основной лёг, исчерпал лимит или
отказался переводить фразу? Компаньон молча возьмёт следующий, и сообщение не
потеряется.

Перевод успевает за живой Торговлей: фраза появляется в оверлее меньше чем через
секунду после отправки, а процессор занят при этом на десятую долю процента.
Искать в памяти игры ничего не приходится: аддон сам кладёт буфер туда, где его
ждут.

Можно и вовсе ничего не настраивать. MyMemory работает без регистрации, поэтому
фразы переводятся с первого запуска. Словарь в игре работает всегда.

## Что в словаре

436 терминов, 13 категорий, 14 языков. Плюс названия зон и комплектов из
LibBabble. Любую категорию можно выключить отдельно.

| Категория | Примеры | Терминов |
|---|---|---|
| Общение | ty, gg, brb, wp, omw, cya, pls | 83 |
| Рейды и подземелья | wipe, prog, soak, kite, brez, pull, adds | 63 |
| Классы и специализации | dk, ret, bm, disc, resto | 59 |
| Сленг | ez, copium, bricked, w2w, gogo | 49 |
| Бой | aggro, aoe, cc, dot, purge, arena | 39 |
| Группы | lfm, lf1m, inv, pug, mythic, heroic | 36 |
| Эндгейм и Midnight | delve, m+, keystone, catalyst, timed | 26 |
| Характеристики | crit, haste, mastery, vers, mana, parse | 25 |
| Профессии | jc, bs, enchant, herb, alch | 17 |
| Состояние | afk, oom, combat, ooc, bio | 14 |
| Роли | tank, healer, dps, melee, ranged | 11 |
| Торговля | wtb, wts, bis, mats, cod, sold | 9 |
| Гильдия | gm, officer, recruit, gbank | 5 |

## Что заметно в игре

- **В ключе M+ чат закрыт, и компаньон об этом скажет.** С выходом Midnight
  игра отдаёт аддонам текст чата секретным значением, пока идёт забег. Прочитать
  его не может ни один аддон, этот тоже. Оверлей честно пишет, что чат закрыт, и
  возвращается к переводу, как только ключ закончился.
- **Ссылки на предметы целы.** Внутрь гиперссылок и цветовых блоков подсказка не
  лезет.
- **Пунктуация не прячет термины.** `dps/heal`, `gg,wp`, `brb/afk` находятся
  все, потому что так и пишут.
- **Заглавные не мешают.** Фраза, начатая со `Спс`, найдёт термин `спс`.
- **Один термин — одна подсказка.** На `ty ty ty` будет одно `ty = спасибо`.
- **Порядок как в сообщении.** Не больше трёх терминов плюс счётчик остальных,
  чтобы строка чата осталась строкой.
- **Пока работает компаньон, аддон молчит.** Иначе одну фразу переведут дважды
  и разными словами. Нужны оба сразу, включи в `/babel config`.

## Приватность

Аддон хранит только твои настройки. Компаньон отправляет текст сообщений тому
сервису перевода, который ты выбрал: без этого перевода не бывает. Больше никуда
ничего не уходит.

Чат на диск не пишется, пока ты сам не включишь запись, и галочка честно
предупреждает, что в файл попадут чужие шёпоты.

Права администратора не нужны.

## Благодарности

Словарь вырос из [WoW Translator](https://www.curseforge.com/wow/addons/wow-translator)
от **Pirson** (MIT): оттуда 314 терминов на 14 языках. BabelChat добавил сленг и
свежий набор по эндгейму и Midnight, переписал движок сопоставления и саму подачу
подсказки, а сверху получил приложение-компаньон.

- **Pirson** — данные словаря и сама идея подсказки в игре — [Buy Me a Coffee](https://buymeacoffee.com/franciscorb)
- **Andrey Yumashev** — аддон, приложение, движок перевода
- **AhegaoZKun** — поддержка Linux/Wayland, бэкенд Microsoft Translator

Лицензия MIT.
