import argparse
import re
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Pattern

import requests
from bs4 import BeautifulSoup
from ftfy import fix_text
from spellchecker import SpellChecker
from unidecode import unidecode

class FilterMode(Enum):
    EXACT = "exato"
    CONTAINS = "contem"
    STARTS_WITH = "comeca"

class TextProcessor:
    @staticmethod
    def clean_text(text: str, invalid_phrases: Optional[set] = None) -> str:
        """Limpa o texto removendo caracteres inválidos e frases indesejadas."""
        text = fix_text(text.encode("latin1", errors="ignore").decode("utf-8", errors="ignore"))
        text = re.sub(r"/CNPJ|[^\x00-\x7F]", "", text)
        
        phrases = {"sem informacao", "sem informação", "nenhum", "zero"}
        if invalid_phrases:
            phrases.update(invalid_phrases)
            
        return "\n".join(
            line.strip() for line in text.splitlines()
            if line.strip() and not any(p in line.lower() for p in phrases)
        )

    @staticmethod
    def correct_text(text: str) -> str:
        """Corrige ortografia e normaliza o texto."""
        spell = SpellChecker(language="pt")
        words = [
            spell.correction(word.lower()) or word
            for word in unidecode(fix_text(text)).split()
        ]
        return " ".join(words).upper()

class DataExtractor:
    PATTERNS: Dict[str, Pattern] = {
        "Nome": re.compile(r"(?:nome|name):\s*(.+?)(?:\n|$)", re.IGNORECASE),
        "CPF": re.compile(r"(?:cpf):\D*(\d{11})", re.IGNORECASE),
        "CNPJ": re.compile(r"(?:cnpj):\D*(\d{14})", re.IGNORECASE),
        "Nascimento": re.compile(r"(?:nascimento|data de nascimento):\s*([\d/-]+)", re.IGNORECASE),
        "Sexo": re.compile(r"(?:sexo|gender):\s*([MF])", re.IGNORECASE),
    }

    @classmethod
    def extract_from_block(cls, block: str) -> Dict[str, Optional[str]]:
        return {key: cls._extract_field(block, pattern) for key, pattern in cls.PATTERNS.items()}

    @staticmethod
    def _extract_field(text: str, pattern: Pattern) -> Optional[str]:
        match = pattern.search(text.upper())
        return match.group(1).strip() if match else None

class AgeCalculator:
    @staticmethod
    def calculate_age(birth_date: Optional[str]) -> Optional[int]:
        if not birth_date:
            return None

        date_str = re.sub(r"[^0-9]", "", birth_date)
        formats = [
            ("%d%m%Y", 8),  # DDMMYYYY
            ("%Y%m%d", 8),  # AAAAMMDD
            ("%m%Y", 6),    # MMAAAA
            ("%Y", 4),      # Apenas ano
        ]

        for fmt, length in formats:
            try:
                date_part = date_str[:length]
                birth = datetime.strptime(date_part, fmt)
                today = datetime.today()
                age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
                return max(age, 0)
            except ValueError:
                continue
        return None

class WebScraper:
    @staticmethod
    def fetch_url_content(url: str) -> str:
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            for element in soup(['script', 'style', 'nav', 'footer', 'header', 'meta']):
                element.decompose()
                
            text = soup.get_text(separator='\n', strip=True)
            return re.sub(r'\n{3,}', '\n\n', text)
        except requests.RequestException as e:
            raise RuntimeError(f"Erro ao acessar URL: {str(e)}") from e

