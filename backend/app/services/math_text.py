"""Turn the OCR's LaTeX (``$\\frac { p } { q }$``, ``\\mathrm { i s }``) into plain text a student can read in chat."""
import re

_SYMBOLS = {
    "times": "×", "div": "÷", "cdot": "·", "pm": "±", "mp": "∓", "leq": "≤", "le": "≤", "geq": "≥", "ge": "≥",
    "neq": "≠", "ne": "≠", "approx": "≈", "equiv": "≡", "cong": "≅", "sim": "~", "propto": "∝", "infty": "∞",
    "angle": "∠", "triangle": "△", "parallel": "||", "perp": "⊥", "circ": "°", "degree": "°", "prime": "′",
    "rightarrow": "→", "to": "→", "longrightarrow": "→", "leftarrow": "←", "leftrightarrow": "↔", "Rightarrow": "⇒",
    "implies": "⇒", "iff": "⇔", "rightleftharpoons": "⇌", "uparrow": "↑", "downarrow": "↓", "therefore": "∴",
    "because": "∵", "in": "∈", "notin": "∉", "subset": "⊂", "cup": "∪", "cap": "∩", "bigcap": "∩", "emptyset": "∅",
    "sum": "Σ", "prod": "Π", "bullet": "•", "ldots": "...", "cdots": "...", "dots": "...", "vert": "|", "mid": "|",
    "lfloor": "⌊", "rfloor": "⌋", "lceil": "⌈", "rceil": "⌉", "percent": "%",
    "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ε", "varepsilon": "ε", "theta": "θ",
    "lambda": "λ", "mu": "μ", "nu": "ν", "pi": "π", "rho": "ρ", "sigma": "σ", "tau": "τ", "phi": "φ", "chi": "χ",
    "xi": "ξ", "upsilon": "υ", "omega": "ω", "Gamma": "Γ", "Delta": "Δ", "Theta": "Θ", "Lambda": "Λ", "Sigma": "Σ",
    "Pi": "Π", "Phi": "Φ", "Omega": "Ω",
    "sin": "sin", "cos": "cos", "tan": "tan", "cot": "cot", "sec": "sec", "csc": "cosec", "log": "log",
}
# Upright-text commands: their argument is a word or a label.
_WORD_FONT = "mathrm|text|textrm|textbf|textit|operatorname|mbox|hbox"
# Commands whose one argument is shown as is (other fonts, accents, boxes).
_KEEP_ARG = ("mathbf|mathit|mathsf|mathtt|mathbb|mathcal|mathfrak|boldsymbol|pmb|bm|vec|dot|ddot|hat|widehat|"
             "tilde|widetilde|bar|overline|underline|boxed|textcircled|overrightarrow|overleftarrow|underbrace|"
             "overbrace|displaystyle")
_DROP = re.compile(r"\\(?:left|right|big|Big|bigg|Bigg|displaystyle|textstyle|scriptstyle|scriptsize|tiny|"
                   r"small|large|Large|rm|bf|it|limits|nolimits|hline|quad|qquad|space)(?![A-Za-z])|\\(?:cline|tag)\{[^{}]*\}|\\[,;:!> ]")
