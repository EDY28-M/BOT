import pandas as pd
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

try:
    df = pd.read_excel('DNI_UNIVERSIDADES.xlsx', dtype=str)
    print("COLUMNS:")
    for i, col in enumerate(df.columns):
        print(f"  [{i}] {repr(col)}")
    print("\nFIRST 3 ROWS:")
    print(df.head(3).to_string())
    print("\nTOTAL ROWS:", len(df))
    
    # Check for INSTITUCION-like columns
    for col in df.columns:
        if 'INSTIT' in col.upper():
            print(f"\nColumn '{col}' unique values:")
            print(df[col].value_counts(dropna=False).head(10))
except Exception as e:
    print(f"Error: {e}")
