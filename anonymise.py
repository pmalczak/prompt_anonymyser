import json
from pathlib import Path

from anonymiser import Anonymizer

# prefix = '1_'
# prefix = '2_'
# prefix = '3_'
prefix = '6_'


def main(_prefix: str):
    anonymizer = Anonymizer()

    p = Path(__file__).parent / 'assets'
    f = p / f'{_prefix}text'
    original_text = f.read_text(encoding='utf-8')

    anonymized_text, mapping = anonymizer.anonymize(original_text)

    print("=== ZANONIMIZOWANY TEKST ===")
    print(anonymized_text)

    print("\n=== MAPA PODSTAWIEŃ ===")
    print(json.dumps(mapping, ensure_ascii=False, indent=2))

    anonymizer.save_mapping(f"assets/{_prefix}mapping.json")

    # restored_text = anonymizer.deanonymize(anonymized_text)
    #
    # print("\n=== ODKODOWANY TEKST ===")
    # print(restored_text)




if __name__ == "__main__":
    main(prefix)
