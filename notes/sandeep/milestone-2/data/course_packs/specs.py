"""Hand-written course-pack specs: concepts, prerequisite links and practice questions.

Contains no textbook text. Each concept points to the NCERT chapter that teaches it;
build_course_packs.py attaches the matching text from that chapter.

Practice questions are written by the team in the style of the NCERT exercises. Where a
question has an `expr`, its answer is computed in code (so it cannot be mistyped);
otherwise the answer is typed in by hand (17 of the 70 questions) and was checked by the author.

Level 1 note: NCERT has no Class 6-10 chapter on plain multiplication and division (that is Class 3-5
content, which we did not process). The concept points to Class 6 chapter 3 (Number Play), the closest
chapter, and its attached text is general number-operations text, not a lesson on the topic.
Levels: 1 = foundations, 2 = builds on 1, 3 = builds on 2, 4 = builds on 3.
"""


class Q:
    def __init__(self, text, ans=None, hint="", difficulty=1, expr=None, dec=False):
        self.text, self.ans, self.hint, self.difficulty, self.expr, self.dec = text, ans, hint, difficulty, expr, dec


def C(id, name, level, cls, chapter, prereqs, keywords, questions):
    return dict(id=id, name=name, level=level, cls=cls, chapter=chapter, prerequisites=prereqs,
                keywords=keywords, questions=questions)


