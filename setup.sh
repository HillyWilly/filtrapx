#!/bin/bash

echo "Instalando dependências do requirements.txt..."
pip install -r requirements.txt

echo "Dependências instaladas com sucesso."

# Apagar o script após execução
rm -- "$0"