class FileHandler:
    FORMATS = [
        {   # Formato AnoninoBuscasOfcBot
            "detector": lambda t: "BY: @AnoninoBuscasOfcBot" in t,
            "processor": lambda t: [
                DataExtractor.extract_from_block(b)
                for b in TextProcessor.correct_text(
                    TextProcessor.clean_text(t)
                ).split("\n\n")
            ]
        },
        {   # Formato com marcadores • RESULTADO
            "detector": lambda t: re.search(r"•\s*RESULTADO\s*:", t),
            "processor": lambda t: [
                DataExtractor.extract_from_block(b)
                for b in re.split(r"•\s*RESULTADO\s*:\s*\d+", t)
                if "NOME" in b
            ]
        },
        {   # Formato genérico
            "detector": lambda _: True,
            "processor": lambda t: [
                DataExtractor.extract_from_block(f"Nome: {b}")
                for b in re.split(r"(?:\n|^)[👤•]*\s*Nome:\s*", t, flags=re.IGNORECASE)[1:]
            ]
        }
    ]

    @staticmethod
    def create_temp_file(content: str, prefix: str) -> Path:
        temp_dir = Path("temp")
        temp_dir.mkdir(exist_ok=True)
        file_path = temp_dir / f"{prefix}_{datetime.now().strftime('%Y%m%d%H%M%S')}.txt"
        file_path.write_text(content, encoding='utf-8')
        return file_path

    @classmethod
    def get_files(cls, args: argparse.Namespace) -> List[Path]:
        if args.url:
            return [cls.create_temp_file(WebScraper.fetch_url_content(args.url), "web")]
        
        if args.termux:
            telegram_dir = Path("../storage/downloads/Telegram")
            if not telegram_dir.exists():
                raise FileNotFoundError("Diretório do Telegram não encontrado")
            
            txt_files = list(telegram_dir.glob("*.txt"))
            return [max(txt_files, key=lambda f: f.stat().st_mtime)] if txt_files else []
        
        if args.clip:
            print("\nCole o texto (pressione Enter + Ctrl+D/Ctrl+Z para finalizar):")
            content = sys.stdin.read()
            return [cls.create_temp_file(content, "clip")]
        
        path = Path(args.input)
        return list(path.glob("*.txt")) if path.is_dir() else [path]

    @classmethod
    def process_file(cls, content: str) -> List[Dict]:
        for fmt in cls.FORMATS:
            if fmt["detector"](content):
                return fmt["processor"](content)
        return []

    @staticmethod
    def save_results(records: List[Dict], print_flag: bool) -> None:
        output_dir = Path("out")
        output_dir.mkdir(exist_ok=True)
        
        output = []
        for record in records:
            output.append(
                f"Nome: {record['Nome'] or 'Não informado'}\n"
                f"CPF/CNPJ: {record['CPF'] or record['CNPJ'] or 'Nenhum'}\n"
                f"Nascimento: {record['Nascimento'] or 'Não informado'}\n"
                f"Sexo: {record['Sexo'] or 'Não informado'}\n"
                f"Idade: {record.get('Idade', 'Indefinida')}\n"
                f"{'-'*24}\n"
            )
        
        output_path = output_dir / "resultados.txt"
        output_path.write_text("\n".join(output), encoding="utf-8")
        
        if print_flag:
            print("\n".join(output))
            print(f"\n{len(records)} resultado(s) encontrados.")

class FilterSystem:
    @staticmethod
    def apply_filters(
        records: List[Dict],
        name_filter: str,
        mode: FilterMode,
        gender_filter: str,
        min_age: int,
        max_age: int
    ) -> List[Dict]:
        filtered = []
        for record in records:
            record["Idade"] = AgeCalculator.calculate_age(record["Nascimento"])
            
            if all([
                FilterSystem._check_name(record["Nome"], name_filter, mode),
                FilterSystem._check_gender(record["Sexo"], gender_filter),
                FilterSystem._check_age(record["Idade"], min_age, max_age)
            ]):
                filtered.append(record)
        return filtered

    @staticmethod
    def _check_name(name: Optional[str], query: str, mode: FilterMode) -> bool:
        if not query:
            return True
        if not name:
            return False
            
        name = name.upper()
        query = query.upper()
        
        return {
            FilterMode.EXACT: name == query,
            FilterMode.CONTAINS: query in name,
            FilterMode.STARTS_WITH: name.startswith(query)
        }[mode]

    @staticmethod
    def _check_gender(gender: Optional[str], target: str) -> bool:
        return not target or (gender and gender.upper() == target.upper())

    @staticmethod
    def _check_age(age: Optional[int], min_age: int, max_age: int) -> bool:
        if age is None:
            return min_age == 0 and max_age == 150
        return min_age <= age <= max_age

def main():
    parser = argparse.ArgumentParser(description="Processa e filtra dados de texto.")
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("input", nargs="?", help="Arquivo ou pasta de entrada")
    input_group.add_argument("-u", "--url", help="URL para extrair conteúdo")
    input_group.add_argument("-t", "--termux", action="store_true", help="Usar último arquivo do Telegram")
    input_group.add_argument("-c", "--clip", action="store_true", help="Colar texto diretamente")
    
    parser.add_argument("-n", "--name", help="Filtrar por nome", default="")
    parser.add_argument("-m", "--mode", type=FilterMode, default=FilterMode.EXACT)
    parser.add_argument("-s", "--gender", choices=["M", "F"], help="Filtrar por sexo", default="")
    parser.add_argument("-imn", "--min_age", type=int, default=0)
    parser.add_argument("-imx", "--max_age", type=int, default=150)
    parser.add_argument("-p", "--print", action="store_true", help="Mostrar resultados no terminal")

    args = parser.parse_args()

    try:
        files = FileHandler.get_files(args)
        all_records = []
        
        for file in files:
            content = file.read_text(encoding="utf-8", errors="ignore")
            all_records.extend(FileHandler.process_file(content))
        
        filtered = FilterSystem.apply_filters(
            all_records,
            args.name,
            args.mode,
            args.gender,
            args.min_age,
            args.max_age
        )
        
        FileHandler.save_results(filtered, args.print)
        
    except Exception as e:
        print(f"\nErro: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
