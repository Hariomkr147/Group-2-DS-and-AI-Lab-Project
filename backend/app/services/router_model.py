"""Shared features for training and serving the local message classifier."""

ARTIFACT_VERSION = 1


def format_context(message, *, course, subjects, concept=None, question=None, answer_type=None,
                   recent=(), grade=None):
    history = " ".join(f"{role}: {text[:350]}" for role, text in recent)
    grade_text = f" Selected class: {grade}." if grade else ""
    return (
        f"Student message: {message}\n"
        f"Course: {course}. Enabled subjects: {', '.join(subjects)}.{grade_text}\n"
        f"Current concept: {concept or 'none'}.\n"
        f"Pending assessment question: {question or 'none'}.\n"
        f"Expected answer type: {answer_type or 'none'}.\n"
        f"Recent conversation: {history}"
    )


def tfidf_features():
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.pipeline import FeatureUnion

    return FeatureUnion([
        ("words", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)),
        ("characters", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5),
                                     min_df=2, sublinear_tf=True)),
    ])


def classifiers():
    from sklearn.linear_model import LogisticRegression

    return {name: LogisticRegression(C=4, class_weight="balanced", max_iter=1000, random_state=42)
            for name in ("intent", "scope")}


def predict(encoder, heads, premise):
    features = encoder.transform([premise])
    predictions = {}
    for name, head in heads.items():
        probabilities = head.predict_proba(features)[0]
        best = int(probabilities.argmax())
        predictions[name] = (str(head.classes_[best]), float(probabilities[best]))
    return predictions
