"""Rules of the automatic passage builder (stdlib only; a word counter stands in for the tokenizer)."""
import unittest
from build_passages import build, tidy_latex

SID = "ncert-en-science-g7-test-07"
SOURCE = dict(source_id=SID, sha256="a" * 64, source_url="https://example.org/x.pdf", book_title="Curiosity",
              subject="science", grade="7", chapter_title="Heat Transfer in Nature")


def block(n, text, kind="prose", page=1, reasons=None):
    return dict(block_id=f"{SID}:p{page:03d}:h:h:b{n:03d}", source_id=SID, page_number=page, cleaned_text=text, cleaned_latex="",
                content_role="chapter_content", removed=False, content_type=kind, quarantine_reasons=reasons or [])


def run(blocks, roles=None, section_map=None, unresolved=()):
    roles = {b["block_id"]: dict(role=(roles or {}).get(b["block_id"], "content")) for b in blocks}
    order = {b["block_id"]: i for i, b in enumerate(blocks)}
    count = lambda t: len(t.split())
    return build(blocks, roles, {SID: SOURCE}, order, count, section_map or {}, {SID: 88}, set(unresolved), "v1", "rev")


LONG = "Heat flows from a hotter object to a colder object when the two are in contact with each other. " * 3


class PassageRules(unittest.TestCase):
    def test_merges_blocks_under_one_section_and_maps_concept(self):
        blocks = [block(1, "7.1 Conduction of Heat", "heading"), block(2, LONG), block(3, LONG)]
        passages, _, concepts = run(blocks, section_map={SID: {"7.1": "conduction"}})
        self.assertEqual(len(passages), 1)
        self.assertEqual(passages[0]["concept_ids"], ["conduction"])
        self.assertEqual(passages[0]["block_ids"], [b["block_id"] for b in blocks])
        self.assertEqual(passages[0]["printed_page_labels"], [89])
        self.assertEqual(concepts, [])

    def test_new_section_starts_new_passage_with_heading_concept(self):
        blocks = [block(1, "7.1 Conduction of Heat", "heading"), block(2, LONG), block(3, "7.2 Convection"), block(4, LONG)]
        passages, _, concepts = run(blocks, section_map={SID: {"7.1": "conduction"}})
        self.assertEqual([p["section_number"] for p in passages], ["7.1", "7.2"])
        self.assertEqual(concepts[0]["title"], "Convection")
        self.assertEqual(passages[1]["concept_ids"], [concepts[0]["concept_id"]])

    def test_questions_figures_noise_and_unresolved_never_enter(self):
        blocks = [block(1, "7.1 Conduction", "heading"), block(2, LONG), block(3, "1. Why does a metal spoon get hot?"),
                  block(4, "figure", "diagram/image"), block(5, "95"), block(6, "Price is  50 " + LONG),
                  block(7, LONG + " costs 5"), block(8, "Figure it Out", "heading"), block(9, LONG + " boxed")]
        passages, excluded, _ = run(blocks, roles={blocks[2]["block_id"]: "question"}, unresolved=[blocks[6]["block_id"]])
        used = {b for p in passages for b in p["block_ids"]}
        for i in (2, 3, 4, 5, 6, 8):
            self.assertNotIn(blocks[i]["block_id"], used)
        for reason in ("role_question", "figure", "page_number_or_running_head", "unreadable_symbols", "unresolved_currency", "question_box_or_teacher_note"):
            self.assertIn(reason, excluded)

    def test_short_fragment_joins_previous_passage(self):
        blocks = [block(1, "7.1 Conduction", "heading"), block(2, LONG), block(3, "Teacher’s Note", "heading"),
                  block(4, "Ask the class."), block(5, "Good conductors", "heading"), block(6, "Metals conduct heat well.")]
        passages, _, _ = run(blocks)
        self.assertEqual(len(passages), 1)
        self.assertIn("Metals conduct heat well.", passages[0]["text"])
        self.assertNotIn("Ask the class", passages[0]["text"])

    def test_tidy_latex_is_whitespace_only(self):
        self.assertEqual(tidy_latex(r"\frac { 1 0 } { 2 7 } and \operatorname { i s }"), r"\frac{10}{27} and \operatorname{is}")
        self.assertEqual(tidy_latex("inﬁ ltration"), "infiltration")

    def test_actual_tokenizer_excludes_oversize_blocks_without_truncation(self):
        from tokenizers import Tokenizer
        from build_content_pack import MODEL_DIR
        tokenizer=Tokenizer.from_file(str(MODEL_DIR/'tokenizer.json'));tokenizer.no_truncation();tokenizer.no_padding()
        blocks=[block(1,'7.1 Conduction','heading'),block(2,LONG),block(3,'radiation '*600)]
        roles={b['block_id']:{'role':'content'} for b in blocks}
        order={b['block_id']:i for i,b in enumerate(blocks)}
        passages,excluded,_=build(blocks,roles,{SID:SOURCE},order,lambda t:len(tokenizer.encode(t).ids),{}, {},set(),'v1','rev')
        self.assertEqual(excluded['oversize_single_block'],1)
        self.assertNotIn(blocks[-1]['block_id'],{bid for p in passages for bid in p['block_ids']})
        self.assertTrue(passages and all(p['token_count']==len(tokenizer.encode(p['text']).ids)<=400 for p in passages))


if __name__ == "__main__":
    unittest.main()
