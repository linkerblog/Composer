import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageOps
import random
import os
import io
import math
import colorsys
import base64

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Generador de Composiciones", layout="centered")

# --- INICIALIZACIÓN DE MEMORIA DE SESIÓN ---
if 'img_final' not in st.session_state:
    st.session_state.img_final = None
if 'img_bytes' not in st.session_state:
    st.session_state.img_bytes = None
if 'orden' not in st.session_state:
    st.session_state.orden = [0, 1, 2]
if 'last_files_hash' not in st.session_state:
    st.session_state.last_files_hash = None

# --- FUNCIONES DE NAVEGACIÓN Y ESTADO (CALLBACKS) ---
def mover_izq(v_idx):
    st.session_state.orden[v_idx], st.session_state.orden[v_idx-1] = st.session_state.orden[v_idx-1], st.session_state.orden[v_idx]

def mover_der(v_idx):
    st.session_state.orden[v_idx], st.session_state.orden[v_idx+1] = st.session_state.orden[v_idx+1], st.session_state.orden[v_idx]

def clear_field(key):
    """Limpia el campo de texto y asegura el borrado en el session_state"""
    if key in st.session_state:
        st.session_state[key] = ""

# --- LÓGICA DE PATRÓN DE FONDO (SVG) ---
def obtener_patron_css():
    dir_vector = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vector")
    
    if not os.path.exists(dir_vector):
        try:
            os.makedirs(dir_vector)
        except:
            pass
        return ""
    
    svg_files = [f for f in os.listdir(dir_vector) if f.lower().endswith('.svg')]
    if not svg_files:
        return ""
    
    svg_layers = []
    positions = []
    sizes = []
    
    # Usamos hasta 8 iconos para crear capas superpuestas con separación
    for i, f in enumerate(svg_files[:8]): 
        path = os.path.join(dir_vector, f)
        try:
            with open(path, "r", encoding="utf-8") as svg_file:
                svg_data = svg_file.read()
                svg_encoded = base64.b64encode(svg_data.encode('utf-8')).decode('utf-8')
                svg_layers.append(f"url('data:image/svg+xml;base64,{svg_encoded}')")
                
                # Generamos "aleatoriedad" basada en el índice para que sea consistente entre reruns
                offset_x = (i * 37) % 100
                offset_y = (i * 23) % 100
                scale = 250 + (i * 70) % 300
                
                positions.append(f"{offset_x}% {offset_y}%")
                sizes.append(f"{scale}px {scale}px")
        except:
            continue
    
    if not svg_layers:
        return ""

    # Configuramos el fondo con múltiples capas, posiciones y tamaños
    css_bg = f"""
    background-image: {', '.join(svg_layers)};
    background-position: {', '.join(positions)};
    background-size: {', '.join(sizes)};
    background-repeat: repeat;
    opacity: 0.08;
    filter: brightness(0) invert(1); /* Los hace blancos sutiles */
    """
    return css_bg

