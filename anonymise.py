import json
from pathlib import Path

from anonymiser import Anonymizer


def main(prefix: str):
    anonymizer = Anonymizer()

    p = Path(__file__).parent
    f = p / f'{prefix}text'
    original_text = f.read_text(encoding='utf-8')

    anonymized_text, mapping = anonymizer.anonymize(original_text)

    print("=== ZANONIMIZOWANY TEKST ===")
    print(anonymized_text)

    print("\n=== MAPA PODSTAWIEŃ ===")
    print(json.dumps(mapping, ensure_ascii=False, indent=2))

    anonymizer.save_mapping(f"{prefix}mapping.json")

    # restored_text = anonymizer.deanonymize(anonymized_text)
    #
    # print("\n=== ODKODOWANY TEKST ===")
    # print(restored_text)


if __name__ == "__main__":
    # prefix = '1_'
    # prefix = '2_'
    prefix = '3_'
    main(prefix)
