"""Lightweight dependency-free UI localization.

UI strings are identified by the `Msg` enum, whose *values* are the English source
text. Translation tables are keyed by `Msg` members, so both call sites and table
entries are type-checked - a typo'd key fails at type-check/parse time instead of
silently falling back. Missing translations fall back to the English value.

Tone/goal display names have their own per-language maps keyed by the enum value.
The active language is set once at startup (see main.py); switching it requires an
app restart.
"""

from enum import StrEnum

from app.config import GOAL_DESCRIPTIONS as _EN_GOAL_DESCRIPTIONS
from app.schemas.models import Goal, Tone

DEFAULT_LANGUAGE = "en"

_current: str = DEFAULT_LANGUAGE


class Msg(StrEnum):
    """UI string identifiers. The member value is the English source text."""

    # main tab
    CLEAR = "Clear"
    SETTINGS = "Settings"
    ORIGINAL_TEXT = "Original Text"
    TONE_LABEL = "Tone:"
    POLISHED_VERSIONS = "Polished Versions"
    USE = "Use"
    COPY = "Copy"
    COPIED_EXCL = "Copied!"
    TRIGGER = "Trigger ({hotkey})"
    POLISHING = "Polishing…"
    POLISHING_PROGRESS = "Polishing… ({received}/{total})"
    POLISHED_READY = "Polished versions ready"
    ERROR = "Error"
    COPIED_TO_CLIPBOARD = "Copied to clipboard ({tone} / {goal})"
    PASTED = "Pasted ({tone} / {goal})"
    COPIED = "Copied ({tone} / {goal})"
    EMPTY = "Empty"
    ENTER_OR_PASTE = "Enter or paste text to polish."
    NO_API_KEY = "No API key"
    CONFIGURE_API_KEY = "Configure your API key in Settings first."
    LLM_ERROR = "LLM Error"
    LLM_ERROR_BODY = "An error occurred while calling the LLM:"
    OPEN_LOG = "Open Log"
    CLOSE = "Close"
    COULD_NOT_OPEN_LOG = "Could not open log file:\n{error}"

    # main window
    UPDATE_NOW = "Update Now"
    UPDATE_AVAILABLE = "Update v{version} available"
    MAIN = "Main"
    HISTORY = "History"
    OPEN = "Open"
    QUIT = "Quit"

    # settings dialog
    BASE_URL = "Base URL:"
    MODEL = "Model:"
    API_KEY = "API Key:"
    OUTPUT_LANGUAGE = "Output language:"
    INTERFACE_LANGUAGE = "Interface language:"
    OUTPUT_LANGUAGE_TOOLTIP = (
        "Polished text is written in this language.\n"
        "Input in any language is translated into it."
    )
    RUN_AT_STARTUP = "Run at Windows startup"
    GOALS_TO_GENERATE = "Goals to generate"
    MINIMUM = "Minimum"
    DEFAULT = "Default"
    ALL = "All"
    MORE_GOALS_DISCLAIMER = "More goals = longer generation time."
    CONTEXT = "Context:"
    CONTEXT_TOOLTIP = (
        "Describe the domain or situation your text belongs to\n"
        "(e.g. 'customer support', 'technical docs', 'sales emails').\n"
        "The LLM will strongly follow this context when polishing."
    )
    TEST_CONNECTION = "Test Connection"
    SAVE = "Save"
    CANCEL = "Cancel"
    TESTING = "Testing…"
    MISSING_FIELD = "Missing field"
    API_KEY_REQUIRED = "API key is required."
    MODEL_REQUIRED = "Model name is required."
    NO_GOALS_SELECTED = "No goals selected"
    SELECT_AT_LEAST_ONE_GOAL = "Select at least one goal."
    RESTART_TO_APPLY_LANGUAGE = "Restart Grammar AI to apply the new interface language."
    RESTART_NOW = "Restart Now"
    RESTART_LATER = "Restart Later"

    # history tab
    REFRESH = "Refresh"
    PAGE_SIZE = "Page size:"
    PREV = "Prev"
    NEXT = "Next"
    PAGE_X_OF_Y = "Page {cur} of {total}"
    USED_AT = "Used At"
    TONE = "Tone"
    GOAL = "Goal"
    POLISHED_TEXT = "Polished Text"
    HISTORY_ENTRY = "History Entry"
    ID = "ID"


