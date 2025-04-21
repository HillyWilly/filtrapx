import argparse
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict

class TextProcessor:
    @staticmethod
    def clean(text: str) -> str:
        return re.sub(r'[^\w\s]|_', '', text).strip()

class DataExtractor:
    @staticmethod
    def extract(text: str) -> List[Dict]:
        pattern = re.compile(
            r'(?:NOME|CPF|NASCIMENTO|SEXO):\s*([^\n]+)',
            re.IGNORECASE
        )
        
        records = []
        current = {}
        for line in text.split('\n'):
            match = pattern.search(line)
            if match:
                key = match.group(0).split(':')[0].strip().title()
                value = match.group(1).strip()
                current[key] = value
            elif line.strip() == '' and current:
                records.append(current)
                current = {}
        
        return records

def main():
    parser = argparse.ArgumentParser(description="Processador de Arquivos TXT")
    parser.add_argument("arquivo", help="Caminho do arquivo ou pasta com .txt")
    parser.add_argument("-p", "--print", action="store_true", help="Exibir resultados")
    
    args = parser.parse_args()
    
    try:
        path = Path(args.arquivo)
        files = list(path.glob("*.txt")) if path.is_dir() else [path]
        
        all_records = []
        for file in files:
            text = TextProcessor.clean(file.read_text())
            all_records.extend(DataExtractor.extract(text))
        
        if args.print:
            print(f"\n{len(all_records)} resultados encontrados:")
            for i, record in enumerate(all_records, 1):
                print(f"\nResultado {i}:")
                for key, value in record.items():
                    print(f"{key}: {value}")
                print("-" * 30)
                
        Path('resultados').mkdir(exist_ok=True)
        Path('resultados/relatorio.txt').write_text('\n'.join(str(r) for r in all_records))
        
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    main()
