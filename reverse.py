import json
from pathlib import Path

from anonymise import prefix
from anonymiser import Anonymizer


def main(prefix):
    p = Path(__file__).parent / 'assets'
    f = p / f'{prefix}answer'
    reverse_text = f.read_text(encoding='utf-8')

    anonymizer = Anonymizer()
    anonymizer.load_mapping(f"assets/{prefix}mapping.json")

    restored_text = anonymizer.deanonymize(reverse_text)

    print("\n=== ODKODOWANY TEKST ===")
    print(restored_text)


if __name__ == "__main__":
    main(prefix)
