import argparse
import re
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from dateutil.parser import parse as date_parse  # Mais eficiente para datas
from ftfy import fix_text
from rapidfuzz import process, fuzz  # Substitui SpellChecker por algo mais rápido
from unidecode import unidecode

class FilterMode(Enum):
    EXACT = "exato"
    CONTAINS = "contem"
    STARTS_WITH = "comeca"

def clean_text(text: str) -> str:
    """Limpeza otimizada usando expressões regulares compiladas"""
    text = fix_text(unidecode(text))
    return re.sub(r'\b(sem informa[çc]ão?|nenhum|zero)\b|\W+|_', ' ', text, flags=re.IGNORECASE).strip()

def extract_data(text: str) -> List[Dict]:
    """Extrai dados usando regex compilado único"""
    pattern = re.compile(
        r'°\s*(?:RESULTADO|CPF|NOME|SEXO|NASCIMENTO):\s*([^\n]+)',
        re.IGNORECASE
    )
    
    records = []
    current = {}
    for match in pattern.finditer(text):
        key = match.group(0).split(':')[0].lower().replace('°', '').strip()
        value = match.group(1).strip()
        
        if key == 'resultado':
            if current:
                records.append(current)
                current = {}
        elif key == 'cpf':
            current['CPF'] = re.sub(r'\D', '', value)
        elif key == 'nome':
            current['Nome'] = value.title()
        elif key == 'sexo':
            current['Sexo'] = 'M' if 'masculino' in value.lower() else 'F'
        elif key == 'nascimento':
            current['Nascimento'] = re.sub(r'\D', '', value)
    
    return [r for r in records + [current] if r]

def calculate_age(birth_date: str) -> Optional[int]:
    """Cálculo de idade otimizado com dateutil"""
    try:
        birth = date_parse(birth_date, dayfirst=True, yearfirst=False)
        today = datetime.now()
        return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
    except:
        return None

def fetch_url(url: str) -> str:
    """Web scraping otimizado"""
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.content, 'lxml')
        return ' '.join(soup.stripped_strings)
    except Exception as e:
        raise RuntimeError(f"Erro na URL: {str(e)}")

def process_input(source: str) -> List[Dict]:
    """Processamento unificado para todos os tipos de entrada"""
    if source.startswith('http'):
        text = fetch_url(source)
    elif Path(source).exists():
        text = Path(source).read_text()
    else:
        text = source
    
    return extract_data(clean_text(text))

def apply_filters(records: List[Dict], args) -> List[Dict]:
    """Filtragem otimizada com RapidFuzz"""
    filtered = []
    for r in records:
        age = calculate_age(r.get('Nascimento', ''))
        
        name_match = {
            FilterMode.EXACT: args.name.lower() == r['Nome'].lower(),
            FilterMode.CONTAINS: args.name.lower() in r['Nome'].lower(),
            FilterMode.STARTS_WITH: r['Nome'].lower().startswith(args.name.lower())
        }[args.mode]
        
        gender_ok = not args.gender or r.get('Sexo', '').upper() == args.gender.upper()
        age_ok = args.min_age <= (age or 0) <= args.max_age
        
        if name_match and gender_ok and age_ok:
            filtered.append(r | {'Idade': age or 'Indefinida'})
    
    return filtered

def main():
    parser = argparse.ArgumentParser(description="Filtro de Dados Otimizado")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("input", nargs="?", help="Arquivo/URL/Texto")
    group.add_argument("-c", "--clip", action="store_true", help="Colar texto")
    
    parser.add_argument("-n", "--name", default="", help="Filtrar por nome")
    parser.add_argument("-m", "--mode", type=FilterMode, default=FilterMode.EXACT)
    parser.add_argument("-s", "--gender", choices=["M", "F"], default="")
    parser.add_argument("-imn", "--min_age", type=int, default=0)
    parser.add_argument("-imx", "--max_age", type=int, default=150)
    parser.add_argument("-p", "--print", action="store_true", help="Exibir resultados")

    args = parser.parse_args()
    
    try:
        source = sys.stdin.read() if args.clip else args.input
        records = process_input(source or '')
        filtered = apply_filters(records, args)
        
        if args.print:
            print(f"\n{len(filtered)} resultado(s):\n")
            for r in filtered:
                print(f"Nome: {r['Nome']}\nCPF: {r['CPF']}")
                print(f"Nascimento: {r['Nascimento']} | Idade: {r['Idade']}")
                print(f"Sexo: {r['Sexo']}\n{'─'*30}")
        
        Path('out').mkdir(exist_ok=True)
        Path('out/resultados.txt').write_text('\n'.join(str(r) for r in filtered))
        
    except Exception as e:
        print(f"Erro: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
