import re

from better_profanity import profanity

profanity.load_censor_words()

# Phrases that are safe despite containing blocked substrings
SAFE_PHRASES = [
    "shoot baskets", "shoot hoops", "basketball shoot",
    "killer whale", "lady killer",
    "die roll", "dice", "roll the die",
    "hit the target", "hit the ball",
    "gun it", "water gun", "nerf gun", "laser gun",
    "bomb the test",
]

BLOCKED_INPUT_KEYWORDS = [
    "kill", "murder", "blood", "gore", "horror",
    "sex", "nude", "naked", "porn", "hentai",
    "drug", "cocaine", "heroin", "meth",
    "alcohol", "beer", "wine", "vodka", "whiskey",
    "gambling", "casino", "betting",
    "suicide", "self-harm",
    "terrorist", "racist", "nazi",
]

PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous",
    r"disregard\s+(all\s+)?instructions",
    r"you\s+are\s+now",
    r"forget\s+(all\s+)?your\s+rules",
    r"new\s+instructions?:",
    r"system\s*prompt",
]

PII_PATTERNS = [
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",  # email
    r"(?<!\d)(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{2,4}(?!\d)",  # phone
    r"\d{1,5}\s+\w+\s+(?:st|street|ave|avenue|blvd|boulevard|rd|road|dr|drive|ln|lane|ct|court)\b",  # address
]

PII_MESSAGE = (
    "It looks like you included personal information. "
    "Please don't include names, addresses, or phone numbers in your game ideas."
)

LEETSPEAK_MAP = str.maketrans("0134@$!", "oiieass")

FORBIDDEN_OUTPUT_PATTERNS = [
    (r"https?://", "external URL"),
    (r"//[a-zA-Z]", "protocol-relative URL"),
    (r"\bfetch\s*\(", "fetch() call"),
    (r"\bXMLHttpRequest\b", "XMLHttpRequest"),
    (r"\bWebSocket\b", "WebSocket"),
    (r"\bnavigator\.sendBeacon\b", "sendBeacon"),
    (r"\blocalStorage\b", "localStorage"),
    (r"\bsessionStorage\b", "sessionStorage"),
    (r"\bdocument\.cookie\b", "document.cookie"),
    (r"\beval\s*\(", "eval() call"),
    (r"\bFunction\s*\(", "Function() constructor"),
    (r"<iframe", "iframe tag"),
    (r"<form[^>]+action\s*=", "form action"),
    (r"\bnew\s+Function\s*\(", "new Function() constructor"),
    (r"\bimport\s*\(", "dynamic import"),
    (r"\bwindow\.open\s*\(", "window.open() call"),
    (r"javascript\s*:", "javascript: URI"),
    (r"data\s*:\s*text/html", "data:text/html URI"),
]


def _normalize(text: str) -> str:
    """Normalize text for keyword matching: lowercase, strip whitespace tricks, de-leetspeak."""
    text = text.lower()
    # Remove spaces between single chars: "k i l l" -> "kill"
    text = re.sub(r'(?<=\b\w)\s+(?=\w\b)', '', text)
    # Also handle "k.i.l.l" or "k-i-l-l"
    text = re.sub(r'(?<=\w)[.\-_]+(?=\w)', '', text)
    # Leetspeak substitution
    text = text.translate(LEETSPEAK_MAP)
    return text


def filter_input(prompt: str) -> tuple[bool, str]:
    """Check if user prompt is safe. Returns (is_safe, reason)."""
    # Check for PII
    for pattern in PII_PATTERNS:
        if re.search(pattern, prompt, re.IGNORECASE):
            return False, PII_MESSAGE

    # Check for prompt injection
    prompt_lower = prompt.lower()
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, prompt_lower):
            return False, "Prompt contains disallowed instructions"

    # Check profanity on original text
    if profanity.contains_profanity(prompt):
        return False, "Prompt contains inappropriate language"

    # Check safe phrases first — if the prompt matches a safe phrase, skip keyword blocking
    normalized = _normalize(prompt)
    for safe in SAFE_PHRASES:
        normalized = normalized.replace(safe.lower(), "")

    # Check blocked keywords on normalized text
    for keyword in BLOCKED_INPUT_KEYWORDS:
        if keyword in normalized:
            return False, "Prompt contains blocked content"

    return True, "ok"


def filter_output(html: str) -> tuple[bool, str]:
    """Check if generated HTML is safe. Returns (is_safe, reason)."""
    for pattern, description in FORBIDDEN_OUTPUT_PATTERNS:
        if re.search(pattern, html, re.IGNORECASE):
            return False, f"Generated HTML contains forbidden pattern: {description}"

    # Strip HTML tags and check visible text for profanity
    visible_text = re.sub(r"<[^>]+>", " ", html)
    if profanity.contains_profanity(visible_text):
        return False, "Generated HTML contains inappropriate language"

    return True, "ok"
