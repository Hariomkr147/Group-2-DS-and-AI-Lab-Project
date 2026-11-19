"""Flag reproducible source-symbol and OCR hazards without approving text."""
import json
import random
import re
import sys
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / '00_setup_and_scope/code'))
from pipeline import ROOT, SOURCES, local_path, read_csv, read_jsonl, run_record, sha256

PUA_NEAR_NUMBER = re.compile(r'[\ue000-\uf8ff]\s*\d|\d\s*[\ue000-\uf8ff]')
SUSPICIOUS_HOUR = re.compile(r'\bh0ur\b', re.I)


def flags_for_page(native_text, cleaned_blocks):
    reasons = []
    if PUA_NEAR_NUMBER.search(native_text):
        reasons.append({'reason': 'native_private_use_glyph_near_number', 'block_ids': [],
                        'meaning': 'A source font glyph near a number may encode a symbol; compare original PDF.'})
    bad = [b['block_id'] for b in cleaned_blocks if SUSPICIOUS_HOUR.search(b['cleaned_text'] or b['cleaned_latex'] or '')]
    if bad:
        reasons.append({'reason': 'suspicious_h0ur_ocr', 'block_ids': bad,
                        'meaning': 'The letter o may have been misread as zero in a unit word.'})
    return reasons


def sample_pages(pages, seed=20261103):
    """Choose one chapter page per source, independent of input record order."""
    rng = random.Random(seed)
    sources = sorted({p['source_id'] for p in pages if p['content_role'] == 'chapter_content'})
    return [rng.choice(sorted((p for p in pages if p['source_id'] == sid and p['content_role'] == 'chapter_content'),
                              key=lambda p: p['page_number'])) for sid in sources]


def main():
    phase = ROOT / '06_eda_and_quality'
    page_path = ROOT / '04_extract_text_and_ocr/outputs/pages.jsonl'
    blocks_path = ROOT / '05_clean_and_preprocess/outputs/clean_blocks.jsonl'
    with run_record('06_eda_and_quality', [SOURCES, page_path, blocks_path]) as run:
        sources = {s['source_id']: s for s in read_csv(SOURCES)}
        pages = read_jsonl(page_path); blocks = read_jsonl(blocks_path)
        grouped = {}
        for block in blocks:
            grouped.setdefault((block['source_id'], block['page_number']), []).append(block)
        findings = []
        for sid in sorted({p['source_id'] for p in pages}):
            source_path = local_path(sources[sid]['local_path'])
            if sha256(source_path) != sources[sid]['sha256']:
                raise ValueError('Original source PDF differs from its manifest')
            with fitz.open(source_path) as document:
                for page in (p for p in pages if p['source_id'] == sid and p['content_role'] in {'chapter_content', 'private_answer'}):
                    number = page['page_number']
                    for flag in flags_for_page(document[number - 1].get_text(sort=False), grouped.get((sid, number), [])):
                        findings.append(dict(source_id=sid, source_sha256=sources[sid]['sha256'], physical_page=number,
                                             content_role=page['content_role'], **flag))
        output = phase / 'outputs/automatic_source_flags.json'
        output.write_text(json.dumps(dict(run_id=run['run_id'], status='flags_require_ai_source_check' if findings else 'no_flags_detected',
                                          findings=findings, limitations=['Flags are not automatic corrections or approvals',
                                          'A PUA glyph may be decorative; a missing flag does not establish transcription correctness',
                                          'This check does not prove reading order or diagram meaning']), indent=2) + '\n', encoding='utf-8')
        selection = phase / 'outputs/automatic_source_sample_selection.json'
        selection.write_text(json.dumps(dict(run_id=run['run_id'], seed=20261103,
            samples=[dict(source_id=p['source_id'], source_sha256=sources[p['source_id']]['sha256'],
                          physical_page=p['page_number']) for p in sample_pages(pages)],
            status='Selection for Codex source check; not an approval'), indent=2) + '\n', encoding='utf-8')
        run['outputs'].extend([output, selection]); run['counts'] = {'flags': len(findings), 'pages_flagged': len({(x['source_id'], x['physical_page']) for x in findings})}
        print(json.dumps(run['counts']))


if __name__ == '__main__':
    main()
