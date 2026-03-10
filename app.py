# app.py
import streamlit as st
from streamlit_option_menu import option_menu

# Configuración inicial
st.set_page_config(page_title="Sistema Bot Notas - Colegio", layout="wide")

# Cargar CSS externo
with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# --- SIDEBAR: GESTIÓN DE ROLES ---
with st.sidebar:
    st.header("🤖 Bot de Notas")
    rol = st.radio("Acceso de usuario:", ["Cliente / Profesor", "Panel Administrativo"])
    st.divider()
    st.info("Versión 1.0 - Multi-instancia activa")

# --- VISTA: CLIENTE / PROFESOR ---
if rol == "Cliente / Profesor":
    st.title("📤 Carga de Calificaciones")
    st.subheader("Suba sus archivos para el procesamiento del Bot")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        files = st.file_uploader(
            "Formatos permitidos: Imágenes (Fotos de planillas), PDF o Excel",
            type=['png', 'jpg', 'pdf', 'xlsx'],
            accept_multiple_files=True
        )
    
    with col2:
        st.markdown("### Resumen de carga")
        if files:
            for file in files:
                st.write(f"✅ {file.name}")
        else:
            st.write("Esperando archivos...")

# --- VISTA: ADMINISTRADOR ---
else:
    st.title("⚙️ Panel de Control del Bot")
    
    # Menú de pestañas para los módulos solicitados
    menu = option_menu(
        menu_title=None,
        options=["Iniciar Bot", "Ver Consola", "Excel", "Scrapping", "OCR", "Management"],
        icons=["play-circle", "terminal", "table", "search", "eye", "list-task"],
        menu_icon="cast",
        default_index=0,
        orientation="horizontal",
    )

    # Contenedores para que los otros empleados inserten su código
    if menu == "Iniciar Bot":
        st.subheader("🚀 Lanzamiento de Instancias")
        c1, c2 = st.columns(2)
        with c1:
            bot_type = st.selectbox("Seleccione el Bot de entrega:", ["Bot Primaria", "Bot Secundaria", "Bot Administrativo"])
        with c2:
            st.number_input("Número de instancia", min_value=1, max_value=10)
        
        if st.button("EJECUTAR BOT"):
            st.success(f"Instancia de {bot_type} iniciada correctamente.")

    elif menu == "Ver Consola":
        st.subheader("🖥 Logs en Tiempo Real")
        st.code(">> [INFO] Bot conectado al portal del colegio...\n>> [SUCCESS] Procesando fila 45 de Excel...", language="python")

    elif menu == "Excel":
        st.subheader("📂 Módulo de Reportes Excel")
        st.button("Descargar Plantilla Maestra")

    elif menu == "Scrapping":
        st.subheader("🌐 Extracción de Datos Web")
        st.text_input("URL del Portal Académico")
        st.button("Testear Conexión")

    elif menu == "OCR":
        st.subheader("🔍 Reconocimiento de Planillas Físicas")
        st.slider("Ajuste de sensibilidad de lectura", 0, 100, 75)

    elif menu == "Management":
        st.subheader("📋 Gestión de Pedidos de Entrega")
        st.table({
            "ID Pedido": ["101", "102"],
            "Profesor": ["García", "Rodríguez"],
            "Estado": ["En cola", "Procesando"]
        })