# Per-language UI string maps, keyed by Msg. English is implicit (the member value).
_TRANSLATIONS: dict[str, dict[Msg, str]] = {
    "es": {
        Msg.CLEAR: "Limpiar",
        Msg.SETTINGS: "Configuración",
        Msg.ORIGINAL_TEXT: "Texto original",
        Msg.TONE_LABEL: "Tono:",
        Msg.POLISHED_VERSIONS: "Versiones pulidas",
        Msg.USE: "Usar",
        Msg.COPY: "Copiar",
        Msg.COPIED_EXCL: "¡Copiado!",
        Msg.TRIGGER: "Activar ({hotkey})",
        Msg.POLISHING: "Puliendo…",
        Msg.POLISHING_PROGRESS: "Puliendo… ({received}/{total})",
        Msg.POLISHED_READY: "Versiones pulidas listas",
        Msg.ERROR: "Error",
        Msg.COPIED_TO_CLIPBOARD: "Copiado al portapapeles ({tone} / {goal})",
        Msg.PASTED: "Pegado ({tone} / {goal})",
        Msg.COPIED: "Copiado ({tone} / {goal})",
        Msg.EMPTY: "Vacío",
        Msg.ENTER_OR_PASTE: "Escribe o pega texto para pulir.",
        Msg.NO_API_KEY: "Sin clave de API",
        Msg.CONFIGURE_API_KEY: "Primero configura tu clave de API en Configuración.",
        Msg.LLM_ERROR: "Error del LLM",
        Msg.LLM_ERROR_BODY: "Ocurrió un error al llamar al LLM:",
        Msg.OPEN_LOG: "Abrir registro",
        Msg.CLOSE: "Cerrar",
        Msg.COULD_NOT_OPEN_LOG: "No se pudo abrir el archivo de registro:\n{error}",
        Msg.UPDATE_NOW: "Actualizar ahora",
        Msg.UPDATE_AVAILABLE: "Actualización v{version} disponible",
        Msg.MAIN: "Principal",
        Msg.HISTORY: "Historial",
        Msg.OPEN: "Abrir",
        Msg.QUIT: "Salir",
        Msg.BASE_URL: "URL base:",
        Msg.MODEL: "Modelo:",
        Msg.API_KEY: "Clave de API:",
        Msg.OUTPUT_LANGUAGE: "Idioma de salida:",
        Msg.INTERFACE_LANGUAGE: "Idioma de la interfaz:",
        Msg.OUTPUT_LANGUAGE_TOOLTIP: "El texto pulido se escribe en este idioma.\nLa entrada en cualquier idioma se traduce a él.",
        Msg.RUN_AT_STARTUP: "Ejecutar al iniciar Windows",
        Msg.GOALS_TO_GENERATE: "Objetivos a generar",
        Msg.MINIMUM: "Mínimo",
        Msg.DEFAULT: "Predeterminado",
        Msg.ALL: "Todos",
        Msg.MORE_GOALS_DISCLAIMER: "Más objetivos = mayor tiempo de generación.",
        Msg.TEST_CONNECTION: "Probar conexión",
        Msg.SAVE: "Guardar",
        Msg.CANCEL: "Cancelar",
        Msg.TESTING: "Probando…",
        Msg.MISSING_FIELD: "Campo faltante",
        Msg.API_KEY_REQUIRED: "Se requiere la clave de API.",
        Msg.MODEL_REQUIRED: "Se requiere el nombre del modelo.",
        Msg.NO_GOALS_SELECTED: "Ningún objetivo seleccionado",
        Msg.SELECT_AT_LEAST_ONE_GOAL: "Selecciona al menos un objetivo.",
        Msg.RESTART_TO_APPLY_LANGUAGE: "Reinicia Grammar AI para aplicar el nuevo idioma de la interfaz.",
        Msg.RESTART_NOW: "Reiniciar ahora",
        Msg.RESTART_LATER: "Reiniciar más tarde",
        Msg.CONTEXT: "Contexto:",
        Msg.CONTEXT_TOOLTIP: "Describe el dominio o situación de tu texto\n(p. ej. 'soporte al cliente', 'docs técnicos', 'emails de ventas').\nEl LLM seguirá este contexto estrictamente al pulir el texto.",
        Msg.REFRESH: "Actualizar",
        Msg.PAGE_SIZE: "Tamaño de página:",
        Msg.PREV: "Anterior",
        Msg.NEXT: "Siguiente",
        Msg.PAGE_X_OF_Y: "Página {cur} de {total}",
        Msg.USED_AT: "Fecha de uso",
        Msg.TONE: "Tono",
        Msg.GOAL: "Objetivo",
        Msg.POLISHED_TEXT: "Texto pulido",
        Msg.HISTORY_ENTRY: "Entrada del historial",
        Msg.ID: "ID",
    },
    "fr": {
        Msg.CLEAR: "Effacer",
        Msg.SETTINGS: "Paramètres",
        Msg.ORIGINAL_TEXT: "Texte original",
        Msg.TONE_LABEL: "Ton :",
        Msg.POLISHED_VERSIONS: "Versions peaufinées",
        Msg.USE: "Utiliser",
        Msg.COPY: "Copier",
        Msg.COPIED_EXCL: "Copié !",
        Msg.TRIGGER: "Déclencher ({hotkey})",
        Msg.POLISHING: "Peaufinage…",
        Msg.POLISHING_PROGRESS: "Peaufinage… ({received}/{total})",
        Msg.POLISHED_READY: "Versions peaufinées prêtes",
        Msg.ERROR: "Erreur",
        Msg.COPIED_TO_CLIPBOARD: "Copié dans le presse-papiers ({tone} / {goal})",
        Msg.PASTED: "Collé ({tone} / {goal})",
        Msg.COPIED: "Copié ({tone} / {goal})",
        Msg.EMPTY: "Vide",
        Msg.ENTER_OR_PASTE: "Saisissez ou collez le texte à peaufiner.",
        Msg.NO_API_KEY: "Aucune clé API",
        Msg.CONFIGURE_API_KEY: "Configurez d'abord votre clé API dans les Paramètres.",
        Msg.LLM_ERROR: "Erreur du LLM",
        Msg.LLM_ERROR_BODY: "Une erreur s'est produite lors de l'appel au LLM :",
        Msg.OPEN_LOG: "Ouvrir le journal",
        Msg.CLOSE: "Fermer",
        Msg.COULD_NOT_OPEN_LOG: "Impossible d'ouvrir le fichier journal :\n{error}",
        Msg.UPDATE_NOW: "Mettre à jour maintenant",
        Msg.UPDATE_AVAILABLE: "Mise à jour v{version} disponible",
        Msg.MAIN: "Principal",
        Msg.HISTORY: "Historique",
        Msg.OPEN: "Ouvrir",
        Msg.QUIT: "Quitter",
        Msg.BASE_URL: "URL de base :",
        Msg.MODEL: "Modèle :",
        Msg.API_KEY: "Clé API :",
        Msg.OUTPUT_LANGUAGE: "Langue de sortie :",
        Msg.INTERFACE_LANGUAGE: "Langue de l'interface :",
        Msg.OUTPUT_LANGUAGE_TOOLTIP: "Le texte peaufiné est rédigé dans cette langue.\nUne entrée dans n'importe quelle langue y est traduite.",
        Msg.RUN_AT_STARTUP: "Lancer au démarrage de Windows",
        Msg.GOALS_TO_GENERATE: "Objectifs à générer",
        Msg.MINIMUM: "Minimum",
        Msg.DEFAULT: "Par défaut",
        Msg.ALL: "Tous",
        Msg.MORE_GOALS_DISCLAIMER: "Plus d'objectifs = temps de génération plus long.",
        Msg.TEST_CONNECTION: "Tester la connexion",
        Msg.SAVE: "Enregistrer",
        Msg.CANCEL: "Annuler",
        Msg.TESTING: "Test en cours…",
        Msg.MISSING_FIELD: "Champ manquant",
        Msg.API_KEY_REQUIRED: "La clé API est requise.",
        Msg.MODEL_REQUIRED: "Le nom du modèle est requis.",
        Msg.NO_GOALS_SELECTED: "Aucun objectif sélectionné",
        Msg.SELECT_AT_LEAST_ONE_GOAL: "Sélectionnez au moins un objectif.",
        Msg.RESTART_TO_APPLY_LANGUAGE: "Redémarrez Grammar AI pour appliquer la nouvelle langue de l'interface.",
        Msg.RESTART_NOW: "Redémarrer maintenant",
        Msg.RESTART_LATER: "Redémarrer plus tard",
        Msg.CONTEXT: "Contexte :",
        Msg.CONTEXT_TOOLTIP: "Décrivez le domaine ou la situation de votre texte\n(ex. 'support client', 'docs techniques', 'e-mails commerciaux').\nLe LLM respectera strictement ce contexte lors du peaufinage.",
        Msg.REFRESH: "Actualiser",
        Msg.PAGE_SIZE: "Taille de page :",
        Msg.PREV: "Préc.",
        Msg.NEXT: "Suiv.",
        Msg.PAGE_X_OF_Y: "Page {cur} sur {total}",
        Msg.USED_AT: "Utilisé le",
        Msg.TONE: "Ton",
        Msg.GOAL: "Objectif",
        Msg.POLISHED_TEXT: "Texte peaufiné",
        Msg.HISTORY_ENTRY: "Entrée d'historique",
        Msg.ID: "ID",
    },
    "de": {
        Msg.CLEAR: "Leeren",
        Msg.SETTINGS: "Einstellungen",
        Msg.ORIGINAL_TEXT: "Originaltext",
        Msg.TONE_LABEL: "Ton:",
        Msg.POLISHED_VERSIONS: "Verfeinerte Versionen",
        Msg.USE: "Verwenden",
        Msg.COPY: "Kopieren",
        Msg.COPIED_EXCL: "Kopiert!",
        Msg.TRIGGER: "Auslösen ({hotkey})",
        Msg.POLISHING: "Verfeinern…",
        Msg.POLISHING_PROGRESS: "Verfeinern… ({received}/{total})",
        Msg.POLISHED_READY: "Verfeinerte Versionen bereit",
        Msg.ERROR: "Fehler",
        Msg.COPIED_TO_CLIPBOARD: "In die Zwischenablage kopiert ({tone} / {goal})",
        Msg.PASTED: "Eingefügt ({tone} / {goal})",
        Msg.COPIED: "Kopiert ({tone} / {goal})",
        Msg.EMPTY: "Leer",
        Msg.ENTER_OR_PASTE: "Text zum Verfeinern eingeben oder einfügen.",
        Msg.NO_API_KEY: "Kein API-Schlüssel",
        Msg.CONFIGURE_API_KEY: "Konfiguriere zuerst deinen API-Schlüssel in den Einstellungen.",
        Msg.LLM_ERROR: "LLM-Fehler",
        Msg.LLM_ERROR_BODY: "Beim Aufruf des LLM ist ein Fehler aufgetreten:",
        Msg.OPEN_LOG: "Protokoll öffnen",
        Msg.CLOSE: "Schließen",
        Msg.COULD_NOT_OPEN_LOG: "Protokolldatei konnte nicht geöffnet werden:\n{error}",
        Msg.UPDATE_NOW: "Jetzt aktualisieren",
        Msg.UPDATE_AVAILABLE: "Update v{version} verfügbar",
        Msg.MAIN: "Haupt",
        Msg.HISTORY: "Verlauf",
        Msg.OPEN: "Öffnen",
        Msg.QUIT: "Beenden",
        Msg.BASE_URL: "Basis-URL:",
        Msg.MODEL: "Modell:",
        Msg.API_KEY: "API-Schlüssel:",
        Msg.OUTPUT_LANGUAGE: "Ausgabesprache:",
        Msg.INTERFACE_LANGUAGE: "Oberflächensprache:",
        Msg.OUTPUT_LANGUAGE_TOOLTIP: "Der verfeinerte Text wird in dieser Sprache verfasst.\nEingaben in jeder Sprache werden in sie übersetzt.",
        Msg.RUN_AT_STARTUP: "Beim Windows-Start ausführen",
        Msg.GOALS_TO_GENERATE: "Zu generierende Ziele",
        Msg.MINIMUM: "Minimum",
        Msg.DEFAULT: "Standard",
        Msg.ALL: "Alle",
        Msg.MORE_GOALS_DISCLAIMER: "Mehr Ziele = längere Generierungszeit.",
        Msg.TEST_CONNECTION: "Verbindung testen",
        Msg.SAVE: "Speichern",
        Msg.CANCEL: "Abbrechen",
        Msg.TESTING: "Test läuft…",
        Msg.MISSING_FIELD: "Fehlendes Feld",
        Msg.API_KEY_REQUIRED: "API-Schlüssel ist erforderlich.",
        Msg.MODEL_REQUIRED: "Modellname ist erforderlich.",
        Msg.NO_GOALS_SELECTED: "Keine Ziele ausgewählt",
        Msg.SELECT_AT_LEAST_ONE_GOAL: "Wähle mindestens ein Ziel aus.",
        Msg.RESTART_TO_APPLY_LANGUAGE: "Starte Grammar AI neu, um die neue Oberflächensprache anzuwenden.",
        Msg.RESTART_NOW: "Jetzt neu starten",
        Msg.RESTART_LATER: "Später neu starten",
        Msg.CONTEXT: "Kontext:",
        Msg.CONTEXT_TOOLTIP: "Beschreibe die Domäne oder Situation deines Textes\n(z. B. 'Kundensupport', 'technische Doku', 'Verkaufs-E-Mails').\nDas LLM folgt diesem Kontext strikt beim Verfeinern.",
        Msg.REFRESH: "Aktualisieren",
        Msg.PAGE_SIZE: "Seitengröße:",
        Msg.PREV: "Zurück",
        Msg.NEXT: "Weiter",
        Msg.PAGE_X_OF_Y: "Seite {cur} von {total}",
        Msg.USED_AT: "Verwendet am",
        Msg.TONE: "Ton",
        Msg.GOAL: "Ziel",
        Msg.POLISHED_TEXT: "Verfeinerter Text",
        Msg.HISTORY_ENTRY: "Verlaufseintrag",
        Msg.ID: "ID",
    },
    "ja": {
        Msg.CLEAR: "クリア",
        Msg.SETTINGS: "設定",
        Msg.ORIGINAL_TEXT: "元のテキスト",
        Msg.TONE_LABEL: "トーン:",
        Msg.POLISHED_VERSIONS: "推敲されたバージョン",
        Msg.USE: "使用",
        Msg.COPY: "コピー",
        Msg.COPIED_EXCL: "コピーしました!",
        Msg.TRIGGER: "実行 ({hotkey})",
        Msg.POLISHING: "推敲中…",
        Msg.POLISHING_PROGRESS: "推敲中… ({received}/{total})",
        Msg.POLISHED_READY: "推敲されたバージョンが準備できました",
        Msg.ERROR: "エラー",
        Msg.COPIED_TO_CLIPBOARD: "クリップボードにコピーしました ({tone} / {goal})",
        Msg.PASTED: "貼り付けました ({tone} / {goal})",
        Msg.COPIED: "コピーしました ({tone} / {goal})",
        Msg.EMPTY: "空",
        Msg.ENTER_OR_PASTE: "推敲するテキストを入力または貼り付けてください。",
        Msg.NO_API_KEY: "APIキーがありません",
        Msg.CONFIGURE_API_KEY: "先に設定でAPIキーを構成してください。",
        Msg.LLM_ERROR: "LLMエラー",
        Msg.LLM_ERROR_BODY: "LLMの呼び出し中にエラーが発生しました:",
        Msg.OPEN_LOG: "ログを開く",
        Msg.CLOSE: "閉じる",
        Msg.COULD_NOT_OPEN_LOG: "ログファイルを開けませんでした:\n{error}",
        Msg.UPDATE_NOW: "今すぐ更新",
        Msg.UPDATE_AVAILABLE: "アップデート v{version} が利用可能です",
        Msg.MAIN: "メイン",
        Msg.HISTORY: "履歴",
        Msg.OPEN: "開く",
        Msg.QUIT: "終了",
        Msg.BASE_URL: "ベースURL:",
        Msg.MODEL: "モデル:",
        Msg.API_KEY: "APIキー:",
        Msg.OUTPUT_LANGUAGE: "出力言語:",
        Msg.INTERFACE_LANGUAGE: "インターフェース言語:",
        Msg.OUTPUT_LANGUAGE_TOOLTIP: "推敲されたテキストはこの言語で書かれます。\nどの言語の入力もこの言語に翻訳されます。",
        Msg.RUN_AT_STARTUP: "Windows起動時に実行",
        Msg.GOALS_TO_GENERATE: "生成する目標",
        Msg.MINIMUM: "最小",
        Msg.DEFAULT: "デフォルト",
        Msg.ALL: "すべて",
        Msg.MORE_GOALS_DISCLAIMER: "目標が多いほど生成時間が長くなります。",
        Msg.TEST_CONNECTION: "接続をテスト",
        Msg.SAVE: "保存",
        Msg.CANCEL: "キャンセル",
        Msg.TESTING: "テスト中…",
        Msg.MISSING_FIELD: "未入力の項目",
        Msg.API_KEY_REQUIRED: "APIキーが必要です。",
        Msg.MODEL_REQUIRED: "モデル名が必要です。",
        Msg.NO_GOALS_SELECTED: "目標が選択されていません",
        Msg.SELECT_AT_LEAST_ONE_GOAL: "少なくとも1つの目標を選択してください。",
        Msg.RESTART_TO_APPLY_LANGUAGE: "新しいインターフェース言語を適用するにはGrammar AIを再起動してください。",
        Msg.RESTART_NOW: "今すぐ再起動",
        Msg.RESTART_LATER: "後で再起動",
        Msg.CONTEXT: "コンテキスト:",
        Msg.CONTEXT_TOOLTIP: "テキストのドメインや状況を説明してください\n(例: 'カスタマーサポート', '技術ドキュメント', '営業メール')。\nLLMは推敲時にこのコンテキストを厳守します。",
        Msg.REFRESH: "更新",
        Msg.PAGE_SIZE: "ページサイズ:",
        Msg.PREV: "前へ",
        Msg.NEXT: "次へ",
        Msg.PAGE_X_OF_Y: "{total}ページ中{cur}ページ",
        Msg.USED_AT: "使用日時",
        Msg.TONE: "トーン",
        Msg.GOAL: "目標",
        Msg.POLISHED_TEXT: "推敲されたテキスト",
        Msg.HISTORY_ENTRY: "履歴エントリ",
        Msg.ID: "ID",
    },
    "ko": {
        Msg.CLEAR: "지우기",
        Msg.SETTINGS: "설정",
        Msg.ORIGINAL_TEXT: "원본 텍스트",
        Msg.TONE_LABEL: "톤:",
        Msg.POLISHED_VERSIONS: "다듬어진 버전",
        Msg.USE: "사용",
        Msg.COPY: "복사",
        Msg.COPIED_EXCL: "복사됨!",
        Msg.TRIGGER: "실행 ({hotkey})",
        Msg.POLISHING: "다듬는 중…",
        Msg.POLISHING_PROGRESS: "다듬는 중… ({received}/{total})",
        Msg.POLISHED_READY: "다듬어진 버전 준비 완료",
        Msg.ERROR: "오류",
        Msg.COPIED_TO_CLIPBOARD: "클립보드에 복사됨 ({tone} / {goal})",
        Msg.PASTED: "붙여넣음 ({tone} / {goal})",
        Msg.COPIED: "복사됨 ({tone} / {goal})",
        Msg.EMPTY: "비어 있음",
        Msg.ENTER_OR_PASTE: "다듬을 텍스트를 입력하거나 붙여넣으세요.",
        Msg.NO_API_KEY: "API 키 없음",
        Msg.CONFIGURE_API_KEY: "먼저 설정에서 API 키를 구성하세요.",
        Msg.LLM_ERROR: "LLM 오류",
        Msg.LLM_ERROR_BODY: "LLM 호출 중 오류가 발생했습니다:",
        Msg.OPEN_LOG: "로그 열기",
        Msg.CLOSE: "닫기",
        Msg.COULD_NOT_OPEN_LOG: "로그 파일을 열 수 없습니다:\n{error}",
        Msg.UPDATE_NOW: "지금 업데이트",
        Msg.UPDATE_AVAILABLE: "업데이트 v{version} 사용 가능",
        Msg.MAIN: "메인",
        Msg.HISTORY: "기록",
        Msg.OPEN: "열기",
        Msg.QUIT: "종료",
        Msg.BASE_URL: "기본 URL:",
        Msg.MODEL: "모델:",
        Msg.API_KEY: "API 키:",
        Msg.OUTPUT_LANGUAGE: "출력 언어:",
        Msg.INTERFACE_LANGUAGE: "인터페이스 언어:",
        Msg.OUTPUT_LANGUAGE_TOOLTIP: "다듬어진 텍스트는 이 언어로 작성됩니다.\n어떤 언어의 입력도 이 언어로 번역됩니다.",
        Msg.RUN_AT_STARTUP: "Windows 시작 시 실행",
        Msg.GOALS_TO_GENERATE: "생성할 목표",
        Msg.MINIMUM: "최소",
        Msg.DEFAULT: "기본값",
        Msg.ALL: "전체",
        Msg.MORE_GOALS_DISCLAIMER: "목표가 많을수록 생성 시간이 길어집니다.",
        Msg.TEST_CONNECTION: "연결 테스트",
        Msg.SAVE: "저장",
        Msg.CANCEL: "취소",
        Msg.TESTING: "테스트 중…",
        Msg.MISSING_FIELD: "누락된 항목",
        Msg.API_KEY_REQUIRED: "API 키가 필요합니다.",
        Msg.MODEL_REQUIRED: "모델 이름이 필요합니다.",
        Msg.NO_GOALS_SELECTED: "선택된 목표 없음",
        Msg.SELECT_AT_LEAST_ONE_GOAL: "최소 한 개의 목표를 선택하세요.",
        Msg.RESTART_TO_APPLY_LANGUAGE: "새 인터페이스 언어를 적용하려면 Grammar AI를 다시 시작하세요.",
        Msg.RESTART_NOW: "지금 다시 시작",
        Msg.RESTART_LATER: "나중에 다시 시작",
        Msg.CONTEXT: "컨텍스트:",
        Msg.CONTEXT_TOOLTIP: "텍스트의 도메인이나 상황을 설명하세요\n(예: '고객 지원', '기술 문서', '영업 이메일').\nLLM은 다듬기 시 이 컨텍스트를 엄격히 따릅니다.",
        Msg.REFRESH: "새로 고침",
        Msg.PAGE_SIZE: "페이지 크기:",
        Msg.PREV: "이전",
        Msg.NEXT: "다음",
        Msg.PAGE_X_OF_Y: "{total} 중 {cur} 페이지",
        Msg.USED_AT: "사용 시각",
        Msg.TONE: "톤",
        Msg.GOAL: "목표",
        Msg.POLISHED_TEXT: "다듬어진 텍스트",
        Msg.HISTORY_ENTRY: "기록 항목",
        Msg.ID: "ID",
    },
}

