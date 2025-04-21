#!/bin/bash

# Verifica se está rodando no Termux
if command -v termux-setup-storage > /dev/null; then
    echo "Termux identificado. Executando termux-setup-storage..."
    termux-setup-storage

    # Espera um pouco para garantir que a permissão seja concedida
    sleep 2

    # Verifica se a pasta de downloads do Telegram existe
    TELEGRAM_DIR="$HOME/storage/downloads/Telegram"
    if [ -d "$TELEGRAM_DIR" ]; then
        echo "Pasta de downloads do Telegram encontrada: $TELEGRAM_DIR"
    else
        echo "Não foi possível encontrar a pasta de downloads do Telegram."
    fi
else
    echo "Termux não identificado. Continuando normalmente..."
fi

# Instala o Python3 se não estiver instalado
if ! command -v python3 > /dev/null; then
    echo "Python3 não encontrado. Instalando..."
    pkg install -y python3
else
    echo "Python3 já está instalado."
fi

echo "Instalando dependências do requirements.txt..."
pip install -r requirements.txt

echo "Dependências instaladas com sucesso."

echo "Execute o código desta maneira: 'filtrapx arquivo.txt --nome JOAO --sexo M --idade_min 25 --idade_max 40'"

# Apagar o script após execução
rm -- "$0"
