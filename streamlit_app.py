import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import random
import os
import io

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Generador de Collages", layout="centered")

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
    """Calcula el tamaño máximo de fuente uniforme."""
    tamano_actual = tamano_inicial
    try:
        # En Streamlit Cloud (Linux), arialbd.ttf podría no estar disponible. 
        # Si tienes la fuente, súbela junto al script. Si no, usará la por defecto.
        fuente = ImageFont.truetype(nombre_fuente, tamano_actual)
        
        while tamano_actual > 12:
            todos_caben = True
            for texto, max_ancho in zip(textos, anchos_maximos):
                bbox = draw.textbbox((0, 0), texto, font=fuente)
                ancho_texto = bbox[2] - bbox[0]
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

def generar_collage(datos_imagenes, logo_file):
    """Función principal que procesa y genera la imagen final en memoria."""
    # Configuraciones estrictas originales
    CONFIG = {
        'ANCHO_LIENZO': 1600,
        'ALTO_LIENZO': 1147,
        'MARGEN_SUPERIOR': 90,  
        'ESPACIADO_X': 24,      
        'MAX_ALTO_IMG': 580,    
        'MAX_ANCHO_TOTAL': 1500,
        'FUENTE_TTF': 'arialbd.ttf', # Sube este archivo a tu repo si quieres usarla
        'TAMANO_BASE_NOMBRE': 48,
        'TAMANO_BASE_LUGAR': 72
    }

    lienzo = Image.new('RGB', (CONFIG['ANCHO_LIENZO'], CONFIG['ALTO_LIENZO']))
    draw = ImageDraw.Draw(lienzo)
    dibujar_degradado_aleatorio(lienzo, draw)

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
        anchos_permitidos_por_columna.append(d['nuevo_ancho'] + CONFIG['ESPACIADO_X'])
    
    ancho_total_real += (CONFIG['ESPACIADO_X'] * 2)
    pos_x_actual = (CONFIG['ANCHO_LIENZO'] - ancho_total_real) // 2

    autores = [d['autor'] for d in datos_imagenes]
    lugares = [d['lugar'] for d in datos_imagenes]

    fuente_nombre_global = calcular_fuente_uniforme_global(
        autores, anchos_permitidos_por_columna, CONFIG['FUENTE_TTF'], CONFIG['TAMANO_BASE_NOMBRE'], draw
    )
    
    fuente_lugar_global = calcular_fuente_uniforme_global(
        lugares, anchos_permitidos_por_columna, CONFIG['FUENTE_TTF'], CONFIG['TAMANO_BASE_LUGAR'], draw
    )

    max_y_texto_detectado = 0

    for d in datos_imagenes:
        lienzo.paste(d['img_redimensionada'], (pos_x_actual, CONFIG['MARGEN_SUPERIOR']))
        centro_img_x = pos_x_actual + (d['nuevo_ancho'] // 2)

        y_texto_nombre = CONFIG['MARGEN_SUPERIOR'] + alto_final_img + 25
        bbox_nombre = draw.textbbox((0, 0), d['autor'], font=fuente_nombre_global)
        w_nombre = bbox_nombre[2] - bbox_nombre[0]
        h_nombre = bbox_nombre[3] - bbox_nombre[1]
        
        draw.text((centro_img_x - (w_nombre / 2), y_texto_nombre), d['autor'], font=fuente_nombre_global, fill="white")
        
        y_texto_lugar = y_texto_nombre + h_nombre + 5 
        bbox_lugar = draw.textbbox((0, 0), d['lugar'], font=fuente_lugar_global)
        w_lugar = bbox_lugar[2] - bbox_lugar[0]
        h_lugar = bbox_lugar[3] - bbox_lugar[1]
        
        draw.text((centro_img_x - (w_lugar / 2), y_texto_lugar), d['lugar'], font=fuente_lugar_global, fill="white")

        if y_texto_lugar + h_lugar > max_y_texto_detectado:
             max_y_texto_detectado = y_texto_lugar + h_lugar

        pos_x_actual += d['nuevo_ancho'] + CONFIG['ESPACIADO_X']

    # Procesar Logo subido por el usuario
    if logo_file is not None:
        logo = Image.open(logo_file).convert("RGB") 
        ancho_logo = 260 
        proporcion = ancho_logo / float(logo.size[0])
        alto_logo = int(float(logo.size[1]) * float(proporcion))
        logo = logo.resize((ancho_logo, alto_logo), Image.Resampling.LANCZOS)
        
        pos_x_logo = (CONFIG['ANCHO_LIENZO'] - ancho_logo) // 2
        pos_y_logo = max(max_y_texto_detectado + 40, CONFIG['ALTO_LIENZO'] - alto_logo - 40)
        
        lienzo.paste(logo, (pos_x_logo, pos_y_logo))

    return lienzo

# --- INTERFAZ DE USUARIO STREAMLIT ---
st.title("🖼️ Creador de Collages de Lira")
st.write("Sube 3 imágenes para generar tu composición. El nombre del archivo se usará como el Autor.")

# Columnas para organizar las subidas de archivos
col1, col2, col3 = st.columns(3)

with col1:
    img1_file = st.file_uploader("Imagen 1", type=['jpg', 'jpeg', 'png'])
    if img1_file:
        autor1 = os.path.splitext(img1_file.name)[0]
        st.info(f"Autor: {autor1}")
        lugar1 = st.text_input("Lugar para Imagen 1", key="lugar1").strip().upper()

with col2:
    img2_file = st.file_uploader("Imagen 2", type=['jpg', 'jpeg', 'png'])
    if img2_file:
        autor2 = os.path.splitext(img2_file.name)[0]
        st.info(f"Autor: {autor2}")
        lugar2 = st.text_input("Lugar para Imagen 2", key="lugar2").strip().upper()

with col3:
    img3_file = st.file_uploader("Imagen 3", type=['jpg', 'jpeg', 'png'])
    if img3_file:
        autor3 = os.path.splitext(img3_file.name)[0]
        st.info(f"Autor: {autor3}")
        lugar3 = st.text_input("Lugar para Imagen 3", key="lugar3").strip().upper()

st.divider()

# Logo opcional
st.write("### Opcional: Subir Logotipo")
logo_upload = st.file_uploader("Sube el logotipo (jpg, png)", type=['jpg', 'jpeg', 'png'])

# Lógica de procesamiento
if img1_file and img2_file and img3_file:
    # Verificamos que el usuario haya escrito los lugares
    if lugar1 and lugar2 and lugar3:
        if st.button("Generar Collage", type="primary", use_container_width=True):
            with st.spinner("Procesando imágenes y calculando matemáticas..."):
                try:
                    # Preparar los datos tal como los espera tu lógica
                    datos_imagenes = [
                        {
                            'img_obj': Image.open(img1_file).convert("RGB"),
                            'autor': autor1,
                            'lugar': lugar1
                        },
                        {
                            'img_obj': Image.open(img2_file).convert("RGB"),
                            'autor': autor2,
                            'lugar': lugar2
                        },
                        {
                            'img_obj': Image.open(img3_file).convert("RGB"),
                            'autor': autor3,
                            'lugar': lugar3
                        }
                    ]

                    # Calcular ratios
                    for d in datos_imagenes:
                        d['ratio'] = d['img_obj'].width / d['img_obj'].height

                    # Generar la imagen
                    imagen_final = generar_collage(datos_imagenes, logo_upload)

                    # Mostrar el resultado
                    st.success("¡Collage generado con éxito!")
                    st.image(imagen_final, caption="Resultado Final", use_container_width=True)

                    # Convertir a bytes para el botón de descarga
                    buf = io.BytesIO()
                    imagen_final.save(buf, format="JPEG", quality=95)
                    byte_im = buf.getvalue()

                    st.download_button(
                        label="⬇️ Descargar Collage HD",
                        data=byte_im,
                        file_name="collage_lira.jpeg",
                        mime="image/jpeg",
                        use_container_width=True
                    )

                except Exception as e:
                    st.error(f"Ocurrió un error al procesar las imágenes: {e}")
    else:
        st.warning("Por favor, ingresa el 'Lugar' para las 3 imágenes antes de continuar.")
else:
    st.info("Esperando a que subas las 3 imágenes necesarias...")
