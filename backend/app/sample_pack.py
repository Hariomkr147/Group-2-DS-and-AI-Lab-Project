"""Small illustrative NCERT-style course pack, loaded at startup for development.

Real packs are ingested through POST /courses. Contents here are placeholders
written by the team, not text from the textbooks.
"""
from .schemas import Concept, CoursePack, Material, Question

SAMPLE_PACK = CoursePack(
    id="ncert-maths",
    title="NCERT Mathematics (sample)",
    subject="Mathematics",
    concepts=[
        Concept(
            id="multiplication", name="Multiplication", level=1,
            materials=[Material(source="NCERT Mathematics", page="to fill",
                                text="Multiplication is repeated addition of equal groups.")],
            questions=[Question(id="mul-1", text="What is 4 x 5?", answer="20",
                                hint="Add 4 five times.")],
        ),
        Concept(
            id="division", name="Division", level=2, prerequisites=["multiplication"],
            materials=[Material(source="NCERT Mathematics", page="to fill",
                                text="Division shares a number into equal groups.")],
            questions=[Question(id="div-1", text="What is 100 / 20?", answer="5",
                                hint="How many 20s make 100?")],
        ),
        Concept(
            id="fractions", name="Fractions", level=2, prerequisites=["division"],
            materials=[Material(source="NCERT Mathematics", page="to fill",
                                text="A fraction shows a part of a whole. 1/5 of 50 means 50 shared into 5 equal parts.")],
            questions=[Question(id="frac-1", text="What is 1/5 of 50?", answer="10",
                                hint="Share 50 into 5 equal groups.")],
        ),
        Concept(
            id="percentages", name="Percentages", level=3, prerequisites=["fractions"],
            materials=[Material(source="NCERT Mathematics", page="to fill",
                                text="Percent means out of 100. 20% of 50 is 20/100 of 50.")],
            questions=[Question(id="pct-1", text="What is 20% of 50?", answer="10",
                                hint="20% means 20 out of how many?", difficulty=2)],
        ),
    ],
)
