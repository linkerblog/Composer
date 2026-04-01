import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageOps
import random
import os
import io
import math
import colorsys

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Generador de Composiciones", layout="centered")

def generar_paleta_analoga():
    h_base = random.random()
    s = random.uniform(0.65, 0.85)
    v = random.uniform(0.75, 0.95)
    colores = []
    for offset in [0, 0.12, -0.08]: 
        h = (h_base + offset) % 1.0
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        colores.append((int(r*255), int(g*255), int(b*255)))
    return colores

def extraer_colores_de_imagenes(datos_imagenes):
    colores = []
    for d in datos_imagenes:
        img_peq = d['img_obj'].resize((1, 1), Image.Resampling.LANCZOS)
        colores.append(img_peq.getpixel((0, 0)))
    return colores

def dibujar_degradado_avanzado(lienzo, colores, ruido_intensidad):
    ancho, alto = lienzo.size
    color1, color2, color3 = colores
    
    escala = 10
    w_peq, h_peq = ancho // escala, alto // escala
    img_base = Image.new('RGB', (w_peq, h_peq))
    
    for y in range(h_peq):
        for x in range(w_peq):
            nx = x / w_peq
            ny = y / h_peq
            
            inf1 = max(0, 1 - math.sqrt(nx**2 + ny**2))**1.6
            inf2 = max(0, 1 - math.sqrt((1-nx)**2 + (1-ny)**2))**1.4
            inf3 = max(0, 1 - math.sqrt((0.4-nx)**2 + (0.8-ny)**2))**1.8 
            inf4 = max(0, 1 - math.sqrt((1-nx)**2 + ny**2))**1.5 
            
            total = inf1 + inf2 + inf3 + inf4 + 0.001
            
            r = int((color1[0]*(inf1+inf4) + color2[0]*inf2 + color3[0]*inf3) / total)
            g = int((color1[1]*(inf1+inf4) + color2[1]*inf2 + color3[1]*inf3) / total)
            b = int((color1[2]*(inf1+inf4) + color2[2]*inf2 + color3[2]*inf3) / total)
            
            img_base.putpixel((x, y), (r, g, b))
            
    degradado_suave = img_base.resize((ancho, alto), Image.Resampling.LANCZOS)
    
    if ruido_intensidad > 0:
        ruido = Image.effect_noise((ancho, alto), 12).convert('L')
        ruido_rgb = Image.merge('RGB', (ruido, ruido, ruido))
        alpha_ruido = ruido_intensidad / 1000.0 
        lienzo.paste(ImageChops.blend(degradado_suave, ruido_rgb, alpha=alpha_ruido))
    else:
        lienzo.paste(degradado_suave)

def calcular_fuente_uniforme_global(textos, anchos_maximos, ruta_fuente, tamano_inicial, draw):
    tamano_actual = tamano_inicial
    fuente = ImageFont.truetype(ruta_fuente, tamano_actual)
    while tamano_actual > 12:
        todos_caben = True
        for texto, max_ancho in zip(textos, anchos_maximos):
            bbox = draw.textbbox((0, 0), texto, font=fuente)
            if (bbox[2] - bbox[0]) > (max_ancho - 10):
                todos_caben = False
                break
        if todos_caben: break
        tamano_actual -= 2
        fuente = ImageFont.truetype(ruta_fuente, tamano_actual)
    return fuente