# Tone display names keyed by Tone value. English falls back to value.capitalize().
_TONE_NAMES: dict[str, dict[Tone, str]] = {
    "es": {
        Tone.PROFESSIONAL: "Profesional",
        Tone.CASUAL: "Informal",
        Tone.CHATTING: "Charla",
        Tone.FORMAL: "Formal",
        Tone.FRIENDLY: "Amistoso",
        Tone.EMPATHETIC: "Empático",
        Tone.ASSERTIVE: "Asertivo",
        Tone.DIPLOMATIC: "Diplomático",
    },
    "fr": {
        Tone.PROFESSIONAL: "Professionnel",
        Tone.CASUAL: "Décontracté",
        Tone.CHATTING: "Discussion",
        Tone.FORMAL: "Formel",
        Tone.FRIENDLY: "Amical",
        Tone.EMPATHETIC: "Empathique",
        Tone.ASSERTIVE: "Affirmé",
        Tone.DIPLOMATIC: "Diplomatique",
    },
    "de": {
        Tone.PROFESSIONAL: "Professionell",
        Tone.CASUAL: "Locker",
        Tone.CHATTING: "Chat",
        Tone.FORMAL: "Förmlich",
        Tone.FRIENDLY: "Freundlich",
        Tone.EMPATHETIC: "Empathisch",
        Tone.ASSERTIVE: "Bestimmt",
        Tone.DIPLOMATIC: "Diplomatisch",
    },
    "ja": {
        Tone.PROFESSIONAL: "プロフェッショナル",
        Tone.CASUAL: "カジュアル",
        Tone.CHATTING: "チャット",
        Tone.FORMAL: "フォーマル",
        Tone.FRIENDLY: "フレンドリー",
        Tone.EMPATHETIC: "共感的",
        Tone.ASSERTIVE: "断定的",
        Tone.DIPLOMATIC: "外交的",
    },
    "ko": {
        Tone.PROFESSIONAL: "전문적",
        Tone.CASUAL: "캐주얼",
        Tone.CHATTING: "채팅",
        Tone.FORMAL: "격식체",
        Tone.FRIENDLY: "친근함",
        Tone.EMPATHETIC: "공감적",
        Tone.ASSERTIVE: "단호함",
        Tone.DIPLOMATIC: "외교적",
    },
}

