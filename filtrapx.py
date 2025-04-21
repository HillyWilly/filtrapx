import os
import re
import argparse
from unidecode import unidecode
from datetime import datetime
from ftfy import fix_text
from spellchecker import SpellChecker

# --- Preparação ---
spell = SpellChecker(language='pt')

def limpar_texto_anonimo(texto):
    texto = texto.encode('latin1', errors='ignore').decode('utf-8', errors='ignore')
    texto = texto.replace('/CNPJ', '')
    texto = ''.join(c for c in texto if c.isascii())
    palavras_invalidas = {'sem informacao', 'sem informação', 'nenhum', 'zero'}
    return '\n'.join(
        linha.strip() for linha in texto.splitlines()
        if linha.strip() and not any(p in linha.strip().lower() for p in palavras_invalidas)
    )

def corrigir_texto(texto):
    texto = fix_text(texto)
    texto = unidecode(texto)
    palavras = texto.split()
    palavras_corrigidas = [
        spell.correction(p.lower()) if spell.correction(p.lower()) else p
        for p in palavras
    ]
    return ' '.join(palavras_corrigidas).upper()

def extrair_registros_anonimo(texto):
    registros = []
    linhas = texto.splitlines()
    registro = {}
    for linha in linhas:
        if 'nome:' in linha.lower():
            if registro:
                registros.append(registro)
                registro = {}
            registro['Nome'] = linha.split(':', 1)[-1].strip().upper()
        elif any(k in linha.lower() for k in ['cpf:', 'cnpj:', 'cpf/cnpj']):
            cpf_linha = re.sub(r'\D', '', linha.split(':', 1)[-1])
            if cpf_linha:
                registro['CPF'] = cpf_linha
        elif 'nascimento:' in linha.lower():
            registro['Nascimento'] = linha.split(':', 1)[-1].strip()
        elif 'sexo:' in linha.lower():
            registro['Sexo'] = linha.split(':', 1)[-1].strip().upper()
    if registro:
        registros.append(registro)
    return registros

def detectar_formato_resultado(texto):
    return bool(re.search(r'•\s*RESULTADO\s*:', texto, flags=re.IGNORECASE))

def extrair_resultados_com_ponto(texto):
    blocos = re.split(r'•\s*RESULTADO\s*:\s*\d+', texto, flags=re.IGNORECASE)
    registros = []
    for bloco in blocos:
        if 'NOME' not in bloco.upper():
            continue
        nome = re.search(r'NOME:\s*(.+)', bloco, flags=re.IGNORECASE)
        cpf = re.search(r'CPF:\s*(\d+)', bloco, flags=re.IGNORECASE)
        nasc = re.search(r'NASCIMENTO:\s*([\d/-]+)', bloco, flags=re.IGNORECASE)
        sexo = re.search(r'SEXO:\s*([MF])', bloco, flags=re.IGNORECASE)
        registros.append({
            'Nome': nome.group(1).strip().upper() if nome else 'None',
            'CPF': cpf.group(1).strip() if cpf else 'None',
            'Nascimento': nasc.group(1).strip() if nasc else 'None',
            'Sexo': sexo.group(1).strip().upper() if sexo else 'None',
        })
    return registros

def extrair_blocos_por_nome(texto):
    blocos = re.split(r'(?:^|\n) *[👤•]*\s*Nome[:\s]', texto, flags=re.IGNORECASE)
    return ["Nome: " + b.strip() for b in blocos[1:]]

def limpar_texto_focus(texto):
    return texto.encode('ascii', 'ignore').decode('ascii')

def extrair_campos_focus(bloco):
    bloco = limpar_texto_focus(bloco.upper())
    def buscar(regex):
        m = re.search(regex, bloco)
        return m.group(1).strip() if m else "None"
    return {
        'Nome': buscar(r'NOME[:\s]+([A-Z\s]+?)(?:\n|$)'),
        'CPF': buscar(r'CPF[:\s]+(\d{11})'),
        'Nascimento': buscar(r'(?:DATA DE NASCIMENTO|NASCIMENTO)[:\s]+([\d/-]+)'),
        'Sexo': buscar(r'SEXO[:\s]+([A-Z]+)'),
    }