def hex_a_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def generar_collage(datos_imagenes, logo_file, ruta_fuente, offset_y_texto, aplicar_marco, estilo_marco, color_marco_hex, colores, ruido_intensidad):
    # Restaurado el lienzo de tamaño estrictamente fijo
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
    dibujar_degradado_avanzado(lienzo, colores, ruido_intensidad)
    draw = ImageDraw.Draw(lienzo)

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
    color_marco_rgb = hex_a_rgb(color_marco_hex)

    for d in datos_imagenes:
        lienzo.paste(d['img_redimensionada'], (pos_x_actual, CONFIG['MARGEN_SUPERIOR']))
        
        if aplicar_marco:
            x0 = pos_x_actual
            y0 = CONFIG['MARGEN_SUPERIOR']
            x1 = pos_x_actual + d['nuevo_ancho'] - 1
            y1 = CONFIG['MARGEN_SUPERIOR'] + alto_final_img - 1
            
            if estilo_marco == "Sólido":
                draw.rectangle([x0, y0, x1, y1], outline=color_marco_rgb, width=2)
            else:
                paso = 4 if estilo_marco == "Punteado" else 12
                largo_linea = 2 if estilo_marco == "Punteado" else 6
                
                for x in range(x0, x1 + 1, paso):
                    draw.line([(x, y0), (min(x + largo_linea - 1, x1), y0)], fill=color_marco_rgb, width=2)
                    draw.line([(x, y1), (min(x + largo_linea - 1, x1), y1)], fill=color_marco_rgb, width=2)
                for y in range(y0, y1 + 1, paso):
                    draw.line([(x0, y), (x0, min(y + largo_linea - 1, y1))], fill=color_marco_rgb, width=2)
                    draw.line([(x1, y), (x1, min(y + largo_linea - 1, y1))], fill=color_marco_rgb, width=2)

        centro_img_x = pos_x_actual + (d['nuevo_ancho'] // 2)

        y_texto_nombre = CONFIG['MARGEN_SUPERIOR'] + alto_final_img + 25 + offset_y_texto
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

    if logo_file is not None:
        logo = Image.open(logo_file).convert("RGBA") 
        ancho_logo = 260 
        proporcion = ancho_logo / float(logo.size[0])
        alto_logo = int(float(logo.size[1]) * float(proporcion))
        logo = logo.resize((ancho_logo, alto_logo), Image.Resampling.LANCZOS)
        
        pos_x_logo = (CONFIG['ANCHO_LIENZO'] - ancho_logo) // 2
        pos_y_logo = max(max_y_texto_detectado + 40, CONFIG['ALTO_LIENZO'] - alto_logo - 30)
        
        if logo.mode == 'RGBA':
            lienzo.paste(logo, (pos_x_logo, pos_y_logo), logo)
        else:
            lienzo.paste(logo, (pos_x_logo, pos_y_logo))

    return lienzo

# --- INTERFAZ DE USUARIO STREAMLIT ---
st.title("Generador de Composiciones")

directorio_actual = os.path.dirname(os.path.abspath(__file__))
ruta_carpeta_fuentes = os.path.join(directorio_actual, "fuentes")

if not os.path.exists(ruta_carpeta_fuentes):
    os.makedirs(ruta_carpeta_fuentes)

fuentes_disponibles = [f for f in os.listdir(ruta_carpeta_fuentes) if f.lower().endswith(('.ttf', '.otf'))]
ruta_fuente_completa = None

if not fuentes_disponibles:
    st.warning(f"No se detectaron archivos de tipografía (.ttf o .otf) en el directorio '{ruta_carpeta_fuentes}'. Inserte al menos un archivo para habilitar la generación.")
else:
    fuente_seleccionada = st.selectbox("Selección de Tipografía", fuentes_disponibles)
    ruta_fuente_completa = os.path.join(ruta_carpeta_fuentes, fuente_seleccionada)

st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    img1_file = st.file_uploader("Archivo 1", type=['jpg', 'jpeg', 'png'])
    if img1_file:
        autor1 = os.path.splitext(img1_file.name)[0]
        lugar1 = st.text_input("Ubicación (Archivo 1)", key="lugar1").strip().upper()

with col2:
    img2_file = st.file_uploader("Archivo 2", type=['jpg', 'jpeg', 'png'])
    if img2_file:
        autor2 = os.path.splitext(img2_file.name)[0]
        lugar2 = st.text_input("Ubicación (Archivo 2)", key="lugar2").strip().upper()

with col3:
    img3_file = st.file_uploader("Archivo 3", type=['jpg', 'jpeg', 'png'])
    if img3_file:
        autor3 = os.path.splitext(img3_file.name)[0]
        lugar3 = st.text_input("Ubicación (Archivo 3)", key="lugar3").strip().upper()

st.divider()

st.write("### Opciones Adicionales")
logo_upload = st.file_uploader("Logotipo (Opcional)", type=['jpg', 'jpeg', 'png'])

col_opc1, col_opc2, col_opc3 = st.columns(3)
with col_opc1:
    offset_texto = st.slider("Ajuste vertical de los textos (px)", min_value=-50, max_value=50, value=0)
    ruido_i = st.slider("Intensidad de Ruido (Grano)", 0, 100, 60)
    usar_aleatorio = st.checkbox("Usar paleta de colores aleatoria", value=False)
with col_opc2:
    aplicar_marco = st.checkbox("Aplicar marco a las fotos")
    estilo_marco = st.selectbox("Patrón del marco", ["Sólido", "Punteado", "Discontinuo"], disabled=not aplicar_marco)
with col_opc3:
    color_marco_hex = st.color_picker("Color del marco", "#FFFFFF", disabled=not aplicar_marco)

if img1_file and img2_file and img3_file:
    if lugar1 and lugar2 and lugar3:
        if ruta_fuente_completa:
            if st.button("Generar Composición", type="primary", width='stretch'):
                with st.spinner("Procesando datos gráficos..."):
                    try:
                        # ImageOps.exif_transpose lee y corrige la orientación real de tus fotos antes de cualquier cálculo
                        datos_imagenes = [
                            {'img_obj': ImageOps.exif_transpose(Image.open(img1_file).convert("RGB")), 'autor': autor1, 'lugar': lugar1},
                            {'img_obj': ImageOps.exif_transpose(Image.open(img2_file).convert("RGB")), 'autor': autor2, 'lugar': lugar2},
                            {'img_obj': ImageOps.exif_transpose(Image.open(img3_file).convert("RGB")), 'autor': autor3, 'lugar': lugar3}
                        ]

                        for d in datos_imagenes:
                            d['ratio'] = d['img_obj'].width / d['img_obj'].height

                        if usar_aleatorio:
                            paleta = generar_paleta_analoga()
                        else:
                            paleta = extraer_colores_de_imagenes(datos_imagenes)

                        imagen_final = generar_collage(
                            datos_imagenes, logo_upload, ruta_fuente_completa, 
                            offset_texto, aplicar_marco, estilo_marco, color_marco_hex, 
                            paleta, ruido_i
                        )

                        st.success("Procesamiento completado.")
                        st.image(imagen_final, caption="Resultado Final", width='stretch')

                        buf = io.BytesIO()
                        imagen_final.save(buf, format="JPEG", quality=95)
                        byte_im = buf.getvalue()

                        st.download_button(
                            label="Descargar Composición",
                            data=byte_im,
                            file_name="composicion_final.jpeg",
                            mime="image/jpeg",
                            width='stretch'
                        )

                    except Exception as e:
                        st.error(f"Error interno de procesamiento: {e}")
        else:
             st.error("Es necesario seleccionar una tipografía para proceder.")
    else:
        st.warning("Se requiere completar el campo 'Ubicación' para los tres archivos.")
else:
    st.info("Esperando carga de archivos requeridos...")