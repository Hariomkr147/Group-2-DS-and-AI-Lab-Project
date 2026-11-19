"""AKT inference with the supplied skill map; DKT remains only for the legacy trainer."""
import hashlib
import json
from pathlib import Path

import torch
from torch import nn
from akt import AKT


class DKT(nn.Module):
    def __init__(self, n, emb=64, hid=128):
        super().__init__()
        self.emb = nn.Embedding(2 * n + 1, emb, padding_idx=2 * n)
        self.lstm = nn.LSTM(emb, hid, batch_first=True)
        self.out = nn.Linear(hid, n)

    def forward(self, x):
        h, _ = self.lstm(self.emb(x))
        return self.out(h)


class KnowledgeTracer:
    def __init__(self, folder):
        self.folder = Path(folder)
        self.model, self.mapping = None, {}
        self.status = 'Missing exported AKT weights and exact skill map'
        if not (self.folder / 'metadata.json').exists():
            return
        meta = json.loads((self.folder / 'metadata.json').read_text())
        weights = self.folder / 'akt_best.pt'
        if hashlib.sha256(weights.read_bytes()).hexdigest() != meta['weights_sha256']:
            raise ValueError('AKT weight checksum mismatch')
        skill_path = self.folder / 'skills.json'
        if hashlib.sha256(skill_path.read_bytes()).hexdigest() != meta['skills_sha256']:
            raise ValueError('AKT skill map checksum mismatch')
        skills = json.loads(skill_path.read_text())
        if [s['index'] for s in skills] != list(range(meta['n_skills'])):
            raise ValueError('AKT skill index ordering is invalid')
        if meta['interaction_encoding'] != 'skill_index + n_skills * correct':
            raise ValueError('Unsupported AKT encoding')
        self.n = meta['n_skills']
        self.max_history = meta['max_history']
        checkpoint = torch.load(weights, map_location='cpu', weights_only=True)
        if checkpoint['arch'] != 'AKT' or checkpoint['n_skills'] != self.n:
            raise ValueError('AKT checkpoint identity differs from the export')
        self.model = AKT(self.n, **checkpoint['kwargs'])
        self.model.load_state_dict(checkpoint['state_dict'], strict=True)
        self.model.eval()
        if not self.model.use_rasch or torch.count_nonzero(self.model.difficulty.weight[self.model.n_questions]):
            raise ValueError('Expected a neutral AKT difficulty entry for unseen questions')
        # Only named vocabulary matches are used; unmapped concepts never acquire guessed indices.
        # Prefer the general Percents skill over Percent Of for ratio-conversion checkpoints.
        aliases = {'fractions': ('fractions', 'unit fractions'),
                   'fraction_multiplication': ('multiplication fractions', 'multiplication and division fractions'),
                   'fraction_division': ('division fractions', 'multiplication and division fractions'),
                   'percentages': ('percents', 'percentages', 'percent of')}
        skill_map = {s['name'].strip().lower(): s['index'] for s in skills}
        for concept, names in aliases.items():
            hits = [skill_map[n] for n in names if n in skill_map]
            if hits:
                self.mapping[concept] = hits[0]
        self.status = f'AKT checkpoint; {len(self.mapping)} mapped topics'

    def predict(self, attempts):
        if self.model is None:
            return {}
        history = [(self.mapping[a['concept']], int(a['correct'])) for a in attempts
                   if a['concept'] in self.mapping][-self.max_history:]
        if not history:
            return {}
        indices = [skill for skill, _ in history]
        skills = torch.tensor([indices] * len(self.mapping), dtype=torch.long)
        answers = torch.tensor([[skill + self.n * correct for skill, correct in history]] * len(self.mapping), dtype=torch.long)
        targets = torch.tensor([indices[1:] + [index] for index in self.mapping.values()], dtype=torch.long)
        # shortcut: NCERT questions have no training IDs, use neutral difficulty until a validated question mapping exists.
        questions = torch.full_like(skills, self.model.n_questions)
        with torch.inference_mode():
            values = self.model(skills, answers, targets, ex_q=questions, tgt_q=questions)[:, -1].sigmoid().tolist()
        return dict(zip(self.mapping, values))
