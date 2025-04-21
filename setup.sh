#!/bin/bash

echo "Instalando dependências do requirements.txt..."
pip install -r requirements.txt

echo "Dependências instaladas com sucesso."

# Apagar o script após execução

echo "Execute o código desta maneira 'filtrapx arquivo.txt --nome JOAO --sexo M --idade_min 25 --idade_max 40' "

rm -- "$0"