MATHS = dict(id="ncert-maths", title="NCERT Mathematics (classes 6-8)", subject="Mathematics", concepts=[
    C("multiplication_division", "Whole-number operations (multiplication and division)", 1, 6, 3, [],
      ["operations", "multiplication", "division", "product", "numbers"],
      [Q("What is 12 x 7?", expr="12*7", hint="Think of 12 groups of 7."),
       Q("What is 100 / 20?", expr="F(100,20)", hint="How many 20s make 100?"),
       Q("What is 144 / 12?", expr="F(144,12)", hint="How many 12s fit in 144?"),
       Q("A packet has 8 pencils. How many pencils are in 15 packets?", expr="8*15", hint="15 groups of 8.", difficulty=2),
       Q("What is 360 / 9?", expr="F(360,9)", hint="9 x 4 = 36, so what is 9 x 40?", difficulty=2)]),
    C("multiples_factors", "Multiples and factors", 1, 6, 5, ["multiplication_division"],
      ["factor", "multiple", "prime", "divisible"],
      [Q("What is the HCF of 12 and 18?", expr="math.gcd(12,18)", hint="List the factors of both numbers."),
       Q("What is the LCM of 4 and 6?", expr="math.lcm(4,6)", hint="List multiples of 6 until one is also a multiple of 4."),
       Q("How many factors does 12 have?", ans="6", hint="Pair up numbers that multiply to 12, and count each number once."),
       Q("Is 91 a prime number? (yes/no)", ans="no", hint="Try dividing by 7.", difficulty=2),
       Q("What is the smallest prime number greater than 20?", ans="23", hint="Check 21 and 22 first.", difficulty=2)]),
    C("fractions", "Fractions", 2, 6, 7, ["multiplication_division", "multiples_factors"],
      ["fraction", "numerator", "denominator", "equivalent"],
      [Q("What is 1/5 of 50?", expr="F(1,5)*50", hint="Share 50 into 5 equal groups."),
       Q("What is 3/4 of 20?", expr="F(3,4)*20", hint="Find 1/4 of 20 first."),
       Q("Write 20/100 in simplest form.", expr="F(20,100)", hint="Divide the top and bottom by the same number."),
       Q("What is 1/2 + 1/4?", expr="F(1,2)+F(1,4)", hint="Make the denominators the same.", difficulty=2),
       Q("Which is larger, 3/5 or 2/3?", ans="2/3", hint="Write both with denominator 15.", difficulty=2),
       Q("What is 2/3 of 18?", expr="F(2,3)*18", hint="Find 1/3 of 18, then double it.", difficulty=2)]),
    C("integers", "Integers", 2, 6, 10, ["multiplication_division"],
      ["integer", "negative", "positive", "zero", "number line"],
      [Q("What is -3 + 8?", expr="-3+8", hint="Start at -3 on the number line and move 8 right."),
       Q("What is 5 - 8?", expr="5-8", hint="Move 8 to the left of 5."),
       Q("What is -6 - 2?", expr="-6-2", hint="Move 2 further left of -6."),
       Q("What is (-5) + (-7)?", expr="-5-7", hint="Both are to the left of zero.", difficulty=2),
       Q("Which is smaller, -7 or -3?", ans="-7", hint="Which is further left on the number line?", difficulty=2)]),
    C("decimals", "Decimals", 3, 7, 3, ["fractions"],
      ["decimal", "tenth", "hundredth", "point"],
      [Q("What is 0.5 + 0.25?", expr="F(1,2)+F(1,4)", dec=True, hint="Line up the decimal points."),
       Q("Write 3/4 as a decimal.", expr="F(3,4)", dec=True, hint="3 divided by 4."),
       Q("What is 3.6 - 1.45?", expr="F(36,10)-F(145,100)", dec=True, hint="Write 3.6 as 3.60.", difficulty=2),
       Q("Which is greater, 0.6 or 0.58?", ans="0.6", hint="Give both numbers the same number of decimal places, then compare.", difficulty=2),
       Q("What is 2.5 x 4?", expr="F(25,10)*4", dec=True, hint="2 x 4 and 0.5 x 4.", difficulty=2)]),
    C("working_with_fractions", "Multiplying and dividing fractions", 3, 7, 8, ["fractions"],
      ["multiplication of fractions", "division of fractions", "reciprocal", "product"],
      [Q("What is 2/3 x 3/4?", expr="F(2,3)*F(3,4)", hint="Multiply the tops, multiply the bottoms, then simplify."),
       Q("What is 5/6 x 12?", expr="F(5,6)*12", hint="Find 1/6 of 12 first."),
       Q("What is 1/2 divided by 1/4?", expr="F(1,2)/F(1,4)", hint="How many quarters fit in a half?", difficulty=2),
       Q("What is 3 divided by 3/5?", expr="3/F(3,5)", hint="Dividing by a fraction means multiplying by its reciprocal.", difficulty=2),
       Q("How many 1/4-litre glasses can be filled from 3 litres?", expr="3/F(1,4)", hint="How many quarters are in 1 litre?", difficulty=2)]),
    C("letter_numbers", "Expressions with letters", 3, 7, 4, ["multiplication_division"],
      ["letter-number", "expression", "variable", "pattern"],
      [Q("If a = 3, what is 2a + 5?", expr="2*3+5", hint="Replace a with 3."),
       Q("If x = 4, what is 3x - 2?", expr="3*4-2", hint="3x means 3 times x."),
       Q("A pencil costs p rupees. Write the cost of 6 pencils.", ans="6p", hint="6 groups of p."),
       Q("Write 'a number n increased by 7' as an expression.", ans="n + 7", hint="Increased by means add.", difficulty=2),
       Q("If n = 5, what is n x n + 1?", expr="5*5+1", hint="Square first, then add 1.", difficulty=2)]),
    C("ratio", "Ratio and proportion", 3, 8, 7, ["fractions"],
      ["ratio", "proportion", "comparing"],
      [Q("Simplify the ratio 12 : 18.", ans="2 : 3", hint="Divide both by their HCF."),
       Q("Divide 50 in the ratio 2 : 3. What is the larger share?", expr="50*F(3,5)", hint="There are 2 + 3 = 5 equal parts.", difficulty=2),
       Q("If 3 pens cost 15 rupees, what do 7 pens cost?", expr="F(15,3)*7", hint="Find the cost of one pen.", difficulty=2),
       Q("Are the ratios 2 : 3 and 4 : 6 equal? (yes/no)", ans="yes", hint="Simplify 4 : 6.")]),
    C("percentages", "Percentages", 3, 8, 7, ["fractions", "decimals"],
      ["percent", "per cent", "%", "discount", "profit"],
      [Q("What is 20% of 50?", expr="F(20,100)*50", hint="20% means 20 out of how many?", difficulty=2),
       Q("What is 15% of 60?", expr="F(15,100)*60", hint="Write 15% as a fraction first.", difficulty=2),
       Q("Write 25% as a fraction in simplest form.", expr="F(25,100)", hint="25 out of 100, then simplify."),
       Q("Write 3/5 as a percentage.", expr="F(3,5)*100", hint="Make the denominator 100.", dec=False),
       Q("A shirt costs 400 rupees. A 10% discount is given. What is the discount in rupees?", expr="F(10,100)*400", hint="Find 10% of 400.", difficulty=2),
       Q("What percent of 80 is 20?", expr="F(20,80)*100", hint="Write 20 out of 80 as a fraction, then out of 100.", difficulty=3)]),
    C("linear_equations", "Linear equations in one variable", 4, 8, 2, ["letter_numbers", "integers", "fractions"],
      ["equation", "solve", "solution", "variable", "transposing"],
      [Q("Solve x + 7 = 15.", expr="15-7", hint="What do you subtract from both sides?"),
       Q("Solve 3x = 21.", expr="F(21,3)", hint="Divide both sides by 3."),
       Q("Solve 2x + 3 = 11.", expr="F(11-3,2)", hint="Remove the 3 first.", difficulty=2),
       Q("Solve 5x - 4 = 21.", expr="F(21+4,5)", hint="Add 4 to both sides first.", difficulty=2),
       Q("Solve x/4 = 6.", expr="6*4", hint="Multiply both sides by 4.", difficulty=2),
       Q("Solve 3(x - 2) = 12.", expr="F(12,3)+2", hint="Divide both sides by 3 first.", difficulty=3)]),
])

