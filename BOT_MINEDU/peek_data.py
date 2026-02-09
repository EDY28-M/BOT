import pandas as pd
try:
    df = pd.read_excel('c:/Users/USER/Downloads/AUTOMATIZARDNI/BOT_MINEDU/DNI_UNIVERSIDADES.xlsx')
    print("COLUMNS:", df.columns.tolist())
    print(df.head(2))
except Exception as e:
    print(e)
