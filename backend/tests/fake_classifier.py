"""A stand-in for the conversation classifier model: fixed labels for the phrases the tests send.
Anything else gets None, as when the model is off."""
from app.services import conversation

LABELS = {
    "hello": "greeting", "hi there": "greeting", "hi": "greeting",
    "thanks": "thanks", "ok thanks": "thanks", "bye": "bye",
    "yes please": "yes", "ok": "yes", "yes": "yes",
    "next": "practice", "quiz me": "practice", "give me another question": "practice",
    "can you provide a different question": "practice", "something else": "practice",
    "give me a harder one": "harder", "an easier question": "easier", "give me an easier one": "easier",
    "i don't know": "idk", "idk": "idk",
    "what can you do": "menu", "which topics can i learn": "menu", "how can you help me": "menu",
    "what can you help me with": "menu", "who are you": "menu",
    "example please": "example",
    "what is a percentage": "explain",
    "you are giving the same question again and again": "repeat",
    "where are we": "where", "which topic are we on": "where", "what are we studying now": "where",
    "what topic are we discussing": "where", "which chapter are we in": "where", "what's the current topic": "where",
    "which topic did we select": "where", "tell me the topic we are on": "where", "can you tell me where we are": "where",
    "what topic am i on": "where", "what is the current topic": "where",
}


def fake_classify(text: str, question: str = "") -> str | None:
    return LABELS.get(conversation.normalize(text))


PATH_LABELS = {
    "back to the main topic": "main_topic", "go back to the main topic": "main_topic",
    "back to the previous topic": "resume", "i'm ready to go back": "resume",
    "start from the very basics": "deepest",
    "got it": "understood", "i understand now": "understood", "ok, that makes sense": "understood",
    "ok, i get it now": "understood",
    "go back to the basics": "basics", "can we revise the basics": "basics",
    "what are the prerequisites": "prerequisites", "what should i know first": "prerequisites",
    "no, you only explain": "explain", "just tell me": "explain",
}


def fake_classify_path(text: str, detour: bool = False) -> str | None:
    """A stand-in for socratic.classify_path (the lesson-movement model call)."""
    return PATH_LABELS.get(conversation.normalize(text))