SCIENCE = dict(id="ncert-science", title="NCERT Science (motion and force, classes 6-9)", subject="Science", concepts=[
    C("length_and_motion", "Measuring length and types of motion", 1, 6, 5, [],
      ["length", "motion", "metre", "periodic", "rectilinear"],
      [Q("What is the SI unit of length?", ans="metre", hint="It is the base SI unit used to measure distance."),
       Q("How many centimetres are in 2 metres?", expr="2*100", hint="1 metre = 100 cm."),
       Q("The to-and-fro motion of a swing is called what kind of motion?", ans="periodic", hint="Notice that the swing keeps returning to the same position again and again.", difficulty=2)]),
    C("time_and_speed", "Time and speed", 2, 7, 8, ["length_and_motion"],
      ["speed", "time", "distance", "km/h", "average"],
      [Q("A car covers 120 km in 2 hours. What is its speed in km/h?", expr="F(120,2)", hint="Speed = distance / time."),
       Q("A cyclist moves at 15 km/h. How far does the cyclist go in 3 hours?", expr="15*3", hint="Distance = speed x time."),
       Q("A train travels 300 km at 60 km/h. How many hours does it take?", expr="F(300,60)", hint="Time = distance / speed.", difficulty=2)]),
    C("force_pressure", "Force and pressure", 3, 8, 8, ["time_and_speed"],
      ["force", "pressure", "newton", "area", "pascal"],
      [Q("What is the SI unit of force?", ans="newton", hint="Force = mass x acceleration, so its unit is kg m/s^2, which has a special name."),
       Q("What is the pressure when a force of 60 N acts on an area of 2 square metres (in pascals)?", expr="F(60,2)", hint="Pressure = force / area."),
       Q("When the same force acts on a smaller area, does the pressure increase or decrease?", ans="increase", hint="Think of a sharp knife versus a blunt one.", difficulty=2)]),
    C("describing_motion", "Describing motion: speed and acceleration", 3, 9, 4, ["time_and_speed"],
      ["acceleration", "velocity", "speed", "displacement", "graph"],
      [Q("An object moves 20 m in 4 s. What is its average speed in m/s?", expr="F(20,4)", hint="Distance divided by time."),
       Q("A car speeds up from 10 m/s to 30 m/s in 5 s. What is its acceleration in m/s^2?", expr="F(30-10,5)", hint="Acceleration = change in velocity / time.", difficulty=2),
       Q("What does the slope of a distance-time graph give?", ans="speed", hint="Slope = change in the vertical value / change in the horizontal value. What do the two axes show?", difficulty=2)]),
    C("forces_affect_motion", "How forces affect motion", 4, 9, 6, ["force_pressure", "describing_motion"],
      ["newton", "law of motion", "force", "mass", "acceleration", "inertia"],
      [Q("A force of 20 N acts on a 4 kg mass. What is the acceleration in m/s^2?", expr="F(20,4)", hint="F = m x a."),
       Q("What force gives a 5 kg mass an acceleration of 3 m/s^2 (in newtons)?", expr="5*3", hint="F = m x a."),
       Q("Which of Newton's laws is written F = ma?", ans="second", hint="Recall which of the three numbered laws links a force to the acceleration it produces.", difficulty=2)]),
    C("work_energy", "Work and energy", 4, 9, 7, ["forces_affect_motion"],
      ["work", "energy", "joule", "kinetic", "potential"],
      [Q("How much work does a 10 N force do in moving an object 5 m in its own direction (in joules)?", expr="10*5", hint="Work = force x distance."),
       Q("What is the SI unit of work and energy?", ans="joule", hint="Work = force x distance, so its unit is N m, which has a special name."),
       Q("What is the kinetic energy of a 2 kg object moving at 3 m/s (in joules)? Use KE = 1/2 x m x v^2.", expr="F(1,2)*2*3**2", hint="Square the speed first.", difficulty=3)]),
])

PACKS = [MATHS, SCIENCE]
