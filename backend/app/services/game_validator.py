"""
Game HTML Validator — two-level validation system.

Level 1: Static analysis (Python) — fast, catches common patterns
Level 2: Runtime execution (Node.js + jsdom) — catches actual JS errors

Both levels run in the generation pipeline before a game is saved.
"""

import asyncio
import json
import logging
import os
import re
import tempfile

logger = logging.getLogger(__name__)

# Path to the Node.js runtime validator script (sibling to backend/)
_RUNTIME_VALIDATOR_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "tools", "validate_runtime.js"
)


# ---------------------------------------------------------------------------
# Level 1 — Static Analysis
# ---------------------------------------------------------------------------


def static_validate(html: str) -> tuple[bool, list[str]]:
    """
    Быстрый статический анализ HTML-игры.
    Возвращает (passed, list_of_warnings).
    Warnings не блокируют, но передаются в retry-промпт.
    """
    warnings: list[str] = []

    # Extract JavaScript from <script> tags
    scripts = re.findall(r"<script[^>]*>(.*?)</script>", html, re.DOTALL | re.IGNORECASE)
    js_code = "\n".join(scripts)

    if not js_code.strip():
        return False, ["No JavaScript found in game HTML"]

    # --- Check 1: Uninitialized array declarations used later ---
    # Find `let/var/const x, y, z;` patterns where variables are later
    # used with array methods (.forEach, .map, .filter, .push, .length, [i])
    _check_uninitialized_arrays(js_code, warnings)

    # --- Check 2: Top-level ctx access without guard ---
    _check_canvas_context(js_code, warnings)

    # --- Check 3: requestAnimationFrame at top level ---
    _check_raf_at_top_level(js_code, warnings)

    is_critical = any("[CRITICAL]" in w for w in warnings)
    return not is_critical, warnings


def _check_uninitialized_arrays(js_code: str, warnings: list[str]) -> None:
    """Detect `let x, y;` where x or y is later used as an array."""
    # Find all `let/var/const` declarations that use comma-separated names without assignment
    # Pattern: `let name1, name2, name3;` or `let name1, name2 = value, name3;`
    decl_pattern = re.compile(
        r"\b(let|var|const)\s+([^;{]+);",
        re.MULTILINE,
    )

    array_methods = [
        ".forEach",
        ".map",
        ".filter",
        ".reduce",
        ".find",
        ".some",
        ".every",
        ".push",
        ".pop",
        ".shift",
        ".unshift",
        ".splice",
        ".slice",
        ".length",
        ".includes",
        ".indexOf",
        ".concat",
        ".sort",
        ".reverse",
        ".fill",
        ".flat",
        ".flatMap",
        ".join",
    ]

    # Patterns that indicate iterable usage
    # Use negative lookahead for property access (`.trail`, `[0]`) to avoid false positives
    # on objects like `for (let t of cat.trail)` — cat is an object, not iterable
    iterable_patterns = [
        # `for (let x of name)` — name IS the iterable
        r"for\s*\(\s*(?:let|var|const)\s+\w+\s+of\s+{name}\s*[)\s]",
        # `for (let x in name)` — name IS the object
        r"for\s*\(\s*(?:let|var|const)\s+\w+\s+in\s+{name}\s*[)\s]",
        # `[...name]` — array spread
        r"\[\.\.\.{name}\s*\]",
    ]

    for match in decl_pattern.finditer(js_code):
        parts = match.group(2).split(",")
        for part in parts:
            part = part.strip()
            # Skip if it has an assignment
            if "=" in part:
                continue
            var_name = part.strip()
            if not re.match(r"^[a-zA-Z_$][a-zA-Z0-9_$]*$", var_name):
                continue

            # Skip single-char variables — too many false positives
            # (e.g., `s` matches inside `eggs.push`)
            if len(var_name) < 2:
                continue

            # Check if this variable is used with array methods
            # Use word boundary \b to avoid matching inside other identifiers
            found_method = False
            for method in array_methods:
                pattern = r"\b" + re.escape(var_name) + re.escape(method)
                if re.search(pattern, js_code):
                    warnings.append(
                        f"[CRITICAL] Variable '{var_name}' declared without initialization "
                        f"but used with '{method}'. Initialize as: {var_name} = []"
                    )
                    found_method = True
                    break

            if found_method:
                continue

            # Check iterable usage (for...of, for...in, spread)
            for ip in iterable_patterns:
                if re.search(ip.format(name=re.escape(var_name)), js_code):
                    warnings.append(
                        f"[CRITICAL] Variable '{var_name}' declared without initialization "
                        f"but used in for...of/for...in loop. Initialize as: {var_name} = []"
                    )
                    break


