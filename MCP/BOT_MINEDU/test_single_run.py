from minedu_bot import MinedulBot
import logging

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%H:%M:%S')

# Crear archivo de prueba con un DNI
import pandas as pd

df = pd.DataFrame({
    'DNI': ['10777845']  # DNI de prueba
})

df.to_excel('test_single_dni.xlsx', index=False)

# Ejecutar bot
bot = MinedulBot()
print("="*50)
print("  PRUEBA MINEDU BOT - 1 DNI")
print("="*50)
bot.procesar_lista('test_single_dni.xlsx')
print("\n[OK] Prueba completada")