# Goal display names keyed by Goal value. English falls back to value.capitalize().
_GOAL_NAMES: dict[str, dict[Goal, str]] = {
    "es": {
        Goal.INFORM: "Informar",
        Goal.PERSUADE: "Persuadir",
        Goal.REASSURE: "Tranquilizar",
        Goal.MOTIVATE: "Motivar",
        Goal.CLARIFY: "Aclarar",
        Goal.APOLOGIZE: "Disculparse",
        Goal.REQUEST: "Solicitar",
        Goal.ACKNOWLEDGE: "Reconocer",
        Goal.ENGAGE: "Involucrar",
        Goal.REVIEW: "Revisar",
        Goal.CLEAN: "Depurar",
    },
    "fr": {
        Goal.INFORM: "Informer",
        Goal.PERSUADE: "Persuader",
        Goal.REASSURE: "Rassurer",
        Goal.MOTIVATE: "Motiver",
        Goal.CLARIFY: "Clarifier",
        Goal.APOLOGIZE: "S'excuser",
        Goal.REQUEST: "Demander",
        Goal.ACKNOWLEDGE: "Reconnaître",
        Goal.ENGAGE: "Engager",
        Goal.REVIEW: "Évaluer",
        Goal.CLEAN: "Épurer",
    },
    "de": {
        Goal.INFORM: "Informieren",
        Goal.PERSUADE: "Überzeugen",
        Goal.REASSURE: "Beruhigen",
        Goal.MOTIVATE: "Motivieren",
        Goal.CLARIFY: "Klären",
        Goal.APOLOGIZE: "Entschuldigen",
        Goal.REQUEST: "Anfragen",
        Goal.ACKNOWLEDGE: "Anerkennen",
        Goal.ENGAGE: "Einbinden",
        Goal.REVIEW: "Bewerten",
        Goal.CLEAN: "Bereinigen",
    },
    "ja": {
        Goal.INFORM: "情報提供",
        Goal.PERSUADE: "説得",
        Goal.REASSURE: "安心させる",
        Goal.MOTIVATE: "動機づけ",
        Goal.CLARIFY: "明確化",
        Goal.APOLOGIZE: "謝罪",
        Goal.REQUEST: "依頼",
        Goal.ACKNOWLEDGE: "承認",
        Goal.ENGAGE: "引き込む",
        Goal.REVIEW: "レビュー",
        Goal.CLEAN: "整理",
    },
    "ko": {
        Goal.INFORM: "정보 전달",
        Goal.PERSUADE: "설득",
        Goal.REASSURE: "안심",
        Goal.MOTIVATE: "동기 부여",
        Goal.CLARIFY: "명확화",
        Goal.APOLOGIZE: "사과",
        Goal.REQUEST: "요청",
        Goal.ACKNOWLEDGE: "인정",
        Goal.ENGAGE: "참여 유도",
        Goal.REVIEW: "검토",
        Goal.CLEAN: "정리",
    },
}


