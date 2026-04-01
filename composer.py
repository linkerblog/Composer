from PIL import Image, ImageDraw, ImageFont
import os
import random
from pathlib import Path

def obtener_color_aleatorio():
    """Genera un color RGB al azar."""
    return (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

def dibujar_degradado_aleatorio(lienzo, draw):
    """Dibuja un degradado lineal en el lienzo con colores aleatorios."""
    color_inicio = obtener_color_aleatorio()
    color_fin = obtener_color_aleatorio()
    
    ancho, alto = lienzo.size
    for y in range(alto):
        r = int(color_inicio[0] + (color_fin[0] - color_inicio[0]) * (y / alto))
        g = int(color_inicio[1] + (color_fin[1] - color_inicio[1]) * (y / alto))
        b = int(color_inicio[2] + (color_fin[2] - color_inicio[2]) * (y / alto))
        draw.line([(0, y), (ancho, y)], fill=(r, g, b))

def calcular_fuente_uniforme_global(textos, anchos_maximos, nombre_fuente, tamano_inicial, draw):
    """
    Calcula el tamaño máximo de fuente que permite que TODOS los textos
    quepan en sus respectivas columnas, garantizando que todos compartan
    el mismo tamaño final para mantener la simetría.
    """
    tamano_actual = tamano_inicial
    try:
        fuente = ImageFont.truetype(nombre_fuente, tamano_actual)
        
        while tamano_actual > 12:
            todos_caben = True
            for texto, max_ancho in zip(textos, anchos_maximos):
                bbox = draw.textbbox((0, 0), texto, font=fuente)
                ancho_texto = bbox[2] - bbox[0]
                # Dejamos 10px de margen de seguridad para que no queden pegados
                if ancho_texto > (max_ancho - 10):
                    todos_caben = False
                    break
            
            if todos_caben:
                break
                
            tamano_actual -= 2
            fuente = ImageFont.truetype(nombre_fuente, tamano_actual)
            
        return fuente
    except IOError:
        return ImageFont.load_default()

def main():
    # --- CONFIGURACIONES ESTRICTAS ---
    CONFIG = {
        'ANCHO_LIENZO': 1600,
        'ALTO_LIENZO': 1147,
        'MARGEN_SUPERIOR': 90,  
        'ESPACIADO_X': 24,      
        'MAX_ALTO_IMG': 580,    
        'MAX_ANCHO_TOTAL': 1500,
        'ARCHIVO_LOGO_JPEG': 'logo.jpeg',
        'ARCHIVO_FINAL': 'resultado_final_1600x1147.jpeg',
        'FUENTE_TTF': 'arialbd.ttf',
        'TAMANO_BASE_NOMBRE': 48,
        'TAMANO_BASE_LUGAR': 72
    }

    print("Generando lienzo...")
    lienzo = Image.new('RGB', (CONFIG['ANCHO_LIENZO'], CONFIG['ALTO_LIENZO']))
    draw = ImageDraw.Draw(lienzo)
    dibujar_degradado_aleatorio(lienzo, draw)

    # --- PASO 1: Identificar la carpeta de Descargas del sistema ---
    ruta_descargas = str(Path.home() / "Downloads")
    
    if not os.path.exists(ruta_descargas):
        print(f"Error: No se pudo localizar la carpeta de Descargas en: {ruta_descargas}")
        return

    # --- PASO 2: Filtrado y Ordenamiento Único ---
    extensiones_validas = {'.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG'}
    archivos_a_ignorar = {CONFIG['ARCHIVO_LOGO_JPEG'].lower(), CONFIG['ARCHIVO_FINAL'].lower()}
    
    lista_archivos_unicos = []
    
    print("\nEscaneando carpeta de Descargas de manera unica...")
    with os.scandir(ruta_descargas) as entries:
        for entry in entries:
            if entry.is_file() and os.path.splitext(entry.name)[1] in extensiones_validas:
                if entry.name.lower() not in archivos_a_ignorar:
                    lista_archivos_unicos.append({
                        'ruta': entry.path,
                        'mtime': entry.stat().st_mtime,
                        'nombre': entry.name
                    })

    if len(lista_archivos_unicos) < 3:
        print(f"Error: Se requieren al menos 3 imagenes en la carpeta de Descargas. Solo se encontraron {len(lista_archivos_unicos)}.")
        return

    lista_archivos_unicos.sort(key=lambda x: x['mtime'], reverse=True)
    imagenes_a_procesar = lista_archivos_unicos[:3]
    datos_imagenes = []
        
    # --- PASO 3: Recopilar datos interactivos ---
    for item in imagenes_a_procesar:
        ruta_img = item['ruta']
        nombre_archivo = item['nombre']
        nombre_autor = os.path.splitext(nombre_archivo)[0]
        
        print(f"\n--- Procesando archivo: {nombre_archivo} ---")
        print(f"Autor detectado: {nombre_autor}")
        lugar = input(f"Ingrese el ESTADO o MUNICIPIO para esta imagen: ").strip().upper()

        try:
            img_original = Image.open(ruta_img).convert("RGB")
            datos_imagenes.append({
                'img_obj': img_original,
                'autor': nombre_autor,
                'lugar': lugar,
                'ratio': img_original.width / img_original.height
            })
        except Exception as e:
            print(f"Error al cargar {ruta_img}: {e}")
            return

    # --- PASO 4: Matemática de dimensiones estricta ---
    suma_ratios = sum(d['ratio'] for d in datos_imagenes)
    espacio_disponible_w = CONFIG['MAX_ANCHO_TOTAL'] - (CONFIG['ESPACIADO_X'] * 2)
    
    alto_calculado = espacio_disponible_w / suma_ratios
    alto_final_img = int(min(CONFIG['MAX_ALTO_IMG'], alto_calculado))

    ancho_total_real = 0
    anchos_permitidos_por_columna = []

    for d in datos_imagenes:
        d['nuevo_ancho'] = int(alto_final_img * d['ratio'])
        d['img_redimensionada'] = d['img_obj'].resize((d['nuevo_ancho'], alto_final_img), Image.Resampling.LANCZOS)
        ancho_total_real += d['nuevo_ancho']
        
        # El texto puede usar el ancho de su imagen más el espaciado lateral
        anchos_permitidos_por_columna.append(d['nuevo_ancho'] + CONFIG['ESPACIADO_X'])
    
    ancho_total_real += (CONFIG['ESPACIADO_X'] * 2)
    pos_x_actual = (CONFIG['ANCHO_LIENZO'] - ancho_total_real) // 2

    # --- PASO 5: Cálculo de Tipografía Uniforme Global ---
    autores = [d['autor'] for d in datos_imagenes]
    lugares = [d['lugar'] for d in datos_imagenes]

    fuente_nombre_global = calcular_fuente_uniforme_global(
        autores, anchos_permitidos_por_columna, CONFIG['FUENTE_TTF'], CONFIG['TAMANO_BASE_NOMBRE'], draw
    )
    
    fuente_lugar_global = calcular_fuente_uniforme_global(
        lugares, anchos_permitidos_por_columna, CONFIG['FUENTE_TTF'], CONFIG['TAMANO_BASE_LUGAR'], draw
    )

    # --- PASO 6: Colocación de Imágenes y Textos ---
    max_y_texto_detectado = 0

    for d in datos_imagenes:
        lienzo.paste(d['img_redimensionada'], (pos_x_actual, CONFIG['MARGEN_SUPERIOR']))
        centro_img_x = pos_x_actual + (d['nuevo_ancho'] // 2)

        # --- TEXTO: Autor ---
        y_texto_nombre = CONFIG['MARGEN_SUPERIOR'] + alto_final_img + 25
        bbox_nombre = draw.textbbox((0, 0), d['autor'], font=fuente_nombre_global)
        w_nombre = bbox_nombre[2] - bbox_nombre[0]
        h_nombre = bbox_nombre[3] - bbox_nombre[1]
        
        draw.text((centro_img_x - (w_nombre / 2), y_texto_nombre), d['autor'], font=fuente_nombre_global, fill="white")
        
        # --- TEXTO: Lugar ---
        y_texto_lugar = y_texto_nombre + h_nombre + 5 # Interlineado cerrado
        bbox_lugar = draw.textbbox((0, 0), d['lugar'], font=fuente_lugar_global)
        w_lugar = bbox_lugar[2] - bbox_lugar[0]
        h_lugar = bbox_lugar[3] - bbox_lugar[1]
        
        draw.text((centro_img_x - (w_lugar / 2), y_texto_lugar), d['lugar'], font=fuente_lugar_global, fill="white")

        # Rastrear el punto más bajo del texto
        if y_texto_lugar + h_lugar > max_y_texto_detectado:
             max_y_texto_detectado = y_texto_lugar + h_lugar

        pos_x_actual += d['nuevo_ancho'] + CONFIG['ESPACIADO_X']

    # --- PASO 7: Procesar el Logo JPEG ---
    ruta_logo_jpeg = CONFIG['ARCHIVO_LOGO_JPEG']
    if os.path.exists(ruta_logo_jpeg):
        print("\nInsertando logotipo JPEG...")
        logo = Image.open(ruta_logo_jpeg).convert("RGB") 
        ancho_logo = 260 
        proporcion = ancho_logo / float(logo.size[0])
        alto_logo = int(float(logo.size[1]) * float(proporcion))
        logo = logo.resize((ancho_logo, alto_logo), Image.Resampling.LANCZOS)
        
        pos_x_logo = (CONFIG['ANCHO_LIENZO'] - ancho_logo) // 2
        pos_y_logo = max(max_y_texto_detectado + 40, CONFIG['ALTO_LIENZO'] - alto_logo - 40)
        
        lienzo.paste(logo, (pos_x_logo, pos_y_logo))
    else:
        print(f"\nAdvertencia: No se encontro el archivo '{ruta_logo_jpeg}' en el directorio actual. Se omitira el logotipo.")

    lienzo.save(CONFIG['ARCHIVO_FINAL'], quality=95)
    print(f"\nProceso completado. Archivo guardado en el directorio actual como: {CONFIG['ARCHIVO_FINAL']}")

if __name__ == "__main__":
    main()