def _check_canvas_context(js_code: str, warnings: list[str]) -> None:
    """Check if canvas context is obtained outside of a function (top-level)."""
    # Find getContext calls
    ctx_matches = list(re.finditer(r"(\w+)\s*=\s*\w+\.getContext\(", js_code))
    for ctx_match in ctx_matches:
        pos = ctx_match.start()
        # Simple heuristic: count braces before this position
        before = js_code[:pos]
        open_braces = before.count("{")
        close_braces = before.count("}")
        if open_braces <= close_braces:
            # At top level
            warnings.append(
                "[WARNING] Canvas context obtained at top level — may fail if DOM not ready. "
                "Move getContext() inside DOMContentLoaded or init()."
            )


def _check_raf_at_top_level(js_code: str, warnings: list[str]) -> None:
    """Check if requestAnimationFrame is called at top level (outside functions)."""
    for match in re.finditer(r"requestAnimationFrame\s*\(", js_code):
        pos = match.start()
        before = js_code[:pos]
        open_braces = before.count("{")
        close_braces = before.count("}")
        if open_braces <= close_braces:
            warnings.append(
                "[WARNING] requestAnimationFrame called at top level — "
                "game loop may start before init() is called by user."
            )


# ---------------------------------------------------------------------------
# Level 2 — Runtime Validation (Node.js + jsdom)
# ---------------------------------------------------------------------------


async def runtime_validate(html: str, timeout_sec: int = 5) -> tuple[bool, list[str]]:
    """
    Запускает HTML в jsdom через Node.js и ловит ошибки JavaScript.
    Возвращает (passed, list_of_errors).
    """
    validator_path = os.path.abspath(_RUNTIME_VALIDATOR_PATH)
    if not os.path.exists(validator_path):
        logger.warning("Runtime validator script not found at %s, skipping", validator_path)
        return True, []

    # Write HTML to temp file
    fd, tmp_path = tempfile.mkstemp(suffix=".html")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(html)

        proc = await asyncio.create_subprocess_exec(
            "node",
            validator_path,
            tmp_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_sec)
        except TimeoutError:
            proc.kill()
            await proc.wait()
            return True, ["[WARNING] Runtime validation timed out — game may be OK"]

        output = stdout.decode("utf-8", errors="replace").strip()
        if not output:
            logger.warning("Runtime validator returned empty output")
            return True, []

        try:
            result = json.loads(output)
        except json.JSONDecodeError:
            logger.warning("Runtime validator returned invalid JSON: %s", output[:200])
            return True, []

        errors = result.get("errors", [])
        passed = result.get("passed", len(errors) == 0)

        return passed, errors

    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Combined validation
# ---------------------------------------------------------------------------


async def full_validate(html: str) -> tuple[bool, list[str]]:
    """
    Run both static and runtime validation.
    Returns (passed, all_issues).
    """
    static_ok, static_issues = static_validate(html)

    # If static analysis found critical issues, no need for runtime
    if not static_ok:
        return False, static_issues

    runtime_ok, runtime_issues = await runtime_validate(html)

    all_issues = static_issues + runtime_issues
    passed = static_ok and runtime_ok

    return passed, all_issues
