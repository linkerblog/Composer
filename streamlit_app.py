import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageChops
import random
import os
import io
import math
import colorsys

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Generador de Composiciones", layout="centered")

def generar_paleta_analoga():
    """Genera 3 colores armónicos aleatorios usando el espacio HSV."""
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
    """Idea 1: Extrae el color dominante promedio de cada imagen para crear la paleta."""
    colores = []
    for d in datos_imagenes:
        # Reducimos la imagen a 1x1 para obtener el color promedio dominante de forma eficiente
        img_peq = d['img_obj'].resize((1, 1), Image.Resampling.LANCZOS)
        colores.append(img_peq.getpixel((0, 0)))
    return colores

def dibujar_degradado_avanzado(lienzo, colores, ruido_intensidad):
    """
    Renderiza un degradado tipo malla con iluminación simulada.
    ruido_intensidad: valor de 0 a 100 para la textura.
    """
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
    
    # Idea 2: Ajuste de ruido dinámico
    if ruido_intensidad > 0:
        ruido = Image.effect_noise((ancho, alto), 12).convert('L')
        ruido_rgb = Image.merge('RGB', (ruido, ruido, ruido))
        alpha_ruido = ruido_intensidad / 1000.0 # Normalizamos para que no sea excesivo
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

def generar_collage(datos_imagenes, logo_file, ruta_fuente, offset_y_texto, aplicar_marco, estilo_marco, colores, ruido_intensidad):
    CONFIG = {
        'ANCHO_LIENZO': 1600, 'ALTO_LIENZO': 1147, 'MARGEN_SUPERIOR': 90,  
        'ESPACIADO_X': 24, 'MAX_ALTO_IMG': 580, 'MAX_ANCHO_TOTAL': 1500,
        'TAMANO_BASE_NOMBRE': 48, 'TAMANO_BASE_LUGAR': 72
    }

    lienzo = Image.new('RGB', (CONFIG['ANCHO_LIENZO'], CONFIG['ALTO_LIENZO']))
    dibujar_degradado_avanzado(lienzo, colores, ruido_intensidad)
    draw = ImageDraw.Draw(lienzo)

    suma_ratios = sum(d['ratio'] for d in datos_imagenes)
    espacio_disponible_w = CONFIG['MAX_ANCHO_TOTAL'] - (CONFIG['ESPACIADO_X'] * 2)
    alto_final_img = int(min(CONFIG['MAX_ALTO_IMG'], espacio_disponible_w / suma_ratios))

    ancho_total_real = sum(int(alto_final_img * d['ratio']) for d in datos_imagenes) + (CONFIG['ESPACIADO_X'] * 2)
    pos_x_actual = (CONFIG['ANCHO_LIENZO'] - ancho_total_real) // 2

    autores, lugares = [d['autor'] for d in datos_imagenes], [d['lugar'] for d in datos_imagenes]
    anchos_col = [int(alto_final_img * d['ratio']) + CONFIG['ESPACIADO_X'] for d in datos_imagenes]

    f_nombre = calcular_fuente_uniforme_global(autores, anchos_col, ruta_fuente, CONFIG['TAMANO_BASE_NOMBRE'], draw)
    f_lugar = calcular_fuente_uniforme_global(lugares, anchos_col, ruta_fuente, CONFIG['TAMANO_BASE_LUGAR'], draw)

    max_y_texto = 0
    for d in datos_imagenes:
        img_res = d['img_obj'].resize((int(alto_final_img * d['ratio']), alto_final_img), Image.Resampling.LANCZOS)
        lienzo.paste(img_res, (pos_x_actual, CONFIG['MARGEN_SUPERIOR']))
        
        if aplicar_marco:
            x0, y0 = pos_x_actual, CONFIG['MARGEN_SUPERIOR']
            x1, y1 = x0 + img_res.width - 1, y0 + alto_final_img - 1
            if estilo_marco == "Sólido": draw.rectangle([x0, y0, x1, y1], outline="white", width=1)
            else:
                p, l = (3, 1) if estilo_marco == "Punteado" else (10, 5)
                for x in range(x0, x1 + 1, p):
                    draw.line([(x, y0), (min(x + l - 1, x1), y0)], fill="white", width=1)
                    draw.line([(x, y1), (min(x + l - 1, x1), y1)], fill="white", width=1)
                for y in range(y0, y1 + 1, p):
                    draw.line([(x0, y), (x0, min(y + l - 1, y1))], fill="white", width=1)
                    draw.line([(x1, y), (x1, min(y + l - 1, y1))], fill="white", width=1)

        cx = pos_x_actual + (img_res.width // 2)
        y_n = CONFIG['MARGEN_SUPERIOR'] + alto_final_img + 25 + offset_y_texto
        bn = draw.textbbox((0, 0), d['autor'], font=f_nombre)
        draw.text((cx - (bn[2]-bn[0])/2, y_n), d['autor'], font=f_nombre, fill="white")
        
        y_l = y_n + (bn[3]-bn[1]) + 5 
        bl = draw.textbbox((0, 0), d['lugar'], font=f_lugar)
        draw.text((cx - (bl[2]-bl[0])/2, y_l), d['lugar'], font=f_lugar, fill="white")
        max_y_texto = max(max_y_texto, y_l + (bl[3]-bl[1]))
        pos_x_actual += img_res.width + CONFIG['ESPACIADO_X']

    if logo_file:
        logo = Image.open(logo_file).convert("RGBA")
        alto_l = int(logo.size[1] * (260 / logo.size[0]))
        logo = logo.resize((260, alto_l), Image.Resampling.LANCZOS)
        px_l, py_l = (CONFIG['ANCHO_LIENZO'] - 260) // 2, max(max_y_texto + 40, CONFIG['ALTO_LIENZO'] - alto_l - 30)
        lienzo.paste(logo, (px_l, py_l), logo)

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
    
    col_a, col_b = st.columns(2)
    with col_a:
        off_t = st.slider("Altura de Texto (Offset px)", -50, 50, 0)
        ruido_i = st.slider("Intensidad de Ruido (Grano)", 0, 100, 60)
    with col_b:
        marcar = st.checkbox("Enmarcar fotos (1px)")
        estilo_m = st.selectbox("Tipo de patrón", ["Sólido", "Punteado", "Discontinuo"], disabled=not marcar)
        # Idea 1: Checkbox de Aleatorio
        usar_aleatorio = st.checkbox("Usar paleta de colores aleatoria", value=False, help="Si se desactiva, los colores se extraerán de tus fotos.")

    if l1 and l2 and l3:
        if st.button("Generar Composición", type="primary", width='stretch'):
            with st.spinner("Analizando colores y renderizando..."):
                try:
                    datos = [
                        {'img_obj': Image.open(img1).convert("RGB"), 'autor': os.path.splitext(img1.name)[0], 'lugar': l1},
                        {'img_obj': Image.open(img2).convert("RGB"), 'autor': os.path.splitext(img2.name)[0], 'lugar': l2},
                        {'img_obj': Image.open(img3).convert("RGB"), 'autor': os.path.splitext(img3.name)[0], 'lugar': l3}
                    ]
                    for d in datos: d['ratio'] = d['img_obj'].width / d['img_obj'].height

                    # Selección de paleta según el checkbox
                    if usar_aleatorio:
                        paleta = generar_paleta_analoga()
                    else:
                        paleta = extraer_colores_de_imagenes(datos)

                    final = generar_collage(datos, logo_u, ruta_f, off_t, marcar, estilo_m, paleta, ruido_i)
                    st.image(final, width='stretch')
                    
                    buf = io.BytesIO()
                    final.save(buf, format="JPEG", quality=95)
                    st.download_button("Descargar Resultado", buf.getvalue(), "composicion.jpeg", "image/jpeg", width='stretch')
                except Exception as e: st.error(f"Error: {e}")