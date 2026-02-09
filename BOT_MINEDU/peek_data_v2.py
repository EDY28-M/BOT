import pandas as pd
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)
try:
    df = pd.read_excel('c:/Users/USER/Downloads/AUTOMATIZARDNI/BOT_MINEDU/DNI_UNIVERSIDADES.xlsx')
    print("COLUMNS:", df.columns.tolist())
    print("\nSAMPLE DATA:")
    print(df.head(2).to_string())
    print("\nUNIQUE INSTITUCION:")
    if 'INSTITUCION' in df.columns:
        print(df['INSTITUCION'].unique())
    elif 'institucion' in df.columns:
        print(df['institucion'].unique())
    else:
        print("INSTITUCION column not found")
except Exception as e:
    print(e)
