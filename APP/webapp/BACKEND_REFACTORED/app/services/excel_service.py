
import pandas as pd
from typing import List, BinaryIO
from io import BytesIO

class ExcelService:
    @staticmethod
    def parse_uploaded_file(file: BinaryIO, filename: str) -> List[str]:
        dnis = []
        try:
            if filename.endswith(".xlsx") or filename.endswith(".xls"):
                df = pd.read_excel(BytesIO(file.read()))
                # Asumir primera columna o buscar columna 'DNI'
                col = df.columns[0]
                if 'DNI' in df.columns:
                    col = 'DNI'
                
                # Convert to string and clean
                raw_dnis = df[col].astype(str).tolist()
                for d in raw_dnis:
                    clean_d = d.split(".")[0].strip() # Handle '12345678.0'
                    if clean_d.isdigit() and len(clean_d) >= 7:
                        dnis.append(clean_d.zfill(8)) # Pad to 8 chars if needed
            
            elif filename.endswith(".txt") or filename.endswith(".csv"):
                content = file.read().decode("utf-8", errors="ignore")
                lines = content.splitlines()
                for line in lines:
                    clean_d = line.strip()
                    if clean_d.isdigit() and len(clean_d) >= 7:
                        dnis.append(clean_d.zfill(8))
            
            return dnis
        except Exception as e:
            raise ValueError(f"Error parseando archivo: {e}")

    @staticmethod
    def generate_excel(data: List[dict]) -> BytesIO:
        df = pd.DataFrame(data)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Resultados')
        output.seek(0)
        return output
