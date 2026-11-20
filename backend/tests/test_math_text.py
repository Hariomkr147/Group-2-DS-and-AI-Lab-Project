import pytest

from app.services import ncert
from app.services.math_text import readable


@pytest.mark.parametrize("latex, plain", [
    (r"Recall that { \mathrm { i f } }   p ( x ) is", "Recall that if p(x) is"),
    (r"highest power of x in p ( \vec { x } )", "highest power of x in p(x)"),
    (r"$x ^ { 2 } + 8 x + 1 5$", "x² + 8x + 15"),
    (r"$\frac { p } { q }$", "p/q"),
    (r"$\frac{-b}{2a}$", "(-b)/(2a)"),
    (r"$\sqrt { 2 }$", "√2"),
    (r"$\angle \mathrm{PST} = 90 ^ { \circ }$", "∠ PST = 90°"),
    (r"$6 5 . 5 ^ { \circ }$", "65.5°"),
    (r"the $n ^ { t h }$ term", "the nth term"),
    (r"$\mathrm{AC_{1}B, AC_{2}B, \cdots}$", "AC₁B, AC₂B,..."),
    (r"$( \dot { \mathrm { H } } _ { 2 } \mathrm { S } )$", "(H₂ S)"),
    (r"$$42=2\times3\times7\  and \ 12=2\times2\times3$$", "42=2×3×7 and 12=2×2×3"),
    (r"V=220\;V and HOI=\_\_\_", "V=220 V and HOI=___"),
])
def test_ocr_latex_reads_as_plain_maths(latex, plain):
    assert readable(latex) == plain


def test_text_without_maths_is_unchanged():
    text = "A highly polished surface, such as a mirror, reflects most of the light (Fig. 9.1)."
    assert readable(text) == text


def test_passage_text_is_readable():
    row = {"content": r"Recall that if $p ( x )$ is a polynomial, $x ^ { 2 }$ has degree 2. ![](images/a.jpg)"}
    assert ncert.passage_text(row) == "Recall that if p(x) is a polynomial, x² has degree 2."
