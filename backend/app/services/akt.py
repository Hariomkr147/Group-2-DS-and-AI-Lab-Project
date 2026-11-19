"""Loads the trained AKT knowledge tracer and predicts the next-answer chance for one concept.

Opt-in: set KT_MODEL=akt. It needs torch (the `rag` extra) and the files in backend/models/akt.
If anything is missing or fails, `get_tracer()` returns None and the learner model keeps using
smoothed accuracy. Only concepts listed in concept_skill_map.json are scored; others never get a
guessed skill.
"""
import csv
import hashlib
import json
import logging
import os
from pathlib import Path

log = logging.getLogger(__name__)

FOLDER = Path(__file__).resolve().parents[2] / "models" / "akt"
# SHA-256 of the exported files this wiring was checked against (checkpoint and skill map).
# Source: Mrityunjay's from-scratch ASSISTments 2009 run (notes/Mrityunjay Chakraborty), test AUC 0.779.
WEIGHTS_SHA256 = "4e42c91ffc5c0a86a9d2eebb3ea83dc69e6b1f372fdcfa35b61a88acc33fc1c9"
SKILLS_SHA256 = "6917720b8727a95aa904c6cee8052b1df829d4fc16d99e38cb72468d67eb3efc"
MAX_HISTORY = 199  # the model was trained on 200-step windows: 199 past answers plus the target


class Tracer:
    def __init__(self, folder: Path = FOLDER):
        import torch
        from .akt_net import AKT

        weights, skills = folder / "akt_best.pt", folder / "skill_map.csv"
        if hashlib.sha256(weights.read_bytes()).hexdigest() != WEIGHTS_SHA256:
            raise ValueError("AKT weights checksum mismatch")
        if hashlib.sha256(skills.read_bytes()).hexdigest() != SKILLS_SHA256:
            raise ValueError("AKT skill map checksum mismatch")
        rows = list(csv.DictReader(skills.read_text().splitlines()))
        if [int(r["mapped_index"]) for r in rows] != list(range(len(rows))):
            raise ValueError("AKT skill indices are not 0..n-1")
        info = json.loads((folder / "model_info.json").read_text())
        if info["model"] != "AKT" or info["n_skills"] != len(rows):
            raise ValueError("AKT checkpoint does not match the skill map")
        self.n = info["n_skills"]
        state = torch.load(weights, map_location="cpu", weights_only=True)  # bare state dict
        self.model = AKT(self.n, n_questions=info["n_questions"])  # default sizes match the export
        self.model.load_state_dict(state, strict=True)
        self.model.eval()
        mapping = json.loads((folder / "concept_skill_map.json").read_text())["map"]
        if any(not 0 <= i < self.n for i in mapping.values()):
            raise ValueError("concept_skill_map.json has an index outside the skill map")
        self.mapping: dict[str, int] = mapping
        self._torch = torch

    def predict(self, concept_id: str, attempts: list[tuple[str, bool]]) -> float | None:
        """Chance of a correct next answer on `concept_id`, from the learner's ordered (concept, correct)
        history. None when the concept is unmapped or no mapped answer exists yet."""
        target = self.mapping.get(concept_id)
        history = [(self.mapping[c], int(ok)) for c, ok in attempts if c in self.mapping][-MAX_HISTORY:]
        if target is None or not history:
            return None
        torch = self._torch
        skills = torch.tensor([[s for s, _ in history]], dtype=torch.long)
        answers = torch.tensor([[s + self.n * ok for s, ok in history]], dtype=torch.long)
        targets = torch.tensor([[s for s, _ in history][1:] + [target]], dtype=torch.long)
        # NCERT questions have no ASSISTments question id: use the neutral padding difficulty entry.
        questions = torch.full_like(skills, self.model.n_questions)
        with torch.inference_mode():
            return float(self.model(skills, answers, targets, ex_q=questions, tgt_q=questions)[0, -1].sigmoid())


_tracer: Tracer | None = None
_tried = False


def get_tracer() -> Tracer | None:
    """The shared tracer, or None when KT_MODEL is not 'akt' or it could not be loaded."""
    global _tracer, _tried
    if os.environ.get("KT_MODEL", "").lower() != "akt":
        return None
    if not _tried:
        _tried = True
        try:
            _tracer = Tracer()
        except Exception as exc:  # missing torch or files, checksum mismatch: fall back quietly
            log.warning("AKT unavailable, using smoothed accuracy: %s", exc)
    return _tracer
