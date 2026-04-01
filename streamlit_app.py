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
    """Convierte un color hex de Streamlit (#RRGGBB) a tupla RGB."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def generar_collage(datos_imagenes, logo_file, ruta_fuente, offset_y_texto, aplicar_marco, estilo_marco, color_marco_hex, colores, ruido_intensidad):
    CONFIG = {
        'MARGEN_SUPERIOR': 100,  
        'MARGEN_LATERAL': 100,
        'ESPACIADO_X': 35,      
        'ALTO_BASE_IMG': 600, # Altura estandarizada inamovible para evitar recortes
        'TAMANO_BASE_NOMBRE': 48,
        'TAMANO_BASE_LUGAR': 72
    }

    # 1. Pre-cálculo de dimensiones y redimensionado de imágenes
    alto_final_img = CONFIG['ALTO_BASE_IMG']
    ancho_contenido_total = 0
    anchos_col = []

    for d in datos_imagenes:
        nuevo_ancho = int(alto_final_img * d['ratio'])
        d['img_redimensionada'] = d['img_obj'].resize((nuevo_ancho, alto_final_img), Image.Resampling.LANCZOS)
        ancho_contenido_total += nuevo_ancho
        anchos_col.append(nuevo_ancho + CONFIG['ESPACIADO_X'])

    ancho_contenido_total += (CONFIG['ESPACIADO_X'] * (len(datos_imagenes) - 1))
    
    # 2. Definición dinámica del ANCHO del lienzo
    ANCHO_LIENZO = ancho_contenido_total + (CONFIG['MARGEN_LATERAL'] * 2)

    # 3. Pre-cálculo de fuentes y altura de textos
    dummy_img = Image.new('RGB', (1, 1))
    dummy_draw = ImageDraw.Draw(dummy_img)
    
    autores = [d['autor'] for d in datos_imagenes]
    lugares = [d['lugar'] for d in datos_imagenes]
    
    f_nombre = calcular_fuente_uniforme_global(autores, anchos_col, ruta_fuente, CONFIG['TAMANO_BASE_NOMBRE'], dummy_draw)
    f_lugar = calcular_fuente_uniforme_global(lugares, anchos_col, ruta_fuente, CONFIG['TAMANO_BASE_LUGAR'], dummy_draw)

    max_y_texto = 0
    for d in datos_imagenes:
        y_n = CONFIG['MARGEN_SUPERIOR'] + alto_final_img + 30 + offset_y_texto
        bn = dummy_draw.textbbox((0, 0), d['autor'], font=f_nombre)
        y_l = y_n + (bn[3] - bn[1]) + 10
        bl = dummy_draw.textbbox((0, 0), d['lugar'], font=f_lugar)
        max_y_texto = max(max_y_texto, y_l + (bl[3] - bl[1]))

    # 4. Procesamiento del Logo y definición dinámica del ALTO del lienzo
    logo_procesado = None
    alto_logo = 0
    if logo_file:
        logo_original = Image.open(logo_file).convert("RGBA")
        proporcion = 260 / float(logo_original.size[0])
        alto_logo = int(float(logo_original.size[1]) * proporcion)
        logo_procesado = logo_original.resize((260, alto_logo), Image.Resampling.LANCZOS)

    ALTO_LIENZO = max_y_texto + 80
    if logo_procesado:
        ALTO_LIENZO += alto_logo + 40

    # 5. Renderizado final sobre el Lienzo Dinámico
    lienzo = Image.new('RGB', (ANCHO_LIENZO, ALTO_LIENZO))
    dibujar_degradado_avanzado(lienzo, colores, ruido_intensidad)
    draw = ImageDraw.Draw(lienzo)

    pos_x_actual = CONFIG['MARGEN_LATERAL']
    color_marco_rgb = hex_a_rgb(color_marco_hex)

    for d in datos_imagenes:
        lienzo.paste(d['img_redimensionada'], (pos_x_actual, CONFIG['MARGEN_SUPERIOR']))
        
        if aplicar_marco:
            x0, y0 = pos_x_actual, CONFIG['MARGEN_SUPERIOR']
            x1, y1 = x0 + d['img_redimensionada'].width - 1, y0 + alto_final_img - 1
            
            if estilo_marco == "Sólido": 
                draw.rectangle([x0, y0, x1, y1], outline=color_marco_rgb, width=2)
            else:
                p, l = (4, 2) if estilo_marco == "Punteado" else (12, 6)
                for x in range(x0, x1 + 1, p):
                    draw.line([(x, y0), (min(x + l - 1, x1), y0)], fill=color_marco_rgb, width=2)
                    draw.line([(x, y1), (min(x + l - 1, x1), y1)], fill=color_marco_rgb, width=2)
                for y in range(y0, y1 + 1, p):
                    draw.line([(x0, y), (x0, min(y + l - 1, y1))], fill=color_marco_rgb, width=2)
                    draw.line([(x1, y), (x1, min(y + l - 1, y1))], fill=color_marco_rgb, width=2)

        cx = pos_x_actual + (d['img_redimensionada'].width // 2)
        
        y_n = CONFIG['MARGEN_SUPERIOR'] + alto_final_img + 30 + offset_y_texto
        bn = draw.textbbox((0, 0), d['autor'], font=f_nombre)
        draw.text((cx - (bn[2]-bn[0])/2, y_n), d['autor'], font=f_nombre, fill="white")
        
        y_l = y_n + (bn[3]-bn[1]) + 10 
        bl = draw.textbbox((0, 0), d['lugar'], font=f_lugar)
        draw.text((cx - (bl[2]-bl[0])/2, y_l), d['lugar'], font=f_lugar, fill="white")
        
        pos_x_actual += d['img_redimensionada'].width + CONFIG['ESPACIADO_X']

    if logo_procesado:
        px_l = (ANCHO_LIENZO - 260) // 2
        py_l = ALTO_LIENZO - alto_logo - 40
        lienzo.paste(logo_procesado, (px_l, py_l), logo_procesado)

    return lienzo

# --- UI STREAMLIT ---
st.title("Generador de Composiciones")

directorio_actual = os.path.dirname(os.path.abspath(__file__))
ruta_fuentes = os.path.join(directorio_actual, "fuentes")
if not os.path.exists(ruta_fuentes): os.makedirs(ruta_fuentes)
fuentes = [f for f in os.listdir(ruta_fuentes) if f.lower().endswith(('.ttf', '.otf'))]

if not fuentes:
    st.warning("Inserta tipografías en la carpeta 'fuentes'.")
else:
    f_sel = st.selectbox("Tipografía", fuentes)
    ruta_f = os.path.join(ruta_fuentes, f_sel)

st.divider()
c1, c2, c3 = st.columns(3)
img1 = c1.file_uploader("Foto 1", type=['jpg', 'png'])
img2 = c2.file_uploader("Foto 2", type=['jpg', 'png'])
img3 = c3.file_uploader("Foto 3", type=['jpg', 'png'])

if img1 and img2 and img3:
    l1 = c1.text_input("Ubicación 1").strip().upper()
    l2 = c2.text_input("Ubicación 2").strip().upper()
    l3 = c3.text_input("Ubicación 3").strip().upper()
    
    st.divider()
    st.write("### Personalización Avanzada")
    logo_u = st.file_uploader("Logo (PNG Transparente)", type=['png', 'jpg'])
    
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        off_t = st.slider("Altura de Texto (Offset px)", -50, 50, 0)
        ruido_i = st.slider("Intensidad de Ruido (Grano)", 0, 100, 60)
        usar_aleatorio = st.checkbox("Usar paleta aleatoria", value=False)
    with col_b:
        marcar = st.checkbox("Enmarcar fotos")
        estilo_m = st.selectbox("Tipo de patrón", ["Sólido", "Punteado", "Discontinuo"], disabled=not marcar)
    with col_c:
        color_borde = st.color_picker("Color del borde", "#FFFFFF", disabled=not marcar)

    if l1 and l2 and l3:
        if st.button("Generar Composición", type="primary", width='stretch'):
            with st.spinner("Motor de Lienzo Dinámico en marcha..."):
                try:
                    # ImageOps.exif_transpose previene rotaciones extrañas y recortes accidentales
                    datos = [
                        {'img_obj': ImageOps.exif_transpose(Image.open(img1).convert("RGB")), 'autor': os.path.splitext(img1.name)[0], 'lugar': l1},
                        {'img_obj': ImageOps.exif_transpose(Image.open(img2).convert("RGB")), 'autor': os.path.splitext(img2.name)[0], 'lugar': l2},
                        {'img_obj': ImageOps.exif_transpose(Image.open(img3).convert("RGB")), 'autor': os.path.splitext(img3.name)[0], 'lugar': l3}
                    ]
                    for d in datos: d['ratio'] = d['img_obj'].width / d['img_obj'].height

                    if usar_aleatorio:
                        paleta = generar_paleta_analoga()
                    else:
                        paleta = extraer_colores_de_imagenes(datos)

                    final = generar_collage(
                        datos, logo_u, ruta_f, off_t, 
                        marcar, estilo_m, color_borde, 
                        paleta, ruido_i
                    )
                    
                    st.image(final, width='stretch')
                    
                    buf = io.BytesIO()
                    final.save(buf, format="JPEG", quality=100)
                    st.download_button("Descargar Composición en Alta Calidad", buf.getvalue(), "composicion.jpeg", "image/jpeg", width='stretch')
                except Exception as e: st.error(f"Error crítico en renderizado: {e}")