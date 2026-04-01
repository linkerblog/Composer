import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import random
import os
import io

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Generador de Composiciones", layout="centered")

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

def calcular_fuente_uniforme_global(textos, anchos_maximos, ruta_fuente, tamano_inicial, draw):
    """Calcula el tamaño máximo de fuente uniforme."""
    tamano_actual = tamano_inicial
    
    # Se eliminó el fallback a load_default() para evitar textos diminutos.
    # Si la fuente falla, arrojará un error visible en la interfaz.
    fuente = ImageFont.truetype(ruta_fuente, tamano_actual)
    
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
        fuente = ImageFont.truetype(ruta_fuente, tamano_actual)
        
    return fuente

def generar_collage(datos_imagenes, logo_file, ruta_fuente):
    """Función principal que procesa y genera la imagen final en memoria."""
    CONFIG = {
        'ANCHO_LIENZO': 1600,
        'ALTO_LIENZO': 1147,
        'MARGEN_SUPERIOR': 90,  
        'ESPACIADO_X': 24,      
        'MAX_ALTO_IMG': 580,    
        'MAX_ANCHO_TOTAL': 1500,
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
        autores, anchos_permitidos_por_columna, ruta_fuente, CONFIG['TAMANO_BASE_NOMBRE'], draw
    )
    
    fuente_lugar_global = calcular_fuente_uniforme_global(
        lugares, anchos_permitidos_por_columna, ruta_fuente, CONFIG['TAMANO_BASE_LUGAR'], draw
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
st.title("Generador de Composiciones")
st.write("Seleccione los archivos necesarios. El nombre del archivo se utilizará como Autor.")

# --- LECTOR DE FUENTES ---
ruta_carpeta_fuentes = "fuentes"
fuentes_disponibles = []

if os.path.exists(ruta_carpeta_fuentes):
    # Filtramos solo archivos de tipografía
    fuentes_disponibles = [f for f in os.listdir(ruta_carpeta_fuentes) if f.lower().endswith(('.ttf', '.otf'))]

if not fuentes_disponibles:
    st.error(f"No se encontraron fuentes en la carpeta '{ruta_carpeta_fuentes}'. Por favor, verifique el directorio de fuentes.")
    st.stop() # Detiene la ejecución si no hay fuentes para evitar el texto pequeño
else:
    fuente_seleccionada = st.selectbox("Tipografía", fuentes_disponibles)
    ruta_fuente_completa = os.path.join(ruta_carpeta_fuentes, fuente_seleccionada)

st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    img1_file = st.file_uploader("Imagen 1", type=['jpg', 'jpeg', 'png'])
    if img1_file:
        autor1 = os.path.splitext(img1_file.name)[0]
        st.info(f"Autor: {autor1}")
        lugar1 = st.text_input("Lugar (Imagen 1)", key="lugar1").strip().upper()

with col2:
    img2_file = st.file_uploader("Imagen 2", type=['jpg', 'jpeg', 'png'])
    if img2_file:
        autor2 = os.path.splitext(img2_file.name)[0]
        st.info(f"Autor: {autor2}")
        lugar2 = st.text_input("Lugar (Imagen 2)", key="lugar2").strip().upper()

with col3:
    img3_file = st.file_uploader("Imagen 3", type=['jpg', 'jpeg', 'png'])
    if img3_file:
        autor3 = os.path.splitext(img3_file.name)[0]
        st.info(f"Autor: {autor3}")
        lugar3 = st.text_input("Lugar (Imagen 3)", key="lugar3").strip().upper()

st.divider()

st.write("### Opciones Adicionales")
logo_upload = st.file_uploader("Logotipo (Opcional)", type=['jpg', 'jpeg', 'png'])

if img1_file and img2_file and img3_file:
    if lugar1 and lugar2 and lugar3:
        if st.button("Generar Composición", type="primary", use_container_width=True):
            with st.spinner("Procesando archivos..."):
                try:
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

                    for d in datos_imagenes:
                        d['ratio'] = d['img_obj'].width / d['img_obj'].height

                    # Pasamos la ruta de la fuente elegida
                    imagen_final = generar_collage(datos_imagenes, logo_upload, ruta_fuente_completa)

                    st.success("Proceso completado.")
                    st.image(imagen_final, caption="Resultado", use_container_width=True)

                    buf = io.BytesIO()
                    imagen_final.save(buf, format="JPEG", quality=95)
                    byte_im = buf.getvalue()

                    st.download_button(
                        label="Descargar Composición",
                        data=byte_im,
                        file_name="composicion_final.jpeg",
                        mime="image/jpeg",
                        use_container_width=True
                    )

                except Exception as e:
                    st.error(f"Error de procesamiento: {e}")
    else:
        st.warning("Se requiere ingresar el campo 'Lugar' para las 3 imágenes.")
else:
    st.info("Esperando carga de archivos...")