# --- INYECCIÓN DE CSS PARA EL BACKGROUND DE LA APP ---
pattern_css = obtener_patron_css()
st.markdown(f"""
    <style>
    .stApp {{
        background: linear-gradient(135deg, #050a18 0%, #0a1128 50%, #0d1b3e 100%) !important;
        color: #FFFFFF;
    }}
    
    .stApp::before {{
        content: "";
        position: fixed;
        top: 0; 
        left: 0; 
        width: 100%; 
        height: 100%;
        {pattern_css}
        pointer-events: none;
        z-index: 0;
    }}

    .stApp > header, .stApp > .main {{
        position: relative;
        z-index: 1;
    }}

    .stTextInput>div>div>input {{
        background-color: rgba(255, 255, 255, 0.07);
        color: white;
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 8px;
    }}
    
    .stButton>button {{
        border-radius: 8px;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIONES GRÁFICAS ---
def generar_paleta_analoga():
    h_base = random.random()
    s, v = random.uniform(0.65, 0.85), random.uniform(0.75, 0.95)
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
        mejor_color, max_score = (0, 0, 0), -1
        for r, g, b in pixeles:
            h, s, v = colorsys.rgb_to_hsv(r/255.0, g/255.0, b/255.0)
            if (s + v) > max_score: max_score, mejor_color = (s + v), (r, g, b)
        r, g, b = mejor_color
        h, s, v = colorsys.rgb_to_hsv(r/255.0, g/255.0, b/255.0)
        r_v, g_v, b_v = colorsys.hsv_to_rgb(h, min(1.0, s * 1.3 + 0.2), min(1.0, v * 1.1 + 0.1))
        colores.append((int(r_v*255), int(g_v*255), int(b_v*255)))
    return colores

def dibujar_degradado_avanzado(lienzo, colores):
    ancho, alto = lienzo.size
    color1, color2, color3 = colores
    escala = 10
    w_p, h_p = ancho // escala, alto // escala
    img_b = Image.new('RGB', (w_p, h_p))
    for y in range(h_p):
        for x in range(w_p):
            nx, ny = x / w_p, y / h_p
            inf1, inf2 = max(0, 1 - math.sqrt(nx**2 + ny**2))**1.6, max(0, 1 - math.sqrt((1-nx)**2 + (1-ny)**2))**1.4
            inf3, inf4 = max(0, 1 - math.sqrt((0.4-nx)**2 + (0.8-ny)**2))**1.8, max(0, 1 - math.sqrt((1-nx)**2 + ny**2))**1.5
            total = inf1 + inf2 + inf3 + inf4 + 0.001
            r = int((color1[0]*(inf1+inf4) + color2[0]*inf2 + color3[0]*inf3) / total)
            g = int((color1[1]*(inf1+inf4) + color2[1]*inf2 + color3[1]*inf3) / total)
            b = int((color1[2]*(inf1+inf4) + color2[2]*inf2 + color3[2]*inf3) / total)
            img_b.putpixel((x, y), (r, g, b))
    lienzo.paste(img_b.resize((ancho, alto), Image.Resampling.LANCZOS))

def calcular_fuente_uniforme_global(textos, anchos_maximos, ruta_fuente, tamano_inicial, draw):
    tam_a = tamano_inicial
    fuente = ImageFont.truetype(ruta_fuente, tam_a)
    while tam_a > 12:
        caben = True
        for t, m_w in zip(textos, anchos_maximos):
            if not t: continue
            bbox = draw.textbbox((0, 0), t, font=fuente)
            if (bbox[2] - bbox[0]) > (m_w - 10): caben = False; break
        if caben: break
        tam_a -= 2
        fuente = ImageFont.truetype(ruta_fuente, tam_a)
    return fuente

def hex_a_rgb(c):
    c = c.lstrip('#')
    return tuple(int(c[i:i+2], 16) for i in (0, 2, 4))

def generar_collage(datos_imagenes, logo_img, ruta_fuente, off_y_t, off_y_f, ex_t, tam_l, marco, estilo, c_marco_hex, g_marco, colores):
    cfg = {'W': 1600, 'H': 1147, 'TOP': 90, 'GAP': 24, 'M_H': 580, 'M_W': 1500}
    lienzo = Image.new('RGB', (cfg['W'], cfg['H']))
    dibujar_degradado_avanzado(lienzo, colores)
    draw = ImageDraw.Draw(lienzo)
    suma_r = sum(d['ratio'] for d in datos_imagenes)
    h_f = int(min(cfg['M_H'], (cfg['M_W'] - (cfg['GAP']*2)) / suma_r))
    anchos_c = []
    for d in datos_imagenes:
        d['w_r'] = int(h_f * d['ratio'])
        d['i_r'] = d['img_obj'].resize((d['w_r'], h_f), Image.Resampling.LANCZOS)
        anchos_c.append(d['w_r'] + cfg['GAP'])
    pos_x = (cfg['W'] - (sum(d['w_r'] for d in datos_imagenes) + cfg['GAP']*2)) // 2
    f_n = calcular_fuente_uniforme_global([d['autor'] for d in datos_imagenes], anchos_c, ruta_fuente, 48 + ex_t, draw)
    f_l = calcular_fuente_uniforme_global([d['lugar'] for d in datos_imagenes], anchos_c, ruta_fuente, 72 + ex_t, draw)
    max_y, c_m_rgb = 0, hex_a_rgb(c_marco_hex)
    pos_y = cfg['TOP'] + off_y_f
    for d in datos_imagenes:
        lienzo.paste(d['i_r'], (pos_x, pos_y))
        if marco:
            x0, y0, x1, y1 = pos_x, pos_y, pos_x + d['w_r'] - 1, pos_y + h_f - 1
            if estilo == "Sólido": draw.rectangle([x0, y0, x1, y1], outline=c_m_rgb, width=g_marco)
            else:
                p, l = (4, 2) if estilo == "Punteado" else (12, 6)
                for x in range(x0, x1 + 1, p):
                    draw.line([(x, y0), (min(x+l-1, x1), y0)], fill=c_m_rgb, width=g_marco)
                    draw.line([(x, y1), (min(x+l-1, x1), y1)], fill=c_m_rgb, width=g_marco)
                for y in range(y0, y1 + 1, p):
                    draw.line([(x0, y), (x0, min(y+l-1, y1))], fill=c_m_rgb, width=g_marco)
                    draw.line([(x1, y), (x1, min(y+l-1, y1))], fill=c_m_rgb, width=g_marco)
        c_x = pos_x + (d['w_r'] // 2)
        y_n = pos_y + h_f + 25 + off_y_t
        bb_n = draw.textbbox((0, 0), d['autor'], font=f_n)
        draw.text((c_x - ((bb_n[2]-bb_n[0])/2), y_n), d['autor'], font=f_n, fill="white")
        y_l = y_n + (bb_n[3]-bb_n[1]) + 5
        if d['lugar']:
            bb_l = draw.textbbox((0, 0), d['lugar'], font=f_l)
            draw.text((c_x - ((bb_l[2]-bb_l[0])/2), y_l), d['lugar'], font=f_l, fill="white")
            max_y = max(max_y, y_l + (bb_l[3]-bb_l[1]))
        else: max_y = max(max_y, y_n + (bb_n[3]-bb_n[1]))
        pos_x += d['w_r'] + cfg['GAP']
    if logo_img:
        l_h = int(float(logo_img.size[1]) * (tam_l / float(logo_img.size[0])))
        l_p = logo_img.resize((tam_l, l_h), Image.Resampling.LANCZOS)
        p_x_l, p_y_l = (cfg['W'] - tam_l) // 2, max(max_y + 40, cfg['H'] - l_h - 30)
        if l_p.mode == 'RGBA': lienzo.paste(l_p, (p_x_l, p_y_l), l_p)
        else: lienzo.paste(l_p, (p_x_l, p_y_l))
    return lienzo

# --- INTERFAZ ---
st.title("Generador de Composiciones")

dir_f = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fuentes")
if not os.path.exists(dir_f): os.makedirs(dir_f)
fs = [f for f in os.listdir(dir_f) if f.lower().endswith(('.ttf', '.otf'))]
r_f = os.path.join(dir_f, st.selectbox("Tipografía Principal", fs)) if fs else None

st.write("### 1. Carga de Fotografías")
c_up1, c_up2, c_up3 = st.columns(3)
with c_up1: img1 = st.file_uploader("Archivo 1", type=['jpg', 'jpeg', 'png'])
with c_up2: img2 = st.file_uploader("Archivo 2", type=['jpg', 'jpeg', 'png'])
with c_up3: img3 = st.file_uploader("Archivo 3", type=['jpg', 'jpeg', 'png'])

if img1 and img2 and img3:
    st.divider()
    st.write("### 2. Edición de Datos y Orden")
    as_ = [img1, img2, img3]
    h_c = "".join([f.name for f in as_])
    if st.session_state.last_files_hash != h_c:
        for i, f in enumerate(as_):
            st.session_state[f"input_nombre_{i}"] = os.path.splitext(f.name)[0]
            st.session_state[f"input_lugar_{i}"] = ""
        st.session_state.last_files_hash = h_c
    
    ms = []
    for f in as_:
        f.seek(0)
        ms.append(ImageOps.fit(ImageOps.exif_transpose(Image.open(f).convert("RGB")), (300, 300), Image.Resampling.LANCZOS))
    
    cps = st.columns(3)
    for v_i, r_i in enumerate(st.session_state.orden):
        with cps[v_i]:
            st.image(ms[r_i], use_container_width=True)
            st.markdown("**Nombre / Archivo**")
            cn, ct = st.columns([0.78, 0.22], vertical_alignment="bottom")
            with cn: st.text_input("N", key=f"input_nombre_{r_i}", label_visibility="collapsed")
            with ct: st.button("🗑️", key=f"clear_name_{r_i}", on_click=clear_field, args=(f"input_nombre_{r_i}",))
            st.markdown("**Info Extra**")
            ci, cti = st.columns([0.78, 0.22], vertical_alignment="bottom")
            with ci: st.text_input("I", key=f"input_lugar_{r_i}", label_visibility="collapsed")
            with cti: st.button("🗑️", key=f"clear_info_{r_i}", on_click=clear_field, args=(f"input_lugar_{r_i}",))
            cl, cr = st.columns(2)
            with cl: 
                if v_i > 0: st.button("◀", key=f"ml_{r_i}", on_click=mover_izq, args=(v_i,), use_container_width=True)
            with cr:
                if v_i < 2: st.button("▶", key=f"mr_{r_i}", on_click=mover_der, args=(v_i,), use_container_width=True)

    st.divider()
    st.write("### 3. Ajustes de Composición")
    l_up = st.file_uploader("Logotipo (Opcional)", type=['jpg', 'jpeg', 'png'])
    c1, c2, c3 = st.columns(3)
    with c1:
        o_t = st.slider("Posición Y textos (px)", -100, 100, 0, 5)
        o_f = st.slider("Posición Y fotos (px)", -200, 200, 0, 2)
        e_t = st.slider("Aumento fuente (px)", 0, 40, 0, 2)
    with c2:
        t_l = st.slider("Tamaño Logo (px)", 50, 800, 260, 10)
        u_a = st.checkbox("Fondo de composición aleatorio")
        a_m = st.checkbox("Aplicar marco a fotos")
    with c3:
        e_m = st.selectbox("Patrón marco", ["Sólido", "Punteado", "Discontinuo"], disabled=not a_m)
        g_m = st.slider("Grosor marco (px)", 1, 15, 1, disabled=not a_m)
        c_m = st.color_picker("Color marco", "#FFFFFF", disabled=not a_m)

    if st.button("Generar Composición", type="primary", use_container_width=True):
        with st.spinner("Procesando matriz gráfica..."):
            try:
                db = []
                for r_i in range(3):
                    as_[r_i].seek(0)
                    db.append({
                        'img_obj': ImageOps.exif_transpose(Image.open(as_[r_i]).convert("RGB")), 
                        'autor': st.session_state[f"input_nombre_{r_i}"], 
                        'lugar': st.session_state[f"input_lugar_{r_i}"], 
                        'orden': st.session_state.orden.index(r_i)
                    })
                dis = sorted(db, key=lambda x: x['orden'])
                for d in dis: d['ratio'] = d['img_obj'].width / d['img_obj'].height
                
                final = generar_collage(
                    dis, 
                    Image.open(l_up).convert("RGBA") if l_up else None, 
                    r_f, o_t, o_f, e_t, t_l, a_m, e_m, c_m, g_m, 
                    generar_paleta_analoga() if u_a else extraer_colores_vibrantes(dis)
                )
                
                st.session_state.img_final = final
                buf = io.BytesIO()
                final.save(buf, format="JPEG", quality=95)
                st.session_state.img_bytes = buf.getvalue()
            except Exception as e:
                st.error(f"Error: {e}")
                
    if st.session_state.img_final:
        st.image(st.session_state.img_final, use_container_width=True)
        st.download_button("Descargar Composición", st.session_state.img_bytes, "composicion.jpeg", "image/jpeg", use_container_width=True)
else:
    st.info("Sube las tres fotos en la cabecera para comenzar a diseñar.")