_SUPERSCRIPT = str.maketrans("0123456789+-=()n", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿ")
_SUBSCRIPT = str.maketrans("0123456789+-=()", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎")
_ARG = r"\s*\{([^{}]*)\}"
_MATH = re.compile(r"\$\$(.+?)\$\$|\$([^$\n]+?)\$|\\\((.+?)\\\)|\\\[(.+?)\\\]", re.S)


def _word(body: str) -> str:
    """Upright text the OCR spelled out letter by letter ("i s", "P S T") is one word again."""
    body = body.replace("~", " ").strip()
    return f" {body.replace(' ', '')} " if re.fullmatch(r"(?:[A-Za-z] )+[A-Za-z]", body) else f" {body} "


def _tight(text: str) -> str:
    """OCR spaces every token ("1 5", "p ( x )"): join digits back up and tidy brackets and scripts."""
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"([(\[]) ", r"\1", text)
    text = re.sub(r" ([)\],.;:!?′°¹²³⁰-⁹ⁿ₀-₉])", r"\1", text)
    text = re.sub(r"(?<=\d) (?=\d)", "", text)                  # "1 5" -> "15"
    text = re.sub(r"(?<=\d) (?=[a-z]\b)", "", text)             # "8 x" -> "8x"
    return re.sub(r"(?<=\w) \((?=[^()]{1,12}\))", "(", text)       # "p (x)" -> "p(x)"


def _script(body: str, table: dict, mark: str) -> str:
    body = body.strip()
    if re.fullmatch(r"(?:[A-Za-z0-9] )+[A-Za-z0-9]", body):
        body = body.replace(" ", "")                          # OCR spacing: "t h" -> "th"
    if mark == "^" and body in ("th", "st", "nd", "rd"):
        return body                                           # n^{th} reads as "nth"
    if body and all(ch in "0123456789+-=()n" if mark == "^" else ch in "0123456789+-=()" for ch in body):
        return body.translate(table)
    return f"{mark}{body}" if len(body) == 1 else f"{mark}({body})"


def _group(body: str) -> str:
    body = body.strip()
    return body if re.fullmatch(r"\d+(?:\.\d+)?|[A-Za-z][′°²³⁰-⁹]*|[A-Za-z]{2,}", body) else f"({body})"


def _plain(latex: str) -> str:
    text = latex
    text = re.sub(r"\\begin\{array\}\{[^{}]*\}|\\(?:begin|end)\{[a-z*]+\}", " ", text)
    text = text.replace("\\\\", "\n").replace("&", " ")
    text = re.sub(r"\\(?:hspace|vspace|hphantom|phantom)\*?\{[^{}]*\}", " ", text)
    text = _DROP.sub(" ", text)
    text = re.sub(r"\\([%$#&_{}])", r"\1", text)
    text = re.sub(r"\s*([\^_])\s*", r"\1", text)               # "x ^ { 2 }" -> "x^{2}"
    text = re.sub(r"(?<=\d) +(?=\d)|(?<=\d) *\. *(?=\d)", lambda m: "." if "." in m[0] else "", text)  # "6 5 . 5" -> "65.5"
    for _ in range(20):                                       # innermost groups first, until nothing changes
        before = text
        text = re.sub(r"\\(?:d|c|t)?frac" + _ARG + _ARG, lambda m: f"{_group(m[1])}/{_group(m[2])}", text)
        text = re.sub(r"\\sqrt\s*\[([^\]]*)\]" + _ARG, lambda m: f"{m[1].strip()}√{_group(m[2])}", text)
        text = re.sub(r"\\sqrt" + _ARG, lambda m: f"√{_group(m[1])}", text)
        text = re.sub(r"\\(?:overset|underset|stackrel)" + _ARG + _ARG, r"\2", text)
        text = re.sub(r"\\xrightarrow" + _ARG, " → ", text)
        text = re.sub(r"\\(?:" + _WORD_FONT + r")" + _ARG, lambda m: _word(m[1]), text)
        text = re.sub(r"\\(?:" + _KEEP_ARG + r")" + _ARG, r"\1", text)
        text = re.sub(r"\^\s*\{\s*\\circ\s*\}|\^\s*\\circ", "°", text)
        text = re.sub(r"\^" + _ARG, lambda m: _script(m[1], _SUPERSCRIPT, "^"), text)
        text = re.sub(r"_" + _ARG, lambda m: _script(m[1], _SUBSCRIPT, "_"), text)
        if text == before:                                    # no command left to apply: drop one layer of bare braces
            text = re.sub(r"(?<![A-Za-z])\{([^{}]*)\}", r"\1", text)
            if text == before:
                break
    text = re.sub(r"\^\s*([0-9n])", lambda m: m[1].translate(_SUPERSCRIPT), text)
    text = re.sub(r"_\s*([0-9])", lambda m: m[1].translate(_SUBSCRIPT), text)
    text = re.sub(r"\\over\b", "/", text)
    text = re.sub(r"\\([A-Za-z]+)", lambda m: _SYMBOLS.get(m[1], ""), text)
    text = text.replace("~", " ").replace("{", "").replace("}", "")
    return "\n".join(_tight(line) for line in text.split("\n") if line.strip())


def readable(text: str) -> str:
    """Plain-text maths for chat: LaTeX inside $...$ (and a stray bare command outside it) becomes readable symbols."""
    text = _MATH.sub(lambda m: _plain(next(g for g in m.groups() if g is not None)), text)
    if "\\" in text:
        text = re.sub(r"(?:\{\s*)?\\(?:[A-Za-z]+)(?:\s*\{[^{}]*\})*(?:\s*\})?", lambda m: _plain(m[0]), text)
        text = re.sub(r"\\[,;:!> ]", " ", text)               # LaTeX spacing outside $...$
        text = re.sub(r"\\([_`*|~+\-$#%])", r"\1", text)      # Markdown escapes the chat does not render
    text = re.sub(r"\b([A-Za-z]) \( ?(\w{1,3}) ?\)", r"\1(\2)", text)    # "p ( x )" -> "p(x)"
    return re.sub(r"(?<=\S)[ \t]{2,}", " ", text)