# Goal description (tooltip) text keyed by Goal value. English source lives in
# app.config.GOAL_DESCRIPTIONS and is used as the fallback.
_GOAL_DESCRIPTIONS: dict[str, dict[Goal, str]] = {
    "es": {
        Goal.INFORM: "Presentar los hechos de forma clara y objetiva",
        Goal.PERSUADE: "Convencer al lector de adoptar un punto de vista o actuar",
        Goal.REASSURE: "Calmar inquietudes y generar confianza",
        Goal.MOTIVATE: "Inspirar entusiasmo e impulsar la acción",
        Goal.CLARIFY: "Simplificar y hacer el significado inequívoco",
        Goal.APOLOGIZE: "Expresar arrepentimiento y asumir la responsabilidad",
        Goal.REQUEST: "Pedir cortésmente una acción o información",
        Goal.ACKNOWLEDGE: "Validar el punto, el esfuerzo o los sentimientos del lector",
        Goal.ENGAGE: "Hacer el texto más interesante y conversacional",
        Goal.REVIEW: "Evaluar críticamente con comentarios equilibrados y constructivos",
        Goal.CLEAN: "Eliminar el relleno y ceñirse al significado esencial",
    },
    "fr": {
        Goal.INFORM: "Présenter les faits de façon claire et objective",
        Goal.PERSUADE: "Convaincre le lecteur d'adopter un point de vue ou d'agir",
        Goal.REASSURE: "Apaiser les inquiétudes et instaurer la confiance",
        Goal.MOTIVATE: "Susciter l'enthousiasme et inciter à l'action",
        Goal.CLARIFY: "Simplifier et rendre le sens sans ambiguïté",
        Goal.APOLOGIZE: "Exprimer des regrets et assumer ses responsabilités",
        Goal.REQUEST: "Demander poliment une action ou une information",
        Goal.ACKNOWLEDGE: "Valider le point de vue, l'effort ou les sentiments du lecteur",
        Goal.ENGAGE: "Rendre le texte plus intéressant et conversationnel",
        Goal.REVIEW: "Évaluer de façon critique avec un retour équilibré et constructif",
        Goal.CLEAN: "Éliminer le superflu et resserrer sur l'essentiel",
    },
    "de": {
        Goal.INFORM: "Fakten klar und objektiv darstellen",
        Goal.PERSUADE: "Den Leser von einer Sichtweise überzeugen oder zum Handeln bewegen",
        Goal.REASSURE: "Bedenken zerstreuen und Vertrauen aufbauen",
        Goal.MOTIVATE: "Begeisterung wecken und zum Handeln antreiben",
        Goal.CLARIFY: "Vereinfachen und die Bedeutung eindeutig machen",
        Goal.APOLOGIZE: "Bedauern ausdrücken und Verantwortung übernehmen",
        Goal.REQUEST: "Höflich um eine Handlung oder Information bitten",
        Goal.ACKNOWLEDGE: "Den Standpunkt, die Mühe oder die Gefühle des Lesers anerkennen",
        Goal.ENGAGE: "Den Text interessanter und gesprächiger gestalten",
        Goal.REVIEW: "Kritisch mit ausgewogenem, konstruktivem Feedback bewerten",
        Goal.CLEAN: "Überflüssiges entfernen und auf das Wesentliche straffen",
    },
    "ja": {
        Goal.INFORM: "事実を明確かつ客観的に伝える",
        Goal.PERSUADE: "読者に考えを受け入れさせ、行動を促す",
        Goal.REASSURE: "不安を和らげ、信頼を築く",
        Goal.MOTIVATE: "熱意を引き出し、行動を促す",
        Goal.CLARIFY: "簡潔にして意味を明確にする",
        Goal.APOLOGIZE: "遺憾の意を表し、責任を負う",
        Goal.REQUEST: "行動や情報を丁寧に依頼する",
        Goal.ACKNOWLEDGE: "読者の主張、努力、感情を認める",
        Goal.ENGAGE: "文章をより面白く会話的にする",
        Goal.REVIEW: "バランスの取れた建設的なフィードバックで批評する",
        Goal.CLEAN: "無駄を省き、本質的な意味に引き締める",
    },
    "ko": {
        Goal.INFORM: "사실을 명확하고 객관적으로 전달",
        Goal.PERSUADE: "독자가 관점을 받아들이거나 행동하도록 설득",
        Goal.REASSURE: "우려를 가라앉히고 신뢰를 형성",
        Goal.MOTIVATE: "열정을 불러일으키고 행동을 유도",
        Goal.CLARIFY: "단순화하여 의미를 명확하게",
        Goal.APOLOGIZE: "유감을 표하고 책임을 짐",
        Goal.REQUEST: "행동이나 정보를 정중하게 요청",
        Goal.ACKNOWLEDGE: "독자의 주장, 노력, 감정을 인정",
        Goal.ENGAGE: "글을 더 흥미롭고 대화체로 만듦",
        Goal.REVIEW: "균형 잡힌 건설적인 피드백으로 비평",
        Goal.CLEAN: "군더더기를 없애고 핵심 의미로 다듬음",
    },
}


def set_language(code: str) -> None:
    global _current
    _current = code or DEFAULT_LANGUAGE


def get_language() -> str:
    return _current


def t(key: Msg) -> str:
    """Return the translation for `key` in the active language, or its English value."""
    return _TRANSLATIONS.get(_current, {}).get(key, key.value)


def tone_name(tone: Tone) -> str:
    return _TONE_NAMES.get(_current, {}).get(tone, tone.capitalize())


def goal_name(goal: Goal) -> str:
    return _GOAL_NAMES.get(_current, {}).get(goal, goal.capitalize())


def goal_description(goal: Goal) -> str:
    """Localized tooltip description for a goal; falls back to the English source."""
    localized = _GOAL_DESCRIPTIONS.get(_current, {}).get(goal)
    if localized is not None:
        return localized
    return _EN_GOAL_DESCRIPTIONS.get(goal, "")
