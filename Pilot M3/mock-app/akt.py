"""Inference architecture from the supplied AKT comparison notebook."""
import math

import torch
from torch import nn
from torch.nn import functional as F


class MonotonicAttention(nn.Module):
    def __init__(self, d_model, n_heads, dropout=0.1, kq_same=True):
        super().__init__()
        self.h, self.dk = n_heads, d_model // n_heads
        self.k_lin = nn.Linear(d_model, d_model)
        self.q_lin = self.k_lin if kq_same else nn.Linear(d_model, d_model)
        self.v_lin = nn.Linear(d_model, d_model)
        self.out_lin = nn.Linear(d_model, d_model)
        self.drop = nn.Dropout(dropout)
        self.gammas = nn.Parameter(torch.zeros(n_heads, 1, 1))

    def forward(self, q, k, v, allow_diagonal, zero_pad=False):
        batch, length, _ = q.shape
        split = lambda x: x.view(batch, length, self.h, self.dk).transpose(1, 2)
        q_, k_, v_ = split(self.q_lin(q)), split(self.k_lin(k)), split(self.v_lin(v))
        scores = torch.matmul(q_, k_.transpose(-1, -2)) / math.sqrt(self.dk)
        idx = torch.arange(length, device=q.device)
        i, j = idx.unsqueeze(1), idx.unsqueeze(0)
        allowed = (j <= i) if allow_diagonal else (j < i)
        with torch.no_grad():
            s = torch.softmax(scores.masked_fill(~allowed, -1e32), dim=-1) * allowed
            remaining = s.sum(dim=-1, keepdim=True) - s.cumsum(dim=-1)
            dist = (remaining * (i - j).abs().float()).clamp(min=0).sqrt()
        effect = torch.exp(-F.softplus(self.gammas) * dist).clamp(1e-5, 1e5)
        weights = torch.softmax((scores * effect).masked_fill(~allowed, -1e32), dim=-1)
        if zero_pad:
            weights = torch.cat([torch.zeros_like(weights[:, :, :1]), weights[:, :, 1:]], dim=2)
        out = torch.matmul(self.drop(weights), v_).transpose(1, 2).reshape(batch, length, -1)
        return self.out_lin(out)


class AKTBlock(nn.Module):
    def __init__(self, d_model, d_ff, n_heads, dropout, kq_same, use_ffn):
        super().__init__()
        self.attn = MonotonicAttention(d_model, n_heads, dropout, kq_same)
        self.ln1 = nn.LayerNorm(d_model)
        self.drop1 = nn.Dropout(dropout)
        self.use_ffn = use_ffn
        if use_ffn:
            self.ffn = nn.Sequential(nn.Linear(d_model, d_ff), nn.ReLU(), nn.Dropout(dropout),
                                     nn.Linear(d_ff, d_model))
            self.ln2 = nn.LayerNorm(d_model)
            self.drop2 = nn.Dropout(dropout)

    def forward(self, q, k, v, allow_diagonal, zero_pad=False):
        x = self.ln1(q + self.drop1(self.attn(q, k, v, allow_diagonal, zero_pad)))
        return self.ln2(x + self.drop2(self.ffn(x))) if self.use_ffn else x


class AKT(nn.Module):
    def __init__(self, n_skills, n_questions=0, d_model=128, n_heads=8, d_ff=256, n_blocks=1,
                 dropout=0.1, fc_dim=256, kq_same=True, use_rasch=True, l2=1e-5):
        super().__init__()
        self.n_skills, self.n_questions = n_skills, n_questions
        self.use_rasch = use_rasch
        self.item_emb = nn.Embedding(n_skills + 1, d_model, padding_idx=n_skills)
        self.inter_emb = nn.Embedding(2 * n_skills + 1, d_model, padding_idx=2 * n_skills)
        if use_rasch:
            self.item_var = nn.Embedding(n_skills + 1, d_model, padding_idx=n_skills)
            self.inter_var = nn.Embedding(2 * n_skills + 1, d_model, padding_idx=2 * n_skills)
            self.difficulty = nn.Embedding(n_questions + 1, 1, padding_idx=n_questions)
        self.know_enc = nn.ModuleList([
            AKTBlock(d_model, d_ff, n_heads, dropout, kq_same, True) for _ in range(n_blocks)])
        self.ques_enc = nn.ModuleList([
            AKTBlock(d_model, d_ff, n_heads, dropout, kq_same, False) for _ in range(n_blocks)])
        self.retriever = nn.ModuleList([
            AKTBlock(d_model, d_ff, n_heads, dropout, kq_same, True) for _ in range(n_blocks)])
        self.head = nn.Sequential(
            nn.Linear(2 * d_model, fc_dim), nn.ReLU(), nn.Dropout(dropout),
            nn.Linear(fc_dim, fc_dim // 2), nn.ReLU(), nn.Dropout(dropout),
            nn.Linear(fc_dim // 2, 1))

    def forward(self, ex, ans, target, mask=None, ex_q=None, tgt_q=None):
        batch, _ = ex.shape
        skills = torch.cat([ex[:, :1], target], dim=1)
        answers = torch.cat([ans, torch.full((batch, 1), 2 * self.n_skills,
                                             dtype=ans.dtype, device=ans.device)], dim=1)
        x, y = self.item_emb(skills), self.inter_emb(answers)
        if self.use_rasch:
            questions = torch.cat([ex_q[:, :1], tgt_q], dim=1)
            difficulty = self.difficulty(questions)
            x = x + difficulty * self.item_var(skills)
            y = y + difficulty * self.inter_var(answers)
        raw = x
        for block in self.know_enc:
            y = block(y, y, y, allow_diagonal=True)
        for question, retriever in zip(self.ques_enc, self.retriever):
            x = question(x, x, x, allow_diagonal=True)
            x = retriever(x, x, y, allow_diagonal=False, zero_pad=True)
        return self.head(torch.cat([x, raw], dim=-1)[:, 1:]).squeeze(-1)
