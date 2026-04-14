import re
import json
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class Anonymizer:
    mapping: Dict[str, str] = field(default_factory=dict)
    reverse_mapping: Dict[str, str] = field(default_factory=dict)
    counters: Dict[str, int] = field(default_factory=dict)

    # 🔥 TU DEFINIUJESZ SWOJE SŁOWNIKI
    custom_terms: Dict[str, List[str]] = field(default_factory=lambda: {
        "COMPANY": [
            "Fingo sp. z o.o.",
            "Regnology",
            "Intesa Sanpaolo",
            "SGB",
            "BPS",
            "Zrzeszenie",
            "WKFS",
        ],
        "PRODUCT": [
            "RRH",
            "Regnology Reporting Hub",
            "EON",
            "LIQREP",
            "ION",
            "DataFoundation",
            "DF",
            "EUA",
            "RE5",
            "ZHD",
            "Zrzeszeniowa Hurtownia Danych",
        ],
        "SYSTEM": [
            "Salesforce",
            "HubSpot",
            "JIRA",
            "zrzeszonych banków spółdzielczych",
        ],
        "LEGAL_DOC": [
            "DORA Addendum",
            "3862/DI/12/2025",
            "CTNR-010158",
        ]
    })

    def _next_placeholder(self, category: str) -> str:
        self.counters[category] = self.counters.get(category, 0) + 1
        return f"[[{category}_{self.counters[category]}]]"

    def _store_mapping(self, original: str, category: str) -> str:
        if original in self.reverse_mapping:
            return self.reverse_mapping[original]

        placeholder = self._next_placeholder(category)
        self.mapping[placeholder] = original
        self.reverse_mapping[original] = placeholder
        return placeholder

    def _replace_custom_terms(self, text: str) -> str:
        """
        Replace user-defined terms first (highest priority).

        Rules:
        - long phrases: normal escaped match
        - short acronyms / single-token codes: match only as standalone words
        """
        for category, terms in self.custom_terms.items():
            sorted_terms = sorted(terms, key=len, reverse=True)

            for term in sorted_terms:
                escaped = re.escape(term)

                # If term looks like a short acronym/code, match only as a full token
                # Examples: SOW, MSA, SLA, RRH, EON
                is_short_code = (
                        " " not in term
                        and len(term) <= 6
                        and re.fullmatch(r"[A-Za-z0-9._\-]+", term) is not None
                )

                if is_short_code:
                    pattern = re.compile(rf"\b{escaped}\b", re.IGNORECASE)
                else:
                    pattern = re.compile(escaped, re.IGNORECASE)

                def repl(match):
                    original = match.group(0)
                    return self._store_mapping(original, category)

                text = pattern.sub(repl, text)

        return text

    def _replace_matches(self, text: str, pattern: str, category: str, flags: int = 0) -> str:
        regex = re.compile(pattern, flags)

        def repl(match: re.Match) -> str:
            original = match.group(0)
            return self._store_mapping(original, category)

        return regex.sub(repl, text)

    def anonymize(self, text: str) -> Tuple[str, Dict[str, str]]:
        # 🔥 1. NAJPIERW TWOJE SŁOWNIKI
        text = self._replace_custom_terms(text)

        # 🔹 2. EMAIL
        text = self._replace_matches(
            text,
            r'\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b',
            "EMAIL"
        )

        # 🔹 3. URL
        text = self._replace_matches(
            text,
            r'\bhttps?://[^\s]+|\bwww\.[^\s]+\b',
            "URL"
        )

        # 🔹 4. PHONE
        text = self._replace_matches(
            text,
            r'(?:(?<!\w)(?:\+?\d{1,3}[\s\-]?)?(?:\(?\d{2,4}\)?[\s\-]?)?\d{3}[\s\-]?\d{2,4}[\s\-]?\d{2,4}(?!\w))',
            "PHONE"
        )

        # 🔹 5. DATE
        date_patterns = [
            r'\b\d{4}-\d{2}-\d{2}\b',
            r'\b\d{2}\.\d{2}\.\d{4}\b',
            r'\b\d{2}/\d{2}/\d{4}\b',
        ]
        for p in date_patterns:
            text = self._replace_matches(text, p, "DATE")

        # 🔹 6. AMOUNT
        money_patterns = [
            r'\b(?:PLN|EUR|USD)\s?\d[\d\s,.]*\b',
            r'\b\d[\d\s,.]*\s?(?:PLN|EUR|USD|zł)\b'
        ]
        for p in money_patterns:
            text = self._replace_matches(text, p, "AMOUNT")

        # 🔹 7. PERSON (heurystyka)
        text = self._replace_matches(
            text,
            r'\b[A-ZŻŹĆĄŚĘŁÓŃ][a-zżźćńółęąś]+(?:\s+[A-ZŻŹĆĄŚĘŁÓŃ][a-zżźćńółęąś]+){1,2}\b',
            "PERSON"
        )

        return text, self.mapping

    def deanonymize(self, text: str) -> str:
        for placeholder in sorted(self.mapping.keys(), key=len, reverse=True):
            text = text.replace(placeholder, self.mapping[placeholder])
        return text

    def save_mapping(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.mapping, f, ensure_ascii=False, indent=2)

    def load_mapping(self, path: str):
        with open(path, "r", encoding="utf-8") as f:
            self.mapping = json.load(f)
        self.reverse_mapping = {v: k for k, v in self.mapping.items()}
