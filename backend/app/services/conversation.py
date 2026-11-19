"""Everyday conversation: greetings, thanks, "yes", "next", "I don't know", topic menus.

The intent classifier is rarely confident on these short messages, so the tutor matches them here first.
Pure text matching, no database. `tutor.py` decides what to answer.
"""
import re

_UNITS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen "
    "sixteen seventeen eighteen nineteen".split())}
_TENS = {w: 10 * i for i, w in enumerate("_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()) if w != "_"}

_KINDS = (
    ("greeting", r"(?:(?:can|could) you )?(?:say )?(?:hi+|hello+|hey+|heya|namaste|good (?:morning|afternoon|evening))"
                 r"(?: (?:there|tutor|sir|mam|ma'am|everyone|to me))*"),
    ("bye", r"bye|goodbye|good ?night|see you(?: later| soon)?|talk later"),
    ("thanks", r"(?:ok(?:ay)? )?(?:thanks?(?: you)?(?: (?:a lot|so much|tutor))?|thx|ty)(?: (?:that helps|got it))?"
               r"|got it|understood|i understand|makes sense|that helps|that helped|cool|nice|great|awesome|perfect"),
    ("idk", r"(?:i )?(?:don'?t|do not) know|idk|no idea|i have no idea|not sure|i'?m not sure|dunno|no clue|i give up"
            r"|i can'?t(?: do (?:it|this))?"),
    ("menu", r"help(?: me)?|what can you do|what do you do|how does this work|how do i use this"
             r"|(?:what|which) topics?(?: do you (?:have|cover))?(?: can i (?:learn|study))?"
             r"|what can i (?:learn|study|ask)|(?:show|list) (?:me )?(?:the )?(?:topics|concepts)|topics|menu|options"),
    ("harder", r"(?:(?:give me|try|i want|can i have) )?(?:a |an )?(?:harder|tougher|more difficult|challenging)"
               r"(?: (?:one|question|problem))?|make it harder|challenge me"),
    ("easier", r"(?:(?:give me|try|i want|can i have) )?(?:a |an )?(?:easier|simpler|more basic)"
               r"(?: (?:one|question|problem))?|make it easier|too (?:hard|difficult)|this is too (?:hard|difficult)"),
    ("example", r"(?:(?:can|could) you )?(?:(?:give|show) me )?(?:an? |another )?example(?: please)?"),
    ("practice", r"next(?: one| question)?|another(?: one| question)?|one more(?: question)?|more(?: questions?)?"
                 r"|(?:give me |ask me |show me )?(?:a |an |another |one )?(?:practice|new|different)(?: question| problem| one)?"
                 r"|quiz me|test me|ask me (?:a |another )?question|give me (?:a |another )?(?:question|problem|practice question)"
                 r"|continue|go on|move on|skip(?: this| it)?"),
    ("yes", r"yes|yeah|yep|yup|ya|sure|ok(?:ay)?|alright|fine|go ahead|let'?s go|(?:i'?m|i am) ready|ready|please"
            r"|(?:yes|ok(?:ay)?|sure) (?:please|sure|let'?s go)"),
    ("no", r"no|nope|nah|not now|no thanks|no thank you"),
)
_COMPILED = tuple((kind, re.compile(pattern)) for kind, pattern in _KINDS)
_NUMBERISH = r"[-+]?\d[\d.,/]*%?"
_IS_IT = re.compile(rf"is (?:it |the answer |that |this )?({_NUMBERISH}|[a-z -]+?)(?: correct| right| the (?:right )?answer)?")
_THAT_RIGHT = re.compile(rf"({_NUMBERISH}|[a-z -]+?),? (?:is (?:it|that|this) )?(?:correct|right)")
_EXPLAIN_PREFIX = re.compile(
    r"(?:(?:can|could) you )?(?:please )?(?:what(?:'s| is| are| does)|explain|tell me about|define|describe|"
    r"meaning of|how (?:does|do|is)|why (?:is|are|do|does)|[\w ]+ kya (?:hota )?hai|[\w ]+ ka matlab)\b")


def normalize(text: str) -> str:
    t = text.casefold().replace("’", "'")
    t = re.sub(r"[^\w\s'%/+=.,-]", " ", t)
    t = re.sub(r"\s+", " ", t).strip(" .,!?")
    return re.sub(r"^(?:please|pls) ", "", t)


def classify(text: str) -> str | None:
    """greeting, bye, thanks, idk, menu, harder, easier, example, practice, yes, no, or None."""
    t = normalize(text)
    if not t or len(t) > 60:
        return None
    return next((kind for kind, pattern in _COMPILED if pattern.fullmatch(t)), None)


def number_from_words(text: str) -> str | None:
    """'ten' -> '10', 'twenty five' -> '25', 'two hundred and fifty' -> '250'; None if it is not a number."""
    words = [w for w in re.split(r"[\s-]+", text.casefold().strip(" .!?")) if w and w != "and"]
    negative = bool(words) and words[0] in ("minus", "negative")
    words = words[1:] if negative else words
    if not words:
        return None
    total = current = 0
    for w in words:
        if w in _UNITS:
            current += _UNITS[w]
        elif w in _TENS:
            current += _TENS[w]
        elif w == "hundred":
            current = max(current, 1) * 100
        elif w == "thousand":
            total, current = total + max(current, 1) * 1000, 0
        else:
            return None
    return str(-(total + current) if negative else total + current)


def unwrap_answer(text: str) -> str | None:
    """'is 10 correct?' or '10, is that right?' -> '10'. Only numbers (or number words) count as answers."""
    t = normalize(text)
    for pattern in (_IS_IT, _THAT_RIGHT):
        m = pattern.fullmatch(t)
        if m:
            candidate = m[1].strip(' ,.')
            if re.fullmatch(_NUMBERISH, candidate) or number_from_words(candidate) is not None:
                return candidate
    return None


def explain_request(text: str) -> bool:
    """'what is a percentage?', 'explain fractions', 'tell me about division' (the topic is matched elsewhere)."""
    return bool(_EXPLAIN_PREFIX.match(normalize(text)))
