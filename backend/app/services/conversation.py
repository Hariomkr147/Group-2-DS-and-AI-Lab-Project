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
             r"|(?:how|what) (?:can|could|will|do) you (?:help|teach|do)(?: me)?(?: with)?(?: today)?"
             r"|what (?:can|could) you (?:help|teach)(?: me)?(?: with)?|how (?:can|do) i (?:use|learn from) you"
             r"|(?:who|what) are you|what is this(?: app)?|what do you (?:know|teach)"
             r"|(?:what|which) topics?(?: do you (?:have|cover))?(?: can i (?:learn|study))?"
             r"|what can i (?:learn|study|ask)|(?:show|list) (?:me )?(?:the )?(?:topics|concepts)|topics|menu|options"),
    ("harder", r"(?:(?:give me|try|i want|can i have) )?(?:a |an )?(?:harder|tougher|more difficult|challenging)"
               r"(?: (?:one|question|problem))?|make it harder|challenge me"),
    ("easier", r"(?:(?:give me|try|i want|can i have) )?(?:a |an )?(?:easier|simpler|more basic)"
               r"(?: (?:one|question|problem))?|make it easier|too (?:hard|difficult)|this is too (?:hard|difficult)"),
    ("example", r"(?:(?:can|could) you )?(?:(?:give|show) me )?(?:an? |another )?example(?: please)?"),
    ("practice", r"(?:(?:can|could|will) you |please )?(?:provide|give|show|ask|try|get|have|do)(?: me)?(?: a| an| another| one)?"
                 r"(?: (?:different|new|other|another|fresh))(?: question| problem| one)?(?: please)?"
                 r"|(?:a |an )?(?:different|new|other|fresh) (?:question|problem|one)(?: please)?|something (?:else|different)"
                 r"|next(?: one| question)?|another(?: one| question)?|one more(?: question)?|more(?: questions?)?"
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


_REPEAT_COMPLAINT = re.compile(
    r"\b(?:same (?:question|thing|hint)|repeat(?:ing|ed)?|again and again|over and over"
    r"|already (?:asked|answered|did|said))\b")


def complains_of_repeat(text: str) -> bool:
    """'you are giving the same question again and again', 'you keep repeating yourself'."""
    return bool(_REPEAT_COMPLAINT.search(normalize(text)))


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


_FILLER = {"only", "right", "correct", "answer", "is", "the", "it", "its", "it's", "yes", "no", "na", "oy", "ok", "okay",
           "sure", "so", "then", "my", "answers", "that", "this", "i", "think", "got", "just", "are", "isn't", "not", "equal",
           "equals", "hmm", "oh", "wow", "yeah", "yep", "right?", "a", "an", "and", "or", "also", "same", "again"}
_ANY_NUMBER = re.compile(r"[-+]?\d+(?:\.\d+)?(?:/\d+)?")


def loose_number(text: str, question_text: str = "") -> str | None:
    """The one number a short, chatty message gives as its answer: '20!', '20 only', '4x5 is 20 only no',
    '20 is correct answer only right?', 'twenty only'. Numbers already in the question are ignored. None if unclear."""
    t = normalize(text)
    if not t or len(t.split()) > 10:
        return None
    asked = {m for m in _ANY_NUMBER.findall(question_text)}
    found = [n for n in dict.fromkeys(_ANY_NUMBER.findall(t.replace(",", ""))) if n not in asked]
    if len(found) == 1:
        return found[0]
    if not found:
        words = [w for w in t.replace("-", " ").split() if w not in _FILLER]
        return number_from_words(" ".join(words)) if words else None
    return None


def explain_request(text: str) -> bool:
    """'what is a percentage?', 'explain fractions', 'tell me about division' (the topic is matched elsewhere)."""
    return bool(_EXPLAIN_PREFIX.match(normalize(text)))
