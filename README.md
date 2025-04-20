# filtrapx

Processador de Dados de Bots de Busca

Este é um utilitário em Python para processar, limpar e extrair dados estruturados de arquivos `.txt` gerados pelos bots de consulta de dados.

## Bots compatíveis

Este script foi desenvolvido especificamente para funcionar com arquivos `.txt` gerados pelos seguintes bots:

- **@AnonimoBuscasOfcBot**
- **@AlexiaBuscasBot**
- **@FocusSearchBot**
- **@MkBuscasBot**
- **@SkynetBlackRobot**

⚠️ **Atenção:** arquivos de texto que **não sejam** saídas desses bots podem gerar **resultados inesperados**, como:

- Perda de dados;
- Dados não filtrados corretamente;
- Categorização incorreta;
- Falhas na estrutura do SQL de saída.

## Funcionalidades

- Limpeza e normalização de texto;
- Correção ortográfica básica;
- Extração de campos: Nome, CPF, Nascimento, Sexo;
- Cálculo automático de idade;
- Geração de comandos SQL para inserção em banco de dados;
- Filtros por nome, sexo e faixa etária via linha de comando.

## Como usar

```bash
filtrapx arquivo.txt --nome JOAO --sexo M --idade_min 25 --idade_max 40
```

Saída gerada em: `out/resultados.txt`

## Instalação

Instale via `git`:

```bash
git clone https://github.com/HillyWilly/filtrapx
```

## Licença

MIT License. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.
