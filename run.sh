#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

echo "==> Zaruma Gestión"

if [ ! -d ".venv" ]; then
    echo "==> Creando entorno virtual..."
    python3 -m venv .venv
fi

echo "==> Activando entorno virtual..."
source .venv/bin/activate

echo "==> Instalando/actualizando dependencias..."
pip install -r requirements.txt

echo "==> Arrancando servidor local..."
echo "==> Abre en el navegador: http://127.0.0.1:8000"
echo ""

uvicorn main:app --reload