def calcular_idade_str(data_str):
    try:
        nascimento = datetime.strptime(data_str, "%d/%m/%Y") if "/" in data_str else datetime.strptime(data_str, "%Y-%m-%d")
        hoje = datetime.today()
        idade = hoje.year - nascimento.year - ((hoje.month, hoje.day) < (nascimento.month, nascimento.day))
        return idade
    except:
        return "Indefinida"

def gerar_texto_formatado(registros):
    linhas_formatadas = []
    for r in registros:
        nome = r.get('Nome', 'None').replace("'", "''")
        cpf = r.get('CPF', 'None')
        nascimento = r.get('Nascimento', 'None')
        sexo = r.get('Sexo', 'None')
        idade = calcular_idade_str(nascimento)
        bloco = (
            f"Nome: {nome}\n"
            f"CPF: {cpf}\n"
            f"Nascimento: {nascimento}\n"
            f"Sexo: {sexo}\n"
            f"Idade: {idade}\n"
            f"-----------------------\n"
        )
        linhas_formatadas.append(bloco)
    return linhas_formatadas

def aplicar_filtros(linhas, nome_filtro, sexo_filtro, idade_min, idade_max):
    filtradas = []
    for linha in linhas:
        nome, cpf, nascimento, sexo, idade = linha.split('\n')[:5]
        nome = nome.split(': ')[1]
        idade = int(idade.split(': ')[1].strip()) if idade else None
        if nome_filtro and nome_filtro not in nome:
            continue
        if sexo_filtro and sexo_filtro not in sexo:
            continue
        if idade_min and idade and idade < idade_min:
            continue
        if idade_max and idade and idade > idade_max:
            continue
        filtradas.append(linha)
    return filtradas

# --- Execução Principal ---
ddef main():
    parser = argparse.ArgumentParser(description="Processa e filtra dados de texto.")
    parser.add_argument("arquivo", help="Nome do arquivo de entrada")
    parser.add_argument("-n", "--nome", help="Filtrar por nome", default="")
    parser.add_argument("-s", "--sexo", help="Filtrar por sexo (M/F)", default="")
    parser.add_argument("-imn", "--idade_min", type=int, help="Idade mínima", default=0)
    parser.add_argument("-imx", "--idade_max", type=int, help="Idade máxima", default=150)
    parser.add_argument("-p", "--print", help="Imprimir no terminal", action="store_true")

    args = parser.parse_args()

    with open(args.arquivo, 'r', encoding='utf-8', errors='ignore') as f:
        conteudo = f.read()

    if 'BY: @AnoninoBuscasOfcBot' in conteudo:
        texto = limpar_texto_anonimo(conteudo)
        texto = corrigir_texto(texto)
        registros = extrair_registros_anonimo(texto)
    elif detectar_formato_resultado(conteudo):
        registros = extrair_resultados_com_ponto(conteudo)
    else:
        blocos = extrair_blocos_por_nome(conteudo)
        registros = [extrair_campos_focus(bloco) for bloco in blocos]

    linhas_formatadas = gerar_texto_formatado(registros)
    filtradas = aplicar_filtros(linhas_formatadas, args.nome.upper(), args.sexo.upper(), args.idade_min, args.idade_max)

    os.makedirs("out", exist_ok=True)
    with open("out/resultados.txt", 'w', encoding='utf-8') as f:
        f.writelines(l + "\n" for l in filtradas)

    print(f"{len(filtradas)} resultado(s) salvos em 'out/resultados.txt'.")

    # Aqui vem a parte da alteração para imprimir no terminal ou salvar:
    if args.print:
        # Imprime no terminal
        for linha in filtradas:
            print(linha)
    else:
        # Não imprime no terminal, apenas salva
        print(f"{len(filtradas)} resultado(s) salvos em 'out/resultados.txt'.")

if __name__ == "__main__":
    main(
