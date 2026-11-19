"""Recognize checked wrong-method outputs; a number alone never confirms a diagnosis."""
import re
from fractions import Fraction

DATASET_REVISION = "2ae0839debf73c0ce7dd6578d8ea8b99e7be8631"


def numeric(value):
    value = value.strip()
    if not re.fullmatch(r"[-+]?\d{1,8}(?:\.\d{1,8})?(?:/\d{1,8})?", value):
        return None
    try:
        return Fraction(value)
    except (ValueError, ZeroDivisionError):
        return None


def match_methods(methods, response):
    value = numeric(response)
    if value is None:
        return []
    return [dict(misconception_id=mid, dataset_revision=DATASET_REVISION, method=method,
                 evidence="The answer equals this known wrong method's output", wrong_method_output=str(result),
                 status="candidate_only", needs_confirmation=True, persistent=False)
            for mid, method, result in methods if result == value]


def percentage_errors(percent, amount, response):
    p, n = Fraction(percent), Fraction(amount)
    if p <= 0 or n <= 0:
        return []
    methods = [("22482", "amount * percent_number without /100", n * p)]
    if p != 10:  # At 10%, division by 10 is also a valid correct method.
        methods.append(("26916", "amount / percent_number", n / p))
    return match_methods(methods, response)


def fraction_errors(left, right, operation, response):
    a, b = numeric(str(left)), numeric(str(right))
    if a is None or b is None or a <= 0 or b <= 0:
        return []
    methods = []
    if operation == "+":
        an, ad = map(int, str(left).split("/")) if "/" in str(left) else (a.numerator, a.denominator)
        bn, bd = map(int, str(right).split("/")) if "/" in str(right) else (b.numerator, b.denominator)
        methods.append(("19849", "add numerators and add denominators", Fraction(an + bn, ad + bd)))
    elif operation == "*" and b != 1:
        methods.append(("22666", "multiply by reciprocal of second fraction", a / b))
    elif operation == "/" and b != 1:
        methods.append(("23021", "change division to multiplication without reciprocal", a * b))
    return match_methods(methods, response)


def candidate_errors(question, response):
    if len(question) > 8000 or len(response) > 128:
        return []
    ratios=re.findall(r'(?<!\d)(\d{1,8})\s*:\s*(\d{1,8})(?!\d)',question)
    if len(ratios)==1 and re.search(r'percentage',question,re.I) and response.strip().endswith('%'):
        a,b=map(int,ratios[0])
        if a>0 and b>0:
            return match_methods([('14036','attach percent sign to decimal without multiplying by 100',Fraction(a,b))],response.strip()[:-1])
    percent = re.findall(r"(?<!\d)(\d{1,8}(?:\.\d{1,8})?)\s*\\?%\s*of\s*(\d{1,8}(?:\.\d{1,8})?)(?!\d)", question, re.I)
    if len(percent) == 1:
        return percentage_errors(*percent[0], response)
    text = re.sub(r"\\(?:c?frac)\s*\{\s*([0-9 ]{1,16})\s*\}\s*\{\s*([0-9 ]{1,16})\s*\}",
                  lambda m: m[1].replace(" ", "") + "/" + m[2].replace(" ", ""), question)
    text = text.replace("\\times", "×").replace("\\div", "÷")
    expressions = re.findall(r"(?<![\d/])(\d{1,8}/\d{1,8})\s*(\+|×|\*|÷|divided by|of)\s*(\d{1,8}/\d{1,8}|\d{1,8})(?![\d/])", text, re.I)
    if len(expressions) != 1:
        return []
    left, op, right = expressions[0]
    if numeric(left) is None or numeric(right) is None:
        return []
    return fraction_errors(left, right, "/" if op in {"÷", "divided by"} else "*" if op in {"×", "*", "of"} else "+", response)


def corroborated_errors(question, response, working):
    """shortcut: accept explicit arithmetic only; expand after labelled learner validation."""
    if not isinstance(working, str) or len(working) > 8000:
        return []
    number = r"[-+]?\d{1,8}(?:\.\d{1,8})?(?:/\d{1,8})?"
    equations = []
    for line in working.strip().splitlines():
        match = re.fullmatch(rf"\s*({number})\s*([+*/×÷])\s*({number})\s*=\s*({number})\s*", line)
        if not match:
            return []
        left, op, right, result = match.groups()
        a, b, c = numeric(left), numeric(right), numeric(result)
        if a is None or b is None or c is None or op in {'/', '÷'} and b == 0:
            return []
        actual = a+b if op == '+' else a*b if op in {'*', '×'} else a/b
        if actual != c:
            return []
        equations.append((a, op.replace('×', '*').replace('÷', '/'), b, c))
    matches = []
    for rule in candidate_errors(question, response):
        mid = rule['misconception_id']
        percent = re.search(r"(\d+(?:\.\d+)?)\s*\\?%\s*of\s*(\d+(?:\.\d+)?)", question, re.I)
        fractions = re.findall(r"(?<![\d/])(\d+/\d+)(?![\d/])", question)
        supported = False
        if mid=='14036':
            ratios=re.findall(r'(?<!\d)(\d{1,8})\s*:\s*(\d{1,8})(?!\d)',question)
            if len(ratios)==1:
                a,b=map(Fraction,ratios[0])
                supported=equations==[(a,'/',b,a/b)]
        elif percent and mid in {'22482', '26916'}:
            p, n = map(Fraction, percent.groups())
            supported = equations == [(n, '*' if mid == '22482' else '/', p, numeric(response))]
        elif len(fractions) == 2:
            a, b = map(Fraction, fractions)
            if mid in {'22666', '23021'}:
                supported = equations == [(a, '*', 1/b if mid == '22666' else b, numeric(response))]
            elif mid == '19849':
                an, ad = map(int, fractions[0].split('/'))
                bn, bd = map(int, fractions[1].split('/'))
                supported = equations == [(Fraction(an), '+', Fraction(bn), Fraction(an+bn)),
                                           (Fraction(ad), '+', Fraction(bd), Fraction(ad+bd))]
        if supported:
            matches.append({**rule, 'evidence': 'Explicit learner equations reproduce this wrong method; arithmetic checked exactly.'})
    return matches


if __name__ == "__main__":
    assert {r["misconception_id"] for r in percentage_errors(20, 50, "2.5")} == {"26916"}
    assert {r["misconception_id"] for r in percentage_errors(20, 50, "1000")} == {"22482"}
    assert {r["misconception_id"] for r in fraction_errors("1/2", "1/3", "+", "2/5")} == {"19849"}
    assert {r["misconception_id"] for r in fraction_errors("1/2", "1/3", "*", "3/2")} == {"22666"}
    assert {r["misconception_id"] for r in fraction_errors("1/2", "1/3", "/", "1/6")} == {"23021"}
    assert not candidate_errors("1/2 + 1/3", "__import__('os')")
    assert not candidate_errors("1/2 + 1/0", "2/2")
    assert {r["misconception_id"] for r in fraction_errors("2/4", "1/3", "+", "3/7")} == {"19849"}
    assert not percentage_errors(10, 50, "5")
    assert not fraction_errors("1/2", "1", "*", "1/2")
    assert all(r["needs_confirmation"] and not r["persistent"] for r in candidate_errors("20% of 50", "2.5"))
    print("Five original-ID wrong-method rules and unsafe-input boundaries passed")
