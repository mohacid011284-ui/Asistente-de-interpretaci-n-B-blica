import streamlit as st
import google.generativeai as genai
import os

# CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(
    page_title="Instructor de Interpretación Bíblica",
    page_icon="📖",
    layout="wide"
)

# BARRA LATERAL (MENU)
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3389/3389081.png", width=100)
    st.title("Aula Virtual")
    st.markdown("---")
    
    # ENLACES A CLASSROOM
    st.header("🔗 Enlaces Rápidos")
    # AQUÍ ESTABA EL ERROR: Me aseguré de que esta línea tenga 4 espacios al inicio
    st.link_button("Ir a Google Classroom", "https://classroom.google.com/w/ODM5MzY1NTk0Mzc5/t/all")
    
    st.markdown("---")
    st.header("📂 Recursos")
    st.info("Recuerda descargar las hojas de trabajo desde Classroom antes de empezar.")

# CONFIGURACIÓN DE LA API (SECRETA)
# En Streamlit Cloud configuraremos esto en "Secrets"
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except Exception as e:
    st.error("Falta configurar la API Key en los Secrets de Streamlit.")

# FUNCIÓN PARA CARGAR EL SYSTEM PROMPT
def load_system_prompt():
    try:
        # Busca el archivo en la carpeta prompts
        with open("prompts/system_instruction.md", "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        return "Eres un asistente útil. (Error: No se encontró system_instruction.md)"

# INICIALIZAR EL MODELO
if "model" not in st.session_state:
    system_instruction = load_system_prompt()
    st.session_state.model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=system_instruction
    )

# INTERFAZ PRINCIPAL DE CHAT
st.title("📖 Instructor de Interpretación Bíblica")
st.caption("Filosofía: Permanecer en la línea | Método: Expositivo")

# Historial de Chat
if "messages" not in st.session_state:
    st.session_state.messages = []

# Mostrar mensajes anteriores
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Capturar entrada del usuario
if prompt := st.chat_input("Escribe tu duda o pasaje aquí..."):
    # 1. Mostrar mensaje del usuario
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 2. Generar respuesta
    try:
        chat = st.session_state.model.start_chat(history=[
            {"role": m["role"], "parts": [m["content"]]} for m in st.session_state.messages[:-1]
        ])
        response = chat.send_message(prompt)
        
        # 3. Mostrar respuesta del AI
        with st.chat_message("assistant"):
            st.markdown(response.text)
        st.session_state.messages.append({"role": "model", "content": response.text})
        
    except Exception as e:
        st.error(f"Ocurrió un error: {e}")
