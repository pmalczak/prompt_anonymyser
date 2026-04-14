import re
import json
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class Anonymizer:
    mapping: Dict[str, str] = field(default_factory=dict)
    reverse_mapping: Dict[str, str] = field(default_factory=dict)
    counters: Dict[str, int] = field(default_factory=dict)

    custom_terms: Dict[str, List[str]] = field(default_factory=lambda: {
        "COMPANY": [
            "Fingo",
            "Regnology",
            "WKFS",

            "Intesa Sanpaolo",
            "Nordea",
            "SGB",
            "BPS",
            "CEP",
            "CEP Poland",
            "Zrzeszenie",
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

    _alphabet: str = field(default="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", init=False)

    def _next_placeholder(self, category: str) -> str:
        self.counters[category] = self.counters.get(category, 0) + 1
        return f"[[{category}_{self.counters[category]}]]"

    def _normalize_for_hash(self, text: str) -> str:
        """
        Normalize dictionary terms before hashing so the code is stable
        regardless of capitalization or repeated whitespace.
        """
        text = text.strip().lower()
        text = re.sub(r"\s+", " ", text)
        return text

    def _to_base36_code(self, data: bytes, length: int = 4) -> str:
        """
        Convert bytes to a stable A-Z0-9 code.
        """
        num = int.from_bytes(data, byteorder="big")
        alphabet = self._alphabet
        base = len(alphabet)

        chars = []
        for _ in range(length):
            num, rem = divmod(num, base)
            chars.append(alphabet[rem])

        return "".join(chars)

    def _hash_code(self, category: str, original: str, length: int = 4) -> str:
        """
        Stable short code for dictionary terms.
        Includes category to reduce accidental cross-category collisions.
        """
        normalized = self._normalize_for_hash(original)
        seed = f"{category}|{normalized}".encode("utf-8")
        digest = hashlib.blake2b(seed, digest_size=8).digest()
        return self._to_base36_code(digest, length=length)

    def _stable_placeholder(self, category: str, original: str) -> str:
        """
        Create stable placeholder like [[COMPANY_XYZW]].
        If collision occurs, automatically extend code length.
        """
        if original in self.reverse_mapping:
            return self.reverse_mapping[original]

        for length in range(4, 9):
            code = self._hash_code(category, original, length=length)
            placeholder = f"[[{category}_{code}]]"

            existing = self.mapping.get(placeholder)
            if existing is None:
                self.mapping[placeholder] = original
                self.reverse_mapping[original] = placeholder
                return placeholder

            if existing == original:
                self.reverse_mapping[original] = placeholder
                return placeholder

        raise ValueError(f"Could not generate unique stable placeholder for: {original}")

    def _store_mapping(self, original: str, category: str) -> str:
        """
        Regex-detected values still use sequential numbering.
        """
        if original in self.reverse_mapping:
            return self.reverse_mapping[original]

        placeholder = self._next_placeholder(category)
        self.mapping[placeholder] = original
        self.reverse_mapping[original] = placeholder
        return placeholder

    def _replace_custom_terms(self, text: str) -> str:
        """
        Replace user-defined terms first using stable hash-based placeholders.
        Short acronyms are matched only as standalone words.
        """
        for category, terms in self.custom_terms.items():
            sorted_terms = sorted(terms, key=len, reverse=True)

            for term in sorted_terms:
                escaped = re.escape(term)

                is_short_code = (
                    " " not in term
                    and len(term) <= 6
                    and re.fullmatch(r"[A-Za-z0-9._\-]+", term) is not None
                )

                if is_short_code:
                    pattern = re.compile(rf"\b{escaped}\b", re.IGNORECASE)
                else:
                    pattern = re.compile(escaped, re.IGNORECASE)

                def repl(match: re.Match) -> str:
                    original = match.group(0)
                    return self._stable_placeholder(category, original)

                text = pattern.sub(repl, text)

        return text

    def _replace_matches(self, text: str, pattern: str, category: str, flags: int = 0) -> str:
        regex = re.compile(pattern, flags)

        def repl(match: re.Match) -> str:
            original = match.group(0)
            return self._store_mapping(original, category)

        return regex.sub(repl, text)

    def anonymize(self, text: str) -> Tuple[str, Dict[str, str]]:
        text = self._replace_custom_terms(text)

        text = self._replace_matches(
            text,
            r'\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b',
            "EMAIL"
        )

        text = self._replace_matches(
            text,
            r'\bhttps?://[^\s]+|\bwww\.[^\s]+\b',
            "URL"
        )

        text = self._replace_matches(
            text,
            r'(?:(?<!\w)(?:\+?\d{1,3}[\s\-]?)?(?:\(?\d{2,4}\)?[\s\-]?)?\d{3}[\s\-]?\d{2,4}[\s\-]?\d{2,4}(?!\w))',
            "PHONE"
        )

        date_patterns = [
            r'\b\d{4}-\d{2}-\d{2}\b',
            r'\b\d{2}\.\d{2}\.\d{4}\b',
            r'\b\d{2}/\d{2}/\d{4}\b',
        ]
        for p in date_patterns:
            text = self._replace_matches(text, p, "DATE")

        money_patterns = [
            r'\b(?:PLN|EUR|USD|GBP)\s?\d[\d\s,.]*\b',
            r'\b\d[\d\s,.]*\s?(?:PLN|EUR|USD|GBP|zł)\b'
        ]
        for p in money_patterns:
            text = self._replace_matches(text, p, "AMOUNT", flags=re.IGNORECASE)

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

    def save_mapping(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.mapping, f, ensure_ascii=False, indent=2)

    def load_mapping(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as f:
            self.mapping = json.load(f)

        self.reverse_mapping = {v: k for k, v in self.mapping.items()}
        self.counters = {}

        for placeholder in self.mapping:
            m = re.match(r'\[\[([A-Z_]+)_(\d+)\]\]', placeholder)
            if m:
                category = m.group(1)
                idx = int(m.group(2))
                self.counters[category] = max(self.counters.get(category, 0), idx)