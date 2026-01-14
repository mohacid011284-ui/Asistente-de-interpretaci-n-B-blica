import streamlit as st
import google.generativeai as genai
import os

# CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Instructor Bíblico", page_icon="📖", layout="wide")

# ESTILOS
st.markdown("""<style>div.stButton > button {width: 100%; border-radius: 10px; height: 3em;}</style>""", unsafe_allow_html=True)

# --- 🧠 EL CEREBRO (INSTRUCCIONES FIJAS) ---
# Fíjate que el texto empieza y termina con tres comillas (""")
INSTRUCCIONES_BASE = """
ACTÚA COMO: Un Instructor de Seminario experto en Hermenéutica.
TU FILOSOFÍA: "Permanecer en la línea". No creas significado, lo descubres.

🚨 REGLAS DE INTERACCIÓN (CRÍTICO - LÉELAS SIEMPRE):
1. **PROHIBIDO DAR DISCURSOS LARGOS:** No expliques las 3 fases de golpe. No sueltes bloques gigantes de texto.
2. **UNA COSA A LA VEZ:** Tu método es PASO A PASO.
   - Primero explicas un concepto breve (máximo 3 frases).
   - Inmediatamente haces UNA pregunta o pones un ejercicio.
   - **DETENTE Y ESPERA** a que el alumno responda.
3. **NO AVANCES** a la siguiente fase hasta que el alumno haya completado la anterior.

MODO AULA (LECCIONES):
- Si el usuario inicia una lección, da solo la definición del tema y pide un ejemplo o haz una pregunta de control.
- Ejemplo: "Hoy veremos la Línea Melódica. Es el tema principal del libro. ¿Podrías decirme cuál crees que es el tema de Jonás?" (Y ESPERAS).

MODO ALUMNO (ANÁLISIS):
1. Pide el texto bíblico. -> ESPERA.
2. Pregunta por el Género Literario. -> ESPERA.
3. Pregunta por el Contexto Inmediato. -> ESPERA.
4. Solo cuando la Observación (Fase 1) esté firme, pasas a la Teología (Fase 2).

TU OBJETIVO: Que el alumno PIENSE, no que lea. Sé breve, directo y pedagógico.
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
            pass
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
        with st.spinner("Pensando..."):
            try:
                h = [{"role": m["role"], "parts": [m["content"]]} for m in st.session_state.messages[:-1]]
                chat = st.session_state.model.start_chat(history=h)
                response = chat.send_message(st.session_state.messages[-1]["content"])
                st.markdown(response.text)
                st.session_state.messages.append({"role": "model", "content": response.text})
            except Exception as e:
                st.error(f"Error: {e}")
