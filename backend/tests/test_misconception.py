from app.services import misconception as m


def setup_function():
    m.reset_history()


def test_percent_error_uses_the_questions_own_numbers():
    assert m.detect("What is 30% of 70?", "7/3", "21") == "divides_by_the_percent"
    assert m.detect("What is 12% of 150?", "12.5", "18") == "divides_by_the_percent"


def test_unknown_error_is_not_guessed():
    assert m.detect("What is 30% of 70?", "2.3333", "21") is None


def test_correct_or_unreadable_answer_is_not_flagged():
    assert m.detect("What is 20% of 50?", "10", "10") is None
    assert m.detect("What is 20% of 50?", "no idea", "10") is None


def test_search_names_a_wrong_operation_in_an_unseen_question():
    d = m.diagnose("A train covers 150 km in 3 hours. What is its speed in km/h?", "450", "50")
    assert d.name == "multiplies_instead_of_dividing" and d.source == "search"


def test_repeated_error_is_recurring_and_more_confident():
    first = m.diagnose("What is 20% of 50?", "2.5", "10", "kid")
    again = m.diagnose("What is 15% of 60?", "4", "9", "kid")
    assert not first.recurring and again.recurring and again.confidence > first.confidence
