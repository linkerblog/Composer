import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageOps
import random
import os
import io
import math
import colorsys

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Generador de Composiciones", layout="centered")

# --- INICIALIZACIÓN DE MEMORIA DE SESIÓN ---
if 'img_final' not in st.session_state:
    st.session_state.img_final = None
if 'img_bytes' not in st.session_state:
    st.session_state.img_bytes = None
if 'orden' not in st.session_state:
    st.session_state.orden = [0, 1, 2]
if 'nombres' not in st.session_state:
    st.session_state.nombres = ["", "", ""]
if 'lugares' not in st.session_state:
    st.session_state.lugares = ["", "", ""]
if 'last_files_hash' not in st.session_state:
    st.session_state.last_files_hash = None

# --- FUNCIONES DE NAVEGACIÓN (CALLBACKS) ---
def mover_izq(v_idx):
    st.session_state.orden[v_idx], st.session_state.orden[v_idx-1] = st.session_state.orden[v_idx-1], st.session_state.orden[v_idx]

def mover_der(v_idx):
    st.session_state.orden[v_idx], st.session_state.orden[v_idx+1] = st.session_state.orden[v_idx+1], st.session_state.orden[v_idx]

# --- FUNCIONES GRÁFICAS ---
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

def extraer_colores_vibrantes(datos_imagenes):
    colores = []
    for d in datos_imagenes:
        img_peq = d['img_obj'].resize((4, 4), Image.Resampling.LANCZOS)
        pixeles = [img_peq.getpixel((x, y)) for x in range(4) for y in range(4)]
        
        mejor_color = (0, 0, 0)
        max_score = -1
        for r, g, b in pixeles:
            h, s, v = colorsys.rgb_to_hsv(r/255.0, g/255.0, b/255.0)
            score = s + v 
            if score > max_score:
                max_score = score
                mejor_color = (r, g, b)
                
        r, g, b = mejor_color
        h, s, v = colorsys.rgb_to_hsv(r/255.0, g/255.0, b/255.0)
        s = min(1.0, s * 1.3 + 0.2) 
        v = min(1.0, v * 1.1 + 0.1) 
        r_v, g_v, b_v = colorsys.hsv_to_rgb(h, s, v)
        colores.append((int(r_v*255), int(g_v*255), int(b_v*255)))
        
    return colores

def dibujar_degradado_avanzado(lienzo, colores):
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
    lienzo.paste(degradado_suave)

def calcular_fuente_uniforme_global(textos, anchos_maximos, ruta_fuente, tamano_inicial, draw):
    tamano_actual = tamano_inicial
    fuente = ImageFont.truetype(ruta_fuente, tamano_actual)
    while tamano_actual > 12:
        todos_caben = True
        for texto, max_ancho in zip(textos, anchos_maximos):
            if not texto: continue 
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

