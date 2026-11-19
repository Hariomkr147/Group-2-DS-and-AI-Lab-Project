"""Self-check for NCERT answer-key parsing and question linking (no AI text involved)."""
from extract_ncert_questions import parse_key, sim, needs_figure

# Figure-dependent questions are skipped; hints and plain text questions are kept.
assert needs_figure("10. What fraction of the whole square is shaded?")
assert needs_figure("Match each fractional unit with the correct picture: 1/6 1/8")
assert needs_figure("On a number line, draw lines of lengths 1/10 and 3/10.")
assert needs_figure("The figures below show different fractional units of a whole chikki.")
assert not needs_figure("2. Convert the following ratios to percentages. (a) 3 : 4 (b) 2 : 3")
assert not needs_figure("4. Find the distance between the first and last sapling. [Hint: Draw a rough diagram with four saplings]")

md = """# CHAPTER 7 — SOLUTIONS
**Section 7.1**
**Page no. 152**
**Figure it out**
**Q1. Three guavas together weigh 1 kg. Each guava will roughly weigh \\_\\_kg.**
Ans. $\\frac{1}{3}$
**Q4. The big fish weighs** $\\frac { 1 } { 2 }$ **kg. Together they weigh \\_\\_ kg.** Ans. $\\frac { 3 } { 4 }$
**Page No. 176**
1. Tenzin drinks half a glass of milk every day. How many glasses in a week?
Ans: 7/2 glasses.
2. A team of workers can make 1 km of a canal in 8 days.
Ans:
1/8 km.
"""
items = parse_key(md)
assert [(i["page_label"], i["number"]) for i in items] == [(152, 1), (152, 4), (176, 1), (176, 2)], items
assert items[0]["answer"] == "$\\frac{1}{3}$"
assert items[1]["answer"] == "$\\frac { 3 } { 4 }$" and "Ans" not in items[1]["question"]
assert items[3]["answer"] == "1/8 km."
assert sim("Three guavas together weigh 1 kg", "1. Three guavas together weigh 1 kg.") > 0.9
assert sim("Three guavas together weigh 1 kg", "5. Arrange these fraction words in order") < 0.3
print("ok")

# Regression: the real Grade 8 parser merges multiple numbered answers into one block.
from extract_ncert_questions import load_blocks
records = [b for b in load_blocks() if b['source_id'].endswith('g8-hemh1-r202425-an') and b['page'] == 5]
if records:
    parsed = parse_key(records, answer_only=True)
    first_exercise = [r for r in parsed if r['exercise'] == 'Exercise 7.1']
    assert {r['number'] for r in first_exercise} == set(range(1, 7)), first_exercise
    assert all(r['physical_pages'] == [5] and r['source_block_ids'] for r in first_exercise)
    assert '3.' not in next(r['answer'] for r in first_exercise if r['number'] == 2)
    print('real Grade 8 merged-answer and physical-page regression passed')
