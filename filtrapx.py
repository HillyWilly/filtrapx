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
        'Nome': re.compile(r'(?:nome|name):\s*(.+?)(?:\n|$)', re.IGNORECASE),
        'CPF': re.compile(r'(?:cpf):\D*(\d{11})', re.IGNORECASE),
        'CNPJ': re.compile(r'(?:cnpj):\D*(\d{14})', re.IGNORECASE),
        'Nascimento': re.compile(r'(?:nascimento|data de nascimento):\s*([\d/-]+)', re.IGNORECASE),
        'Sexo': re.compile(r'(?:sexo|gender):\s*([MF])', re.IGNORECASE)
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
        date_str = re.sub(r'[^0-9]', '', birth_date)
        formats = [
            ('%d%m%Y', 8),  # DDMMYYYY
            ('%Y%m%d', 8),  # AAAAMMDD
            ('%m%Y', 6),    # MMAAAA
            ('%Y', 4),      # Apenas ano
        ]
        
        for fmt, length in formats:
            try:
                date_part = date_str[:length]
                birth = datetime.strptime(date_part, fmt)
                today = datetime.today()
                return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
            except:
                continue
        return 'Indefinida'

class FileHandler:
    FORMATS = [
        {   # Formato AnoninoBuscasOfcBot
            'detector': lambda t: 'BY: @AnoninoBuscasOfcBot' in t,
            'processor': lambda t: [
                DataExtractor.extract_from_block(b) 
                for b in TextProcessor.correct_text(
                    TextProcessor.clean_text(t)
                ).split('\n\n')
            ]
        },
        {   # Formato com marcadores • RESULTADO
            'detector': lambda t: re.search(r'•\s*RESULTADO\s*:', t),
            'processor': lambda t: [
                DataExtractor.extract_from_block(b) 
                for b in re.split(r'•\s*RESULTADO\s*:\s*\d+', t) 
                if 'NOME' in b
            ]
        },
        {   # Formato genérico
            'detector': lambda _: True,
            'processor': lambda t: [
                DataExtractor.extract_from_block(f'Nome: {b}') 
                for b in re.split(r'(?:\n|^)[👤•]*\s*Nome:\s*', t, flags=re.IGNORECASE)[1:]
            ]
        }
    ]

    @classmethod
    def get_files(cls, args):
        if args.termux:
            telegram_dir = "../storage/downloads/Telegram"
            if not os.path.exists(telegram_dir):
                raise FileNotFoundError("Diretório do Telegram não encontrado")
                
            txt_files = [os.path.join(telegram_dir, f) 
                       for f in os.listdir(telegram_dir) if f.endswith(".txt")]
            
            if not txt_files:
                raise FileNotFoundError("Nenhum arquivo .txt encontrado no Telegram")
                
            return [max(txt_files, key=os.path.getmtime)]
        
        if os.path.isdir(args.input):
            return [os.path.join(args.input, f) 
                   for f in os.listdir(args.input) if f.endswith(".txt")]
        
        return [args.input]

    @classmethod
    def process_file(cls, content):
        for fmt in cls.FORMATS:
            if fmt['detector'](content):
                return fmt['processor'](content)
        return []

    @staticmethod
    def save_results(records, print_flag):
        os.makedirs("out", exist_ok=True)
        output = []
        
        for r in records:
            output.append(
                f"Nome: {r['Nome']}\n"
                f"CPF/CNPJ: {r['CPF'] or r['CNPJ']}\n"
                f"Nascimento: {r['Nascimento']}\n"
                f"Sexo: {r['Sexo']}\n"
                f"Idade: {r.get('Idade', 'Indefinida')}\n"
                f"-----------------------\n"
            )
        
        with open("out/resultados.txt", 'w', encoding='utf-8') as f:
            f.writelines(output)
            
        if print_flag:
            print(''.join(output))
            print(f"\n{len(records)} resultado(s) encontrados.")

class FilterSystem:
    @staticmethod
    def apply_filters(records, filters):
        filtered = []
        for r in records:
            r['Idade'] = AgeCalculator.calculate_age(r['Nascimento'])
            if all([
                FilterSystem._check_name(r['Nome'], filters['name'], filters['mode']),
                FilterSystem._check_gender(r['Sexo'], filters['gender']),
                FilterSystem._check_age(r['Idade'], filters['min_age'], filters['max_age'])
            ]):
                filtered.append(r)
        return filtered

    @staticmethod
    def _check_name(name, query, mode):
        if not query: return True
        name, query = name.upper(), query.upper()
        return {
            'exato': name == query,
            'contem': query in name,
            'comeca': name.startswith(query)
        }.get(mode, False)

    @staticmethod
    def _check_gender(gender, target):
        return not target or gender.upper() == target.upper()

    @staticmethod
    def _check_age(age, min_a, max_a):
        if age == 'Indefinida':
            return min_a == 0 and max_a == 150
        try: 
            return min_a <= int(age) <= max_a
        except: 
            return False

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
    
    try:
        files = FileHandler.get_files(args)
        all_records = []
        
        for file in files:
            with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                all_records.extend(FileHandler.process_file(f.read()))
        
        filtered = FilterSystem.apply_filters(all_records, {
            'name': args.name,
            'gender': args.gender,
            'min_age': args.min_age,
            'max_age': args.max_age,
            'mode': args.mode
        })
        
        FileHandler.save_results(filtered, args.print)
        
    except Exception as e:
        print(f"Erro: {str(e)}")

if __name__ == "__main__":
    main()