def generar_collage(datos_imagenes, logo_img, ruta_fuente, offset_y_texto, extra_tamano_texto, aplicar_marco, estilo_marco, color_marco_hex, grosor_marco, colores):
    CONFIG = {
        'ANCHO_LIENZO': 1600, 'ALTO_LIENZO': 1147, 'MARGEN_SUPERIOR': 90,  
        'ESPACIADO_X': 24, 'MAX_ALTO_IMG': 580, 'MAX_ANCHO_TOTAL': 1500,
        'TAMANO_BASE_NOMBRE': 48, 'TAMANO_BASE_LUGAR': 72
    }

    lienzo = Image.new('RGB', (CONFIG['ANCHO_LIENZO'], CONFIG['ALTO_LIENZO']))
    dibujar_degradado_avanzado(lienzo, colores)
    draw = ImageDraw.Draw(lienzo)

    suma_ratios = sum(d['ratio'] for d in datos_imagenes)
    espacio_disponible_w = CONFIG['MAX_ANCHO_TOTAL'] - (CONFIG['ESPACIADO_X'] * 2)
    alto_final_img = int(min(CONFIG['MAX_ALTO_IMG'], espacio_disponible_w / suma_ratios))

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

    fuente_n = calcular_fuente_uniforme_global(autores, anchos_permitidos_por_columna, ruta_fuente, CONFIG['TAMANO_BASE_NOMBRE'] + extra_tamano_texto, draw)
    fuente_l = calcular_fuente_uniforme_global(lugares, anchos_permitidos_por_columna, ruta_fuente, CONFIG['TAMANO_BASE_LUGAR'] + extra_tamano_texto, draw)

    max_y_texto_detectado = 0
    color_marco_rgb = hex_a_rgb(color_marco_hex)

    for d in datos_imagenes:
        lienzo.paste(d['img_redimensionada'], (pos_x_actual, CONFIG['MARGEN_SUPERIOR']))
        
        if aplicar_marco:
            x0, y0 = pos_x_actual, CONFIG['MARGEN_SUPERIOR']
            x1, y1 = pos_x_actual + d['nuevo_ancho'] - 1, CONFIG['MARGEN_SUPERIOR'] + alto_final_img - 1
            if estilo_marco == "Sólido":
                draw.rectangle([x0, y0, x1, y1], outline=color_marco_rgb, width=grosor_marco)
            else:
                paso, largo_linea = (4, 2) if estilo_marco == "Punteado" else (12, 6)
                for x in range(x0, x1 + 1, paso):
                    draw.line([(x, y0), (min(x + largo_linea - 1, x1), y0)], fill=color_marco_rgb, width=grosor_marco)
                    draw.line([(x, y1), (min(x + largo_linea - 1, x1), y1)], fill=color_marco_rgb, width=grosor_marco)
                for y in range(y0, y1 + 1, paso):
                    draw.line([(x0, y), (x0, min(y + largo_linea - 1, y1))], fill=color_marco_rgb, width=grosor_marco)
                    draw.line([(x1, y), (x1, min(y + largo_linea - 1, y1))], fill=color_marco_rgb, width=grosor_marco)

        centro_img_x = pos_x_actual + (d['nuevo_ancho'] // 2)

        y_texto_nombre = CONFIG['MARGEN_SUPERIOR'] + alto_final_img + 25 + offset_y_texto
        bbox_nombre = draw.textbbox((0, 0), d['autor'], font=fuente_n)
        draw.text((centro_img_x - ((bbox_nombre[2]-bbox_nombre[0]) / 2), y_texto_nombre), d['autor'], font=fuente_n, fill="white")
        alto_nombre = bbox_nombre[3] - bbox_nombre[1]
        
        y_texto_lugar = y_texto_nombre + alto_nombre + 5 
        if d['lugar']:
            bbox_lugar = draw.textbbox((0, 0), d['lugar'], font=fuente_l)
            draw.text((centro_img_x - ((bbox_lugar[2]-bbox_lugar[0]) / 2), y_texto_lugar), d['lugar'], font=fuente_l, fill="white")
            max_y_texto_detectado = max(max_y_texto_detectado, y_texto_lugar + (bbox_lugar[3]-bbox_lugar[1]))
        else:
            max_y_texto_detectado = max(max_y_texto_detectado, y_texto_nombre + alto_nombre)

        pos_x_actual += d['nuevo_ancho'] + CONFIG['ESPACIADO_X']

    if logo_img is not None:
        ancho_logo = 260 
        alto_logo = int(float(logo_img.size[1]) * (ancho_logo / float(logo_img.size[0])))
        logo_procesado = logo_img.resize((ancho_logo, alto_logo), Image.Resampling.LANCZOS)
        pos_x_logo = (CONFIG['ANCHO_LIENZO'] - ancho_logo) // 2
        pos_y_logo = max(max_y_texto_detectado + 40, CONFIG['ALTO_LIENZO'] - alto_logo - 30)
        
        if logo_procesado.mode == 'RGBA':
            lienzo.paste(logo_procesado, (pos_x_logo, pos_y_logo), logo_procesado)
        else:
            lienzo.paste(logo_procesado, (pos_x_logo, pos_y_logo))

    return lienzo

# --- INTERFAZ DE USUARIO STREAMLIT ---
st.title("Generador de Composiciones")

dir_fuentes = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fuentes")
if not os.path.exists(dir_fuentes): os.makedirs(dir_fuentes)
fuentes_disp = [f for f in os.listdir(dir_fuentes) if f.lower().endswith(('.ttf', '.otf'))]
ruta_fuente = None

if not fuentes_disp:
    st.warning("Inserta archivos tipográficos (.ttf o .otf) en la carpeta 'fuentes'.")
else:
    ruta_fuente = os.path.join(dir_fuentes, st.selectbox("Selección de Tipografía", fuentes_disp))

st.write("### 1. Carga de Fotografías")
col_up1, col_up2, col_up3 = st.columns(3)
with col_up1: img1_file = st.file_uploader("Archivo 1", type=['jpg', 'jpeg', 'png'])
with col_up2: img2_file = st.file_uploader("Archivo 2", type=['jpg', 'jpeg', 'png'])
with col_up3: img3_file = st.file_uploader("Archivo 3", type=['jpg', 'jpeg', 'png'])

if img1_file and img2_file and img3_file:
    st.divider()
    st.write("### 2. Orden y Ubicaciones")
    archivos = [img1_file, img2_file, img3_file]
    
    # Lógica de detección de nuevos archivos para inicializar estados
    current_files_hash = "".join([f.name for f in archivos])
    if st.session_state.last_files_hash != current_files_hash:
        st.session_state.nombres = [os.path.splitext(f.name)[0] for f in archivos]
        st.session_state.lugares = ["", "", ""]
        st.session_state.last_files_hash = current_files_hash
    
    miniaturas = []
    for f in archivos:
        f.seek(0)
        img_raw = ImageOps.exif_transpose(Image.open(f).convert("RGB"))
        miniaturas.append(ImageOps.fit(img_raw, (300, 300), Image.Resampling.LANCZOS))
    
    cols_preview = st.columns(3)
    
    for visual_idx, real_idx in enumerate(st.session_state.orden):
        with cols_preview[visual_idx]:
            st.image(miniaturas[real_idx], use_container_width=True)
            
            # --- INPUT NOMBRE (ARCHIVO) ---
            st.markdown("**Nombre / Archivo**")
            c_name, c_trash_name = st.columns([0.78, 0.22], vertical_alignment="bottom")
            with c_name:
                st.session_state.nombres[real_idx] = st.text_input(
                    "Nombre", 
                    value=st.session_state.nombres[real_idx], 
                    key=f"input_nombre_{real_idx}",
                    label_visibility="collapsed"
                ).strip()
            with c_trash_name:
                if st.button("🗑️", key=f"clear_name_{real_idx}", help="Borrar nombre"):
                    st.session_state.nombres[real_idx] = ""
                    st.rerun()

            # --- INPUT INFO EXTRA ---
            st.markdown("**Info Extra**")
            c_info, c_trash_info = st.columns([0.78, 0.22], vertical_alignment="bottom")
            with c_info:
                st.session_state.lugares[real_idx] = st.text_input(
                    "Info Extra", 
                    value=st.session_state.lugares[real_idx], 
                    key=f"input_lugar_{real_idx}",
                    label_visibility="collapsed"
                ).strip().upper()
            with c_trash_info:
                if st.button("🗑️", key=f"clear_info_{real_idx}", help="Vaciar campo"):
                    st.session_state.lugares[real_idx] = ""
                    st.rerun()
            
            # Controles de movimiento
            st.write("")
            c_izq, c_der = st.columns(2)
            with c_izq:
                if visual_idx > 0:
                    st.button("◀ Mover", key=f"btn_izq_{real_idx}", on_click=mover_izq, args=(visual_idx,), use_container_width=True)
            with c_der:
                if visual_idx < 2:
                    st.button("Mover ▶", key=f"btn_der_{real_idx}", on_click=mover_der, args=(visual_idx,), use_container_width=True)

    st.divider()
    st.write("### 3. Opciones Adicionales")
    logo_upload = st.file_uploader("Logotipo (Opcional)", type=['jpg', 'jpeg', 'png'])
    
    c_opc1, c_opc2, c_opc3 = st.columns(3)
    with c_opc1:
        offset_texto = st.slider("Ajuste de posición Y textos (px)", -50, 50, 0, step=5)
        extra_tamano_texto = st.slider("Aumento tamaño fuente (px)", 0, 40, 0, step=2) 
        usar_aleatorio = st.checkbox("Usar paleta aleatoria", False)
    with c_opc2:
        aplicar_marco = st.checkbox("Aplicar marco a fotos")
        estilo_marco = st.selectbox("Patrón", ["Sólido", "Punteado", "Discontinuo"], disabled=not aplicar_marco)
        grosor_marco = st.slider("Grosor (px)", 1, 5, 1, disabled=not aplicar_marco)
    with c_opc3:
        color_marco = st.color_picker("Color", "#FFFFFF", disabled=not aplicar_marco)

    if st.button("Generar Composición", type="primary", use_container_width=True):
        with st.spinner("Procesando matriz gráfica..."):
            try:
                datos_brutos = []
                for r_idx in range(3):
                    archivos[r_idx].seek(0)
                    img_full = ImageOps.exif_transpose(Image.open(archivos[r_idx]).convert("RGB"))
                    pos_visual = st.session_state.orden.index(r_idx)
                    datos_brutos.append({
                        'img_obj': img_full, 
                        'autor': st.session_state.nombres[r_idx], # Ahora usa el estado editable
                        'lugar': st.session_state.lugares[r_idx], 
                        'orden': pos_visual
                    })
                
                datos_imagenes = sorted(datos_brutos, key=lambda x: x['orden'])
                for d in datos_imagenes: d['ratio'] = d['img_obj'].width / d['img_obj'].height

                paleta = generar_paleta_analoga() if usar_aleatorio else extraer_colores_vibrantes(datos_imagenes)
                
                logo_img = None
                if logo_upload:
                    logo_upload.seek(0)
                    logo_img = Image.open(logo_upload).convert("RGBA")

                final = generar_collage(
                    datos_imagenes, logo_img, ruta_fuente, offset_texto, extra_tamano_texto,
                    aplicar_marco, estilo_marco, color_marco, grosor_marco, paleta
                )

                st.session_state.img_final = final
                buf = io.BytesIO()
                final.save(buf, format="JPEG", quality=95)
                st.session_state.img_bytes = buf.getvalue()

            except Exception as e:
                st.error(f"Error crítico en renderizado: {e}")
    
    if st.session_state.img_final:
        st.image(st.session_state.img_final, use_container_width=True)
        st.download_button("Descargar Composición", st.session_state.img_bytes, "composicion.jpeg", "image/jpeg", use_container_width=True)
else:
    st.info("Esperando los tres archivos en la cabecera...")