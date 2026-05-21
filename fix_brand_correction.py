import json

nb_path = r"c:/Users/Carlos Ahumada Soles/OneDrive/Documentos/Proyecto_ML/Proyecto_ML_Ferreteria_COSTOS.ipynb"

with open(nb_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

# Find the cell with the imputation code (by looking for the fillna for 'marca')
for cell in nb.get('cells', []):
    if cell.get('cell_type') == 'code':
        source = ''.join(cell.get('source', []))
        if "df['marca'] = df['marca'].fillna('desconocida')" in source:
            # Update the source with corrected code
            new_source = [
                "# Imputación de valores nulos y corrección de errores de escritura\n",
                "df['marca'] = df['marca'].fillna('desconocida')\n",
                "# Corregir errores comunes de escritura en la columna 'marca'\n",
                "df['marca'] = df['marca'].replace({'desconcocida': 'desconocida', 'desconocida': 'desconocida'})\n",
                "df['tipo_producto'] = df['tipo_producto'].fillna('No especificado')\n",
                "df['categoria'] = df['categoria'].fillna('Sin categoría')\n",
                "\n",
                "df['cantidad'] = df['cantidad'].fillna(df['cantidad'].median())\n",
                "df['precio_unitario'] = df['precio_unitario'].fillna(df['precio_unitario'].median())\n",
                "df['precio_total'] = df['precio_total'].fillna(df['precio_total'].median())\n"
            ]
            cell['source'] = new_source
            break

with open(nb_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
print('Imputation cell updated successfully.')
