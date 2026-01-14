import streamlit as st
import google.generativeai as genai
import os

# CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(
    page_title="Instructor de Interpretación Bíblica",
    page_icon="📖",
    layout="wide"
)

# --- ESTILOS CSS PERSONALIZADOS (Opcional, para botones más bonitos) ---
st.markdown("""
<style>
    div.stButton > button {
        width: 100%;
        border-radius: 10px;
        height: 3em;
    }
</style>
""", unsafe_allow_html=True)

# --- BARRA LATERAL (MENU) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3389/3389081.png", width=100)
    st.title("Aula Virtual")
    st.markdown("---")
    
    # ENLACES A CLASSROOM
    st.header("🔗 Enlaces Rápidos")
    st.link_button("Ir a Google Classroom", "https://classroom.google.com/w/ODM5MzY1NTk0Mzc5/t/all")
    
    st.markdown("---")
    st.header("📂 Recursos")
    st.info("Recuerda descargar las hojas de trabajo desde Classroom antes de empezar.")
    
    # Botón para limpiar historial
    if st.button("🗑️ Borrar Chat", type="primary"):
        st.session_state.messages = []
        st.rerun()

# --- CONFIGURACIÓN DE LA API ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except Exception as e:
    st.error("Falta configurar la API Key en los Secrets de Streamlit.")

# --- FUNCIÓN PARA CARGAR EL SYSTEM PROMPT ---
def load_system_prompt():
    try:
        with open("prompts/system_instruction.md", "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        return "Eres un asistente útil. (Error: No se encontró system_instruction.md)"

# --- INICIALIZAR EL MODELO ---
if "model" not in st.session_state:
    system_instruction = load_system_prompt()
    st.session_state.model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=system_instruction
    )

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- INTERFAZ PRINCIPAL ---
st.title("📖 Instructor de Interpretación Bíblica")
st.caption("Filosofía: Permanecer en la línea | Método: Expositivo")

# --- BOTONES DE ACCIÓN RÁPIDA ---
# Solo los mostramos si el chat está vacío o para facilitar navegación
col1, col2, col3, col4 = st.columns(4)

# Definimos las acciones de los botones
def click_boton(texto_mensaje):
    st.session_state.messages.append({"role": "user", "content": texto_mensaje})

with col1:
    if st.button("🎓 Aula"):
        click_boton("Iniciar Modo Aula: Lección 1")
with col2:
    if st.button("📝 Alumno"):
        click_boton("Quiero analizar un pasaje (Modo Alumno)")
with col3:
    if st.button("🧑‍🏫 Maestro"):
        click_boton("Modela una interpretación completa (Modo Maestro)")
with col4:
    if st.button("🔍 Revisión"):
        click_boton("Aquí está mi trabajo, por favor revísalo bajo tus criterios de evaluación.")

# --- MOSTRAR HISTORIAL DE CHAT ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- LÓGICA DE GENERACIÓN DE RESPUESTA ---
# Se activa si el usuario escribe algo O si presionó un botón (que agregó un mensaje al historial)
input_usuario = st.chat_input("Escribe tu duda o pasaje aquí...")

if input_usuario:
    st.session_state.messages.append({"role": "user", "content": input_usuario})
    st.rerun() # Recargamos para que procese el mensaje nuevo

# Si el último mensaje es del usuario, generamos respuesta del AI
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant"):
        with st.spinner("Analizando el texto..."):
            try:
                # Crear chat con historial previo (excluyendo el último mensaje que acabamos de poner)
                history_for_gemini = [
                    {"role": m["role"], "parts": [m["content"]]} 
                    for m in st.session_state.messages[:-1]
                ]
                
                chat = st.session_state.model.start_chat(history=history_for_gemini)
                response = chat.send_message(st.session_state.messages[-1]["content"])
                
                st.markdown(response.text)
                st.session_state.messages.append({"role": "model", "content": response.text})
            except Exception as e:
                st.error(f"Error: {e}")
