import os
import re
import argparse
from datetime import datetime
from unidecode import unidecode
from ftfy import fix_text
from spellchecker import SpellChecker

spell = SpellChecker(language='pt')

class TextProcessor:
    @staticmethod
    def clean_text(text, invalid_phrases=None):
        text = fix_text(text.encode('latin1', errors='ignore').decode('utf-8', errors='ignore'))
        text = re.sub(r'/CNPJ|[^\x00-\x7F]', '', text)
        phrases = {'sem informacao', 'sem informação', 'nenhum', 'zero'}
        if invalid_phrases: phrases.update(invalid_phrases)
        return '\n'.join(line.strip() for line in text.splitlines() 
                        if line.strip() and not any(p in line.lower() for p in phrases))

    @staticmethod
    def correct_text(text):
        return ' '.join([spell.correction(w.lower()) or w for w in unidecode(fix_text(text)).split()]).upper()

class DataExtractor:
    PATTERNS = {
        'name': re.compile(r'(?:nome|name):\s*(.+?)(?:\n|$)', re.IGNORECASE),
        'cpf': re.compile(r'(?:cpf|cnpj):\D*(\d{11,14})', re.IGNORECASE),
        'birth': re.compile(r'(?:nascimento|data de nascimento):\s*([\d/-]+)', re.IGNORECASE),
        'gender': re.compile(r'(?:sexo|gender):\s*([MF])', re.IGNORECASE)
    }

    @classmethod
    def extract_from_block(cls, block):
        return {key: cls._extract_field(block, pattern) for key, pattern in cls.PATTERNS.items()}

    @staticmethod
    def _extract_field(text, pattern):
        match = pattern.search(text.upper())
        return match.group(1).strip() if match else 'None'

class AgeCalculator:
    @staticmethod
    def calculate_age(birth_date):
        try:
            birth = datetime.strptime(re.sub(r'[^0-9]', '', birth_date)[:8], '%d%m%Y')
            today = datetime.today()
            return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
        except:
            return 'Indefinida'

class FileHandler:
    FORMATS = [
        {'detector': lambda t: 'BY: @AnoninoBuscasOfcBot' in t,
         'processor': lambda t: [DataExtractor.extract_from_block(b) for b in TextProcessor.clean_text(t).split('\n\n')]},
        
        {'detector': lambda t: re.search(r'•\s*RESULTADO\s*:', t),
         'processor': lambda t: [DataExtractor.extract_from_block(b) 
                                for b in re.split(r'•\s*RESULTADO\s*:\s*\d+', t) if 'NOME' in b]},
        
        {'detector': lambda _: True,
         'processor': lambda t: [DataExtractor.extract_from_block(f'Nome: {b}') 
                                for b in re.split(r'(?:^|\n)[👤•]*\s*Nome[:\s]', t)[1:]]}
    ]

    @classmethod
    def process_file(cls, content):
        for fmt in cls.FORMATS:
            if fmt['detector'](content):
                return fmt['processor'](TextProcessor.correct_text(content))
        return []

class FilterSystem:
    @staticmethod
    def apply_filters(records, filters):
        return [r for r in records if all([
            FilterSystem._check_name(r['name'], filters.get('name'), filters.get('mode')),
            FilterSystem._check_gender(r['gender'], filters.get('gender')),
            FilterSystem._check_age(r.get('age', 0), filters.get('min_age'), filters.get('max_age'))
        ])]

    @staticmethod
    def _check_name(name, query, mode):
        if not query: return True
        name, query = name.upper(), query.upper()
        return {
            'exato': name == query,
            'contem': query in name,
            'comeca': name.startswith(query)
        }.get(mode, True)

    @staticmethod
    def _check_gender(gender, target):
        return not target or gender.upper() == target.upper()

    @staticmethod
    def _check_age(age, min_a, max_a):
        return isinstance(age, int) and min_a <= age <= max_a

def main():
    parser = argparse.ArgumentParser(description="Processa e filtra dados de texto.")
    parser.add_argument("input", nargs="?", help="Arquivo ou pasta de entrada")
    parser.add_argument("-t", "--termux", action="store_true", help="Usar último arquivo do Telegram")
    parser.add_argument("-n", "--name", help="Filtrar por nome", default="")
    parser.add_argument("-m", "--mode", choices=["exato", "contem", "comeca"], default="exato")
    parser.add_argument("-s", "--gender", help="Filtrar por sexo (M/F)", default="")
    parser.add_argument("-imn", "--min_age", type=int, default=0)
    parser.add_argument("-imx", "--max_age", type=int, default=150)
    parser.add_argument("-p", "--print", action="store_true", help="Mostrar resultados no terminal")

    args = parser.parse_args()
    files = FileHandler.get_files(args)

    all_records = []
    for file in files:
        with open(file, 'r', encoding='utf-8', errors='ignore') as f:
            all_records.extend(FileHandler.process_file(f.read()))

    for record in all_records:
        record['age'] = AgeCalculator.calculate_age(record['birth'])

    filtered = FilterSystem.apply_filters(all_records, {
        'name': args.name,
        'gender': args.gender,
        'min_age': args.min_age,
        'max_age': args.max_age,
        'mode': args.mode
    })

    FileHandler.save_results(filtered, args.print)

if __name__ == "__main__":
    main()
