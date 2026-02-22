#!/bin/bash
# Script para ejecutar el ciclo autónomo

cd "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"

source ~/coinbase_trader_venv/bin/activate

python autonomous_trader.py --status
