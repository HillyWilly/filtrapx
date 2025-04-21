# FILTRAPX (FILTRA-PUXADA)

**Processador de Dados de Bots de Busca**

`filtrapx` é um utilitário Python criado para processar, limpar, corrigir e extrair dados estruturados a partir de arquivos `.txt` gerados por bots de busca no Telegram. Ele é ideal para organizar saídas dos bots em formatos mais utilizáveis, como listagens legíveis e comandos SQL.

---

## 🤖 Bots Compatíveis

Este script foi desenvolvido para lidar com saídas específicas dos seguintes bots:

- `@AnonimoBuscasOfcBot`
- `@AlexiaBuscasBot`
- `@FocusSearchBot`
- `@MkBuscasBot`
- `@SkynetBlackRobot`

⚠️ **Atenção**: arquivos `.txt` que **não sejam** oriundos desses bots podem gerar **resultados imprevisíveis**, como:

- Perda ou duplicação de dados;
- Extração incompleta;
- Geração incorreta de comandos SQL;
- Resultados com falha na filtragem.

---

## 🧰 Funcionalidades

- Limpeza e normalização de texto (acentuação, codificação);
- Correção ortográfica básica (via `pyspellchecker`);
- Extração automática de campos: `Nome`, `CPF`, `Nascimento`, `Sexo`;
- Cálculo de idade com base na data de nascimento;
- Geração de listagem estruturada e comandos SQL;
- Filtros aplicáveis por:
  - Nome (exato, contém, começa com)
  - Sexo (M/F)
  - Faixa etária (mínima/máxima)
- Compatível com modo **Termux**, buscando automaticamente o arquivo `.txt` mais recente da pasta `Telegram`.

---

## 🚀 Como Usar

### Execução padrão:

```bash
python3 filtrapx.py arquivo.txt
```

### Com filtros:

```bash
python3 filtrapx.py arquivo.txt --nome JOAO --sexo M --idade_min 25 --idade_max 40
```

### Modo Termux:

```bash
python3 filtrapx.py --termux
```

---

### ⚙️ Opções disponíveis

| Parâmetro        | Descrição                                 | Exemplo                            |
|------------------|-------------------------------------------|------------------------------------|
| `arquivo.txt`    | Caminho para o arquivo de entrada         | `dados.txt`                        |
| `--termux, -t`   | Usa o `.txt` baixado no Telegram (Termux) | `--termux`                         |
| `--nome, -n`     | Filtrar por nome                          | `--nome FERREIRA`                  |
| `--modo, -m`     | Filtar por Modo (`exato`, `contem`)       | `--modo contem`                    |
| `--sexo, -s`     | Filtrar por sexo (M ou F)                 | `--sexo F`                         |
| `--idade_min`    | Idade mínima                              | `--idade_min 18`                   |
| `--idade_max`    | Idade máxima                              | `--idade_max 50`                   |
| `--print, -p`    | Imprime resultados no terminal            | `--print`                          |

---

## 📦 Instalação

Clone o repositório:

```bash
git clone https://github.com/HillyWilly/filtrapx
cd filtrapx
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

Ou use o script de instalação no **Termux**:

```bash
bash setup.py
```

---

## 📁 Saída

O resultado filtrado será salvo automaticamente em:

```
out/resultados.txt
```

---

## 📝 Licença

Distribuído sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais informações.

---

## 💡 Exemplo de Saída

```text
Nome: JOAO DA SILVA
CPF: 12345678901
Nascimento: 15/04/1985
Sexo: M
Idade: 40
-----------------------
```

---

Feito com 💻 por [@c0rr0syv3](https://github.com/c0rr0syv3)

