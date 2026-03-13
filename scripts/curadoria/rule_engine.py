#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class RuleMatch:
    rule_id: str
    applied: bool
    reason: str


class CuradoriaRules:
    """Engine de regras baseado em JSON para manutenção fácil por iniciantes.

    Como manter:
    - adicionar/remover item em `rules.json`
    - ajustar `priority` (maior roda antes)
    - ajustar `order` (desempate dentro da mesma priority)
    - ligar/desligar com `enabled`
    """

    def __init__(self, rules_path: Path):
        self.rules_path = Path(rules_path).expanduser().resolve()
        self.cfg = json.loads(self.rules_path.read_text(encoding="utf-8"))

        self.thresholds = self.cfg.get("thresholds", {})
        self.default_label = self.cfg.get("default_label", "revisar")
        self.labels = self.cfg.get("labels", ["meme", "noticia-propaganda", "revisar"])

        rules = [r for r in self.cfg.get("rules", []) if r.get("enabled", True)]
        self.rules = sorted(
            rules,
            key=lambda r: (
                -int(r.get("priority", 0)),
                int(r.get("order", 9999)),
            ),
        )

    def normalize(self, text: str) -> str:
        t = text or ""
        norm_cfg = self.cfg.get("normalize", {})
        if norm_cfg.get("lower", True):
            t = t.lower()
        if norm_cfg.get("strip_accents", True):
            t = "".join(
                c for c in unicodedata.normalize("NFD", t)
                if unicodedata.category(c) != "Mn"
            )
        return t

    def _match_rule(self, text: str, rule: dict[str, Any]) -> bool:
        any_terms = [self.normalize(x) for x in rule.get("when_any", [])]
        all_terms = [self.normalize(x) for x in rule.get("when_all", [])]
        none_terms = [self.normalize(x) for x in rule.get("when_not_any", [])]
        regex_terms = rule.get("when_regex", [])

        if any_terms and not any(term in text for term in any_terms):
            return False
        if all_terms and not all(term in text for term in all_terms):
            return False
        if none_terms and any(term in text for term in none_terms):
            return False
        if regex_terms and not any(re.search(rx, text) for rx in regex_terms):
            return False

        if not any_terms and not all_terms and not none_terms and not regex_terms:
            return False
        return True

    def classify(self, raw_text: str) -> tuple[str, dict[str, Any]]:
        text = self.normalize(raw_text)
        scores = {label: 0 for label in self.labels}
        matches: list[RuleMatch] = []
        forced_label = None

        for rule in self.rules:
            matched = self._match_rule(text, rule)
            if not matched:
                matches.append(RuleMatch(rule_id=rule.get("id", "(sem-id)"), applied=False, reason="no-match"))
                continue

            for label, value in (rule.get("add_scores", {}) or {}).items():
                scores[label] = scores.get(label, 0) + int(value)

            if rule.get("set_label"):
                forced_label = rule.get("set_label")

            matches.append(RuleMatch(rule_id=rule.get("id", "(sem-id)"), applied=True, reason="matched"))

            if rule.get("stop_on_match", False):
                break

        if forced_label:
            label = forced_label
        else:
            news_thr = int(self.thresholds.get("noticia-propaganda", 2))
            meme_thr = int(self.thresholds.get("meme", 2))

            if scores.get("noticia-propaganda", 0) >= news_thr:
                label = "noticia-propaganda"
            elif scores.get("meme", 0) >= meme_thr and scores.get("noticia-propaganda", 0) == 0:
                label = "meme"
            else:
                label = self.default_label

        return label, {
            "scores": scores,
            "forced_label": forced_label,
            "thresholds": self.thresholds,
            "matches": [m.__dict__ for m in matches],
        }
