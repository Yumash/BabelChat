local ADDON_NAME, addonTable = ...
addonTable.SlangDict = {
    -- ── Chat shortcuts / Сокращения в чате ──
    ["rdy"] = {
        esES = "Listo", esMX = "Listo", enUS = "Ready", deDE = "Bereit",
        frFR = "Prêt", itIT = "Pronto", koKR = "준비", ptBR = "Pronto",
        ruRU = "Готов", zhCN = "准备好了", zhTW = "準備好了",
        plPL = "Gotowy", svSE = "Redo", noNO = "Klar"
    },
    ["sec"] = {
        esES = "Un segundo", esMX = "Un segundo", enUS = "One second", deDE = "Sekunde",
        frFR = "Une seconde", itIT = "Un secondo", koKR = "잠깐", ptBR = "Um segundo",
        ruRU = "Секунду", zhCN = "等一下", zhTW = "等一下",
        plPL = "Sekundę", svSE = "En sekund", noNO = "Et sekund"
    },
    ["sry"] = {
        esES = "Perdón", esMX = "Perdón", enUS = "Sorry", deDE = "Sorry/Entschuldigung",
        frFR = "Désolé", itIT = "Scusa", koKR = "미안", ptBR = "Desculpa",
        ruRU = "Сорян/извини", zhCN = "抱歉", zhTW = "抱歉",
        plPL = "Sorki", svSE = "Förlåt", noNO = "Beklager"
    },
    ["soz"] = {
        esES = "Perdón", esMX = "Perdón", enUS = "Sorry", deDE = "Tut mir leid",
        frFR = "Désolé", itIT = "Scusa", koKR = "미안해", ptBR = "Desculpa",
        ruRU = "Сори", zhCN = "不好意思", zhTW = "不好意思",
        plPL = "Sorki", svSE = "Ursäkta", noNO = "Sorry"
    },
    ["ez"] = {
        esES = "Fácil", esMX = "Fácil", enUS = "Easy", deDE = "Einfach",
        frFR = "Facile", itIT = "Facile", koKR = "쉬움", ptBR = "Fácil",
        ruRU = "Изи/легко", zhCN = "简单", zhTW = "簡單",
        plPL = "Łatwe", svSE = "Lätt", noNO = "Lett"
    },
    ["kk"] = {
        esES = "Ok", esMX = "Ok", enUS = "Okay", deDE = "Ok",
        frFR = "Ok", itIT = "Ok", koKR = "ㅇㅋ", ptBR = "Ok",
        ruRU = "Ок/лан", zhCN = "好的", zhTW = "好的",
        plPL = "Ok", svSE = "Ok", noNO = "Ok"
    },
    ["w8"] = {
        esES = "Espera", esMX = "Espera", enUS = "Wait", deDE = "Warte",
        frFR = "Attends", itIT = "Aspetta", koKR = "기다려", ptBR = "Espera",
        ruRU = "Подожди", zhCN = "等等", zhTW = "等等",
        plPL = "Czekaj", svSE = "Vänta", noNO = "Vent"
    },
    ["nw"] = {
        esES = "No te preocupes", esMX = "No te preocupes", enUS = "No worries", deDE = "Kein Problem",
        frFR = "Pas de souci", itIT = "Non preoccuparti", koKR = "걱정마", ptBR = "Sem problemas",
        ruRU = "Не парься", zhCN = "没事", zhTW = "沒事",
        plPL = "Bez stresu", svSE = "Inga problem", noNO = "Ingen fare"
    },
    ["dw"] = {
        esES = "No te preocupes", esMX = "No te preocupes", enUS = "Don't worry", deDE = "Keine Sorge",
        frFR = "T'inquiète", itIT = "Non preoccuparti", koKR = "걱정마", ptBR = "Relaxa",
        ruRU = "Не парься", zhCN = "别担心", zhTW = "別擔心",
        plPL = "Nie martw się", svSE = "Oroa dig inte", noNO = "Ikke bekymre deg"
    },
    ["yw"] = {
        esES = "De nada", esMX = "De nada", enUS = "You're welcome", deDE = "Bitte/Gern geschehen",
        frFR = "De rien", itIT = "Prego", koKR = "천만에", ptBR = "De nada",
        ruRU = "Не за что", zhCN = "不客气", zhTW = "不客氣",
        plPL = "Nie ma za co", svSE = "Varsågod", noNO = "Bare hyggelig"
    },
    ["dc"] = {
        esES = "Desconectado", esMX = "Desconectado", enUS = "Disconnected", deDE = "Getrennt",
        frFR = "Déconnecté", itIT = "Disconnesso", koKR = "접속 끊김", ptBR = "Desconectou",
        ruRU = "Дисконнект/отвалился", zhCN = "掉线了", zhTW = "斷線了",
        plPL = "Rozłączyło", svSE = "Disconnectad", noNO = "Koblet fra"
    },
    ["rez"] = {
        esES = "Resurrección", esMX = "Resurrección", enUS = "Resurrect", deDE = "Wiederbelebung",
        frFR = "Résurrection", itIT = "Resurrezione", koKR = "부활", ptBR = "Ressurreição",
        ruRU = "Рез/воскресить", zhCN = "复活", zhTW = "復活",
        plPL = "Wskrzeszenie", svSE = "Återuppliva", noNO = "Gjenoppliv"
    },
    ["ofc"] = {
        esES = "Por supuesto", esMX = "Por supuesto", enUS = "Of course", deDE = "Natürlich",
        frFR = "Bien sûr", itIT = "Certo", koKR = "당연", ptBR = "Claro",
        ruRU = "Конечно", zhCN = "当然", zhTW = "當然",
        plPL = "Oczywiście", svSE = "Såklart", noNO = "Selvfølgelig"
    },
    ["fr"] = {
        esES = "En serio", esMX = "En serio", enUS = "For real", deDE = "Echt jetzt",
        frFR = "Pour de vrai", itIT = "Sul serio", koKR = "진짜", ptBR = "Sério",
        ruRU = "Реально/серьёзно", zhCN = "真的", zhTW = "真的",
        plPL = "Na serio", svSE = "På riktigt", noNO = "For real"
    },
    ["ngl"] = {
        esES = "No voy a mentir", esMX = "No voy a mentir", enUS = "Not gonna lie", deDE = "Ehrlich gesagt",
        frFR = "Je vais pas mentir", itIT = "Non mentirò", koKR = "솔직히", ptBR = "Sem mentira",
        ruRU = "Не буду врать", zhCN = "不骗你", zhTW = "不騙你",
        plPL = "Nie będę kłamać", svSE = "Ska inte ljuga", noNO = "Skal ikke lyve"
    },
    ["smh"] = {
        esES = "Sacudo la cabeza", esMX = "Sacudo la cabeza", enUS = "Shaking my head", deDE = "Kopfschütteln",
        frFR = "Je secoue la tête", itIT = "Scuoto la testa", koKR = "한심", ptBR = "Balançando a cabeça",
        ruRU = "Фейспалм", zhCN = "无语", zhTW = "無語",
        plPL = "Kręcę głową", svSE = "Skakar på huvudet", noNO = "Rister på hodet"
    },
    ["glhf"] = {
        esES = "Buena suerte, diviértete", esMX = "Buena suerte, diviértete", enUS = "Good luck, have fun", deDE = "Viel Glück, viel Spaß",
        frFR = "Bonne chance, amusez-vous", itIT = "Buona fortuna, divertiti", koKR = "행운을 빌어, 즐겜", ptBR = "Boa sorte, divirta-se",
        ruRU = "Удачи, веселой игры", zhCN = "祝好运，玩得开心", zhTW = "祝好運，玩得開心",
        plPL = "Powodzenia, baw się dobrze", svSE = "Lycka till, ha kul", noNO = "Lykke til, ha det gøy"
    },

    -- ── Gaming slang / Игровой сленг ──
    ["lust"] = {
        esES = "Lujuria de sangre", esMX = "Lujuria de sangre", enUS = "Bloodlust/Heroism", deDE = "Kampfrausch",
        frFR = "Furie sanguinaire", itIT = "Sete di sangue", koKR = "블러드러스트", ptBR = "Sede de Sangue",
        ruRU = "Героизм/лаcт", zhCN = "嗜血", zhTW = "乾渴怒血",
        plPL = "Żądza krwi", svSE = "Blodtörst", noNO = "Blodtørst"
    },
    ["bl"] = {
        esES = "Lujuria de sangre", esMX = "Lujuria de sangre", enUS = "Bloodlust", deDE = "Kampfrausch",
        frFR = "Furie sanguinaire", itIT = "Sete di sangue", koKR = "블러드러스트", ptBR = "Sede de Sangue",
        ruRU = "Героизм/бл", zhCN = "嗜血", zhTW = "嗜血",
        plPL = "Żądza krwi", svSE = "Blodtörst", noNO = "Blodtørst"
    },
    ["hero"] = {
        esES = "Heroísmo", esMX = "Heroísmo", enUS = "Heroism (Bloodlust)", deDE = "Heldentum",
        frFR = "Héroïsme", itIT = "Eroismo", koKR = "영웅심", ptBR = "Heroísmo",
        ruRU = "Героизм", zhCN = "英勇", zhTW = "英勇",
        plPL = "Heroizm", svSE = "Heroism", noNO = "Heroisme"
    },
    ["pug"] = {
        esES = "Grupo aleatorio", esMX = "Grupo aleatorio", enUS = "Pick-Up Group (random)", deDE = "Zufallsgruppe",
        frFR = "Groupe aléatoire", itIT = "Gruppo casuale", koKR = "야생 파티", ptBR = "Grupo aleatório",
        ruRU = "Паг/рандом группа", zhCN = "野队", zhTW = "野團",
        plPL = "Losowa grupa", svSE = "Slumpgrupp", noNO = "Tilfeldig gruppe"
    },
    ["bricked"] = {
        esES = "Clave arruinada", esMX = "Clave arruinada", enUS = "Key ruined/depleted", deDE = "Schlüssel versaut",
        frFR = "Clé ratée", itIT = "Chiave rovinata", koKR = "쐐기 실패", ptBR = "Chave perdida",
        ruRU = "Брикнули/слили ключ", zhCN = "砖了", zhTW = "磚了",
        plPL = "Klucz spalony", svSE = "Nyckeln körd", noNO = "Nøkkelen ødelagt"
    },
    ["pumping"] = {
        esES = "Haciendo mucho daño", esMX = "Haciendo mucho daño", enUS = "Doing huge damage", deDE = "Mächtig Schaden machen",
        frFR = "Énorme DPS", itIT = "Facendo danno enorme", koKR = "딜 쏟는 중", ptBR = "Mandando muito dano",
        ruRU = "Жарит/дамажит", zhCN = "爆发伤害", zhTW = "爆發傷害",
        plPL = "Wyżera", svSE = "Pumpar skada", noNO = "Pumper skade"
    },
    ["carry"] = {
        esES = "Llevar/cargar", esMX = "Llevar/cargar", enUS = "Carry (help weaker players)", deDE = "Tragen/durchziehen",
        frFR = "Porter/carry", itIT = "Portare", koKR = "캐리", ptBR = "Carregar",
        ruRU = "Кэрри/тащить", zhCN = "带/carry", zhTW = "帶/carry",
        plPL = "Nieść/carry", svSE = "Bära/carry", noNO = "Bære/carry"
    },
    ["wipe"] = {
        esES = "Todos muertos, reiniciar", esMX = "Todos muertos, reiniciar", enUS = "Everyone died, restart", deDE = "Alle tot, Neustart",
        frFR = "Tout le monde mort, on recommence", itIT = "Tutti morti, ricominciamo", koKR = "전멸", ptBR = "Todos morreram, reiniciar",
        ruRU = "Вайп/все умерли", zhCN = "团灭", zhTW = "團滅",
        plPL = "Wipe/wszyscy zginęli", svSE = "Alla döda, börja om", noNO = "Alle døde, start på nytt"
    },
    ["prog"] = {
        esES = "Progreso (aprendiendo boss)", esMX = "Progreso (aprendiendo boss)", enUS = "Progression (learning boss)", deDE = "Progress (Boss lernen)",
        frFR = "Progression (apprentissage)", itIT = "Progressione (imparare boss)", koKR = "공략 중", ptBR = "Progressão (aprendendo boss)",
        ruRU = "Прогресс (учим босса)", zhCN = "开荒", zhTW = "開荒",
        plPL = "Progress (nauka bossa)", svSE = "Progress (lär sig boss)", noNO = "Progresjon (lærer boss)"
    },
    ["kite"] = {
        esES = "Correr manteniendo aggro", esMX = "Correr manteniendo aggro", enUS = "Run away while keeping aggro", deDE = "Kiten (wegrennen mit Aggro)",
        frFR = "Kiter (fuir en gardant l'aggro)", itIT = "Kite (scappare tenendo aggro)", koKR = "카이팅", ptBR = "Kitar (correr mantendo aggro)",
        ruRU = "Кайтить", zhCN = "放风筝", zhTW = "放風箏",
        plPL = "Kitować", svSE = "Kita", noNO = "Kite"
    },
    ["go next"] = {
        esES = "Siguiente intento", esMX = "Siguiente intento", enUS = "Move on, next attempt", deDE = "Weiter, nächster Versuch",
        frFR = "On passe au suivant", itIT = "Avanti, prossimo tentativo", koKR = "다음 ㄱ", ptBR = "Bora próximo",
        ruRU = "Дальше/некст", zhCN = "下一把", zhTW = "下一把",
        plPL = "Dalej, następne podejście", svSE = "Vidare, nästa försök", noNO = "Videre, neste forsøk"
    },
    ["brez"] = {
        esES = "Resurrección en combate", esMX = "Resurrección en combate", enUS = "Battle resurrection", deDE = "Kampfwiederbelebung",
        frFR = "Résurrection en combat", itIT = "Resurrezione in combattimento", koKR = "전투 부활", ptBR = "Ressurreição em combate",
        ruRU = "Брез/боевое воскрешение", zhCN = "战复", zhTW = "戰復",
        plPL = "Bojowe wskrzeszenie", svSE = "Stridsåterupplivning", noNO = "Kampoppstandelse"
    },
    ["soak"] = {
        esES = "Absorber mecánica", esMX = "Absorber mecánica", enUS = "Stand in to absorb mechanic", deDE = "Mechanik absorbieren",
        frFR = "Absorber la mécanique", itIT = "Assorbire meccanica", koKR = "밟기", ptBR = "Absorver mecânica",
        ruRU = "Соук/встать в лужу", zhCN = "吃/踩", zhTW = "吃/踩",
        plPL = "Wchłonąć mechanikę", svSE = "Absorbera mekanik", noNO = "Absorbere mekanikk"
    },

    -- ── Toxicity & reactions / Токсичность и реакции ──
    ["copium"] = {
        esES = "Autoengaño", esMX = "Autoengaño", enUS = "Coping with bad outcome", deDE = "Sich was einreden",
        frFR = "Se voiler la face", itIT = "Autoillusione", koKR = "코피움/자기위안", ptBR = "Se enganando",
        ruRU = "Копиум/утешаю себя", zhCN = "精神胜利", zhTW = "精神勝利",
        plPL = "Copium", svSE = "Copium", noNO = "Copium"
    },
    ["clapped"] = {
        esES = "Destruido/aplastado", esMX = "Destruido/aplastado", enUS = "Got destroyed/wrecked", deDE = "Zerstört worden",
        frFR = "Détruit/éclaté", itIT = "Distrutto", koKR = "박살남", ptBR = "Destruído",
        ruRU = "Уничтожен/разнесли", zhCN = "被打爆了", zhTW = "被打爆了",
        plPL = "Zniszczony", svSE = "Förstörd", noNO = "Knust"
    },
    ["diff"] = {
        esES = "Diferencia de nivel", esMX = "Diferencia de nivel", enUS = "Skill difference/gap", deDE = "Skill-Unterschied",
        frFR = "Différence de niveau", itIT = "Differenza di livello", koKR = "실력 차이", ptBR = "Diferença de skill",
        ruRU = "Разница в скилле", zhCN = "差距", zhTW = "差距",
        plPL = "Różnica w skillu", svSE = "Skillskillnad", noNO = "Ferdighetsgap"
    },
    ["sweaty"] = {
        esES = "Tryhard/competitivo", esMX = "Tryhard/competitivo", enUS = "Tryhard/overly competitive", deDE = "Tryhard/verkrampft",
        frFR = "Tryhard/trop compétitif", itIT = "Tryhard/troppo competitivo", koKR = "빡겜러", ptBR = "Tryhard/suado",
        ruRU = "Потный/трайхард", zhCN = "肝帝/太认真", zhTW = "肝帝/太認真",
        plPL = "Spocony/tryhard", svSE = "Svettig/tryhard", noNO = "Svett/tryhard"
    },
    ["bot"] = {
        esES = "Bot (juega como robot)", esMX = "Bot (juega como robot)", enUS = "Plays like a robot/badly", deDE = "Bot (spielt wie ein Roboter)",
        frFR = "Bot (joue comme un robot)", itIT = "Bot (gioca come un robot)", koKR = "봇/기계처럼", ptBR = "Bot (joga como robô)",
        ruRU = "Бот/играет как бот", zhCN = "人机/打得像机器人", zhTW = "人機/打得像機器人",
        plPL = "Bot (gra jak robot)", svSE = "Bot (spelar som en robot)", noNO = "Bot (spiller som en robot)"
    },
    ["touch grass"] = {
        esES = "Sal afuera/toma aire", esMX = "Sal afuera/toma aire", enUS = "Go outside, take a break", deDE = "Geh mal raus",
        frFR = "Va prendre l'air", itIT = "Esci fuori", koKR = "밖에 나가", ptBR = "Vai tomar um ar",
        ruRU = "Выйди на улицу/тачграсс", zhCN = "出去走走", zhTW = "出去走走",
        plPL = "Idź na dwór", svSE = "Gå ut", noNO = "Gå ut"
    },
    ["kek"] = {
        esES = "Jaja (risa Horda)", esMX = "Jaja (risa Horda)", enUS = "Lol (Horde version)", deDE = "Haha (Horde-Version)",
        frFR = "Mdr (version Horde)", itIT = "Lol (versione Orda)", koKR = "ㅋㅋ (호드 버전)", ptBR = "Kk (versão Horda)",
        ruRU = "Кек/лол (Орда)", zhCN = "哈哈（部落版）", zhTW = "哈哈（部落版）",
        plPL = "Kek/lol (wersja Hordy)", svSE = "Kek/lol (Horde-version)", noNO = "Kek/lol (Horde-versjon)"
    },
    ["o7"] = {
        esES = "Saludo militar", esMX = "Saludo militar", enUS = "Salute", deDE = "Salut/Gruß",
        frFR = "Salut militaire", itIT = "Saluto militare", koKR = "경례", ptBR = "Continência",
        ruRU = "Салют/честь отдаю", zhCN = "敬礼", zhTW = "敬禮",
        plPL = "Salut", svSE = "Honnör", noNO = "Salutt"
    },

    -- ── M+ / Dungeon slang ──
    ["key"] = {
        esES = "Piedra angular mítica", esMX = "Piedra angular mítica", enUS = "Mythic+ keystone", deDE = "Mythisch+ Schlüsselstein",
        frFR = "Clé mythique+", itIT = "Chiave mitica+", koKR = "쐐기돌", ptBR = "Pedra angular mítica+",
        ruRU = "Ключ (мифик+)", zhCN = "钥石", zhTW = "鑰石",
        plPL = "Klucz (mityczny+)", svSE = "Mytisk+ nyckelsten", noNO = "Mytisk+ nøkkelstein"
    },
    ["io"] = {
        esES = "Puntuación Raider.IO", esMX = "Puntuación Raider.IO", enUS = "Raider.IO score", deDE = "Raider.IO Wertung",
        frFR = "Score Raider.IO", itIT = "Punteggio Raider.IO", koKR = "레이더IO 점수", ptBR = "Pontuação Raider.IO",
        ruRU = "Рио/рейтинг Raider.IO", zhCN = "RIO分数", zhTW = "RIO分數",
        plPL = "Wynik Raider.IO", svSE = "Raider.IO poäng", noNO = "Raider.IO poeng"
    },
    ["skip"] = {
        esES = "Saltar basura", esMX = "Saltar basura", enUS = "Skip trash packs", deDE = "Trash überspringen",
        frFR = "Passer les packs", itIT = "Saltare il trash", koKR = "스킵", ptBR = "Pular trash",
        ruRU = "Скип/пропускаем", zhCN = "跳过", zhTW = "跳過",
        plPL = "Pominąć", svSE = "Hoppa över", noNO = "Hoppe over"
    },
    ["w2w"] = {
        esES = "Pull masivo", esMX = "Pull masivo", enUS = "Wall-to-wall pull (everything)", deDE = "Alles pullen",
        frFR = "Pull massif (tout)", itIT = "Pull totale", koKR = "올킬풀", ptBR = "Pull gigante",
        ruRU = "Стена в стену (всё тянем)", zhCN = "一波全拉", zhTW = "一波全拉",
        plPL = "Pull wszystkiego", svSE = "Dra allt", noNO = "Dra alt"
    },
    ["pot"] = {
        esES = "Poción", esMX = "Poción", enUS = "Potion (combat)", deDE = "Trank",
        frFR = "Potion", itIT = "Pozione", koKR = "물약", ptBR = "Poção",
        ruRU = "Пот/зелье", zhCN = "药水", zhTW = "藥水",
        plPL = "Mikstura", svSE = "Dryck", noNO = "Drikk"
    },
    ["prepot"] = {
        esES = "Poción antes del pull", esMX = "Poción antes del pull", enUS = "Use potion before pull", deDE = "Vor-Pull Trank",
        frFR = "Potion avant le pull", itIT = "Pozione prima del pull", koKR = "선물약", ptBR = "Poção antes do pull",
        ruRU = "Препот (зелье до пулла)", zhCN = "预药", zhTW = "預藥",
        plPL = "Mikstura przed pullem", svSE = "Dryck före pull", noNO = "Drikk før pull"
    },
    ["vault"] = {
        esES = "Gran Cámara (cofre semanal)", esMX = "Gran Cámara (cofre semanal)", enUS = "Great Vault (weekly chest)", deDE = "Große Kammer (Wochentruhe)",
        frFR = "Grande Chambre (coffre hebdo)", itIT = "Grande Camera (forziere settimanale)", koKR = "대장금고", ptBR = "Grande Cofre (semanal)",
        ruRU = "Хранилище (недельный сундук)", zhCN = "宝库（每周宝箱）", zhTW = "寶庫（每週寶箱）",
        plPL = "Wielki Skarbiec (tygodniowa skrzynia)", svSE = "Stora Valvet (veckokista)", noNO = "Stort Hvelv (ukentlig kiste)"
    },

    -- ── PvP slang ──
    ["gank"] = {
        esES = "Matar por sorpresa", esMX = "Matar por sorpresa", enUS = "Kill unsuspecting player", deDE = "Hinterhalt/unerwarteter Kill",
        frFR = "Tuer par surprise", itIT = "Uccidere di sorpresa", koKR = "기습 킬", ptBR = "Matar de surpresa",
        ruRU = "Ганк/убить из засады", zhCN = "偷袭", zhTW = "偷襲",
        plPL = "Zabić z zaskoczenia", svSE = "Bakhåll/gank", noNO = "Bakholdsangrep"
    },
    ["glad"] = {
        esES = "Gladiador (título PvP top)", esMX = "Gladiador (título PvP top)", enUS = "Gladiator (top PvP title)", deDE = "Gladiator (Top PvP Titel)",
        frFR = "Gladiateur (titre PvP top)", itIT = "Gladiatore (titolo PvP top)", koKR = "검투사 (최상위 PvP)", ptBR = "Gladiador (título PvP top)",
        ruRU = "Глад/Гладиатор (топ PvP)", zhCN = "角斗士（顶级PvP称号）", zhTW = "角鬥士（頂級PvP稱號）",
        plPL = "Gladiator (top tytuł PvP)", svSE = "Gladiator (topp PvP-titel)", noNO = "Gladiator (topp PvP-tittel)"
    },
    ["mmr"] = {
        esES = "Rating de emparejamiento", esMX = "Rating de emparejamiento", enUS = "Matchmaking rating", deDE = "Matchmaking-Wertung",
        frFR = "Score de matchmaking", itIT = "Rating di matchmaking", koKR = "매칭 점수", ptBR = "Rating de matchmaking",
        ruRU = "ММР (рейтинг матчмейкинга)", zhCN = "匹配分", zhTW = "配對分",
        plPL = "MMR (rating dopasowania)", svSE = "Matchmaking-poäng", noNO = "Matchmaking-poeng"
    },
}
