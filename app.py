import streamlit as st
import google.generativeai as genai
import os

# CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Instructor Bíblico", page_icon="📖", layout="wide")

# ESTILOS
st.markdown("""<style>div.stButton > button {width: 100%; border-radius: 10px; height: 3em;}</style>""", unsafe_allow_html=True)

# --- 🧠 EL CEREBRO (INSTRUCCIONES FIJAS) ---
# Las ponemos aquí directo para que nunca fallen
INSTRUCCIONES_BASE = """
ACTÚA COMO: Un Instructor de Seminario experto en Hermenéutica.
TU FILOSOFÍA: "Permanecer en la línea". No creas significado, lo descubres.
TU LEMA: "Ni más (legalismo), ni menos (liberalismo)".

TU OBJETIVO: Guiar al alumno por las 3 Fases del Método Expositivo:
1. EXÉGESIS (Observación): ¿Qué dice el texto? (Contexto, Gramática, Género).
2. TEOLOGÍA (Reflexión): ¿Cómo conecta con Cristo? (Sin alegorizar, usando Tipología, Promesa, etc).
3. APLICACIÓN (Persuasión): ¿Qué demanda hoy? (Para el creyente y no creyente).

REGLAS DE ORO:
- Si el usuario pone un texto, NO des la respuesta final. Haz preguntas socráticas para que él la descubra.
- Si el usuario pide revisión, sé amable pero riguroso basándote en el Manual.
- Si faltan archivos de conocimiento, úsalo lo que sepas de teología reformada clásica.
"""

# --- FUNCIÓN PARA CARGAR EL MANUAL DESDE GITHUB ---
def get_system_prompt():
    prompt_completo = INSTRUCCIONES_BASE
    
    # Intentamos leer el manual que subiste a la carpeta knowledge
    ruta_manual = "knowledge/manual_completo_v2.md"
    
    if os.path.exists(ruta_manual):
        try:
            with open(ruta_manual, "r", encoding="utf-8") as f:
                manual_texto = f.read()
                prompt_completo += "\n\n=== MANUAL DE REFERENCIA ===\n" + manual_texto
        except:
            # Si falla al leer, seguimos con la instrucción base
            pass
    else:
        # Si no encuentra el archivo, agrega una nota para el modelo
        prompt_completo += "\n\n(NOTA: No tengo acceso al manual completo en este momento. Usaré mi conocimiento general de hermenéutica expositiva)."
    
    return prompt_completo

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3389/3389081.png", width=100)
    st.title("Aula Virtual")
    st.markdown("---")
    st.link_button("Ir a Google Classroom", "https://classroom.google.com/w/ODM5MzY1NTk0Mzc5/t/all")
    st.markdown("---")
    if st.button("🗑️ Borrar Chat", type="primary"):
        st.session_state.messages = []
        st.rerun()

# --- API KEY ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except:
    st.error("Falta la API Key en Secrets.")

# --- INICIALIZAR MODELO ---
if "model" not in st.session_state:
    # Aquí construimos el cerebro sumando Instrucciones + Manual
    prompt_final = get_system_prompt()
    
    st.session_state.model = genai.GenerativeModel(
        model_name="gemini-flash-latest", 
        system_instruction=prompt_final
    )

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- INTERFAZ ---
st.title("📖 Instructor de Interpretación Bíblica")
st.caption("Filosofía: Permanecer en la línea")

# Botones
c1, c2, c3, c4 = st.columns(4)
def click(txt): st.session_state.messages.append({"role": "user", "content": txt})
with c1: 
    if st.button("🎓 Aula"): click("Iniciar Modo Aula: Lección 1")
with c2: 
    if st.button("📝 Alumno"): click("Quiero analizar un pasaje")
with c3: 
    if st.button("🧑‍🏫 Maestro"): click("Modela una interpretación")
with c4: 
    if st.button("🔍 Revisión"): click("Revisa mi trabajo según el manual")

# Chat
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if prompt := st.chat_input("Escribe aquí..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()

if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant"):
        with st.spinner("Consultando manual..."):
            try:
                # Historial
                h = [{"role": m["role"], "parts": [m["content"]]} for m in st.session_state.messages[:-1]]
                chat = st.session_state.model.start_chat(history=h)
                response = chat.send_message(st.session_state.messages[-1]["content"])
                st.markdown(response.text)
                st.session_state.messages.append({"role": "model", "content": response.text})
            except Exception as e:
                st.error(f"Error: {e}")
