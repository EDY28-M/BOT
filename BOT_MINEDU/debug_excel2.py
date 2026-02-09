import pandas as pd
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

try:
    df = pd.read_excel('DNI_UNIVERSIDADES.xlsx', dtype=str)
    print("ALL COLUMNS:", df.columns.tolist())
    
    # Find institution column
    inst_col = None
    for col in df.columns:
        if 'INSTITU' in col.upper():
            inst_col = col
            break
    
    print(f"\nInstitution column: {inst_col}")
    
    if inst_col:
        # Show value counts
        print(f"\nValues in '{inst_col}':")
        print(df[inst_col].value_counts(dropna=False).head(15))
        
        # Filter NO ENCONTRADO
        mask = df[inst_col].str.upper().str.contains('NO SE ENCONTR', na=False)
        no_encontrados = df[mask]
        print(f"\nRows with 'NO SE ENCONTR': {len(no_encontrados)}")
        print(no_encontrados['DNI'].head(10).tolist())
    
except Exception as e:
    import traceback
    traceback.print_exc()
