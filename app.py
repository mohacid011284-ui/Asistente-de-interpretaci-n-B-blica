import streamlit as st
from google import genai
from google.genai import types
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Instructor Bíblico", page_icon="📖", layout="wide")
st.markdown("""<style>div.stButton > button {width: 100%; border-radius: 10px; height: 3em;}</style>""", unsafe_allow_html=True)

# --- MODELO VIGENTE ---
MODELO_ACTUAL = "gemini-2.5-flash"

# --- API KEY & CLIENTE ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except:
    st.error("⚠️ Falta la API Key en los Secrets.")
    st.stop()

if "client" not in st.session_state:
    st.session_state.client = genai.Client(api_key=api_key)

# --- CEREBRO (PROMPT ESTRICTO: ENSEÑAR -> PREGUNTAR) ---
INSTRUCCIONES_BASE = """
ROL: Eres un Instructor de Seminario de Hermenéutica Expositiva.
FUENTE: Usa EXCLUSIVAMENTE los archivos de la BIBLIOTECA (abajo).

MODO 1: MAESTRO (Botón 'Aula')
🛑 REGLA DE ORO: ¡NO preguntes sin antes enseñar!
TU SECUENCIA OBLIGATORIA DE RESPUESTA ES:
1. 📖 EXPOSICIÓN: Lee el tema correspondiente en el PLAN DE ESTUDIO/MANUAL. Explica el concepto clave en 1 o 2 párrafos claros (cita el manual).
2. ❓ INTERACCIÓN: SOLO DESPUÉS de explicar, haz UNA pregunta para asegurar que el alumno entendió lo que acabas de explicar.
3. ESPERA: No des la siguiente lección hasta que el alumno responda.

MODO 2: AUDITOR (Botón 'Revisión')
- Compara el sermón/texto del alumno contra las REGLAS del Manual.
- Sé estricto. Cita la regla que se rompió.
"""

def get_prompt():
    texto = INSTRUCCIONES_BASE
    texto += "\n\n=== BIBLIOTECA (TUS ARCHIVOS) ===\n"
    
    # Leemos los archivos de la carpeta knowledge
    if os.path.exists("knowledge"):
        found = False
        for f in os.listdir("knowledge"):
            if f.endswith((".md", ".txt")):
                try: 
                    with open(f"knowledge/{f}","r",encoding="utf-8") as x: 
                        contenido = x.read()
                        texto += f"\n--- CONTENIDO DE {f.upper()} ---\n{contenido}\n"
                        found = True
                except: pass
        if not found:
            texto += "\n[ALERTA: No encontré archivos .txt en la carpeta 'knowledge'. Sin ellos usaré conocimiento general.]\n"
    return texto

# --- CONFIGURACIÓN DEL CHAT ---
if "chat" not in st.session_state or st.session_state.chat is None:
    st.session_state.chat = st.session_state.client.chats.create(
        model=MODELO_ACTUAL,
        config=types.GenerateContentConfig(
            system_instruction=get_prompt(),
            temperature=0.3
        )
    )

if "messages" not in st.session_state: st.session_state.messages = []

# --- INTERFAZ ---
st.title("📖 Instructor de Interpretación Bíblica")

with st.sidebar:
    st.title("Panel de Control")
    archivo = st.file_uploader("📂 Subir Archivo", type=["pdf","txt","md"])
    if archivo: st.success("✅ Archivo cargado")
    
    st.markdown("---")
    if st.button("🗑️ Reiniciar Chat", type="primary"):
        st.session_state.chat = None
        st.session_state.messages = []
        st.rerun()

# --- 4 BOTONES DE ACCIÓN ---
c1,c2,c3,c4 = st.columns(4)
def enviar(t): st.session_state.messages.append({"role":"user","content":t})

with c1: 
    if st.button("🎓 Aula"): enviar("Iniciar Modo Aula: Lección 1")
with c2: 
    if st.button("📝 Alumno"): enviar("Quiero analizar un pasaje (Socrático)")
with c3: 
    if st.button("🧑‍🏫 Maestro"): enviar("Modela una interpretación experta")
with c4: 
    if st.button("🔍 Revisión"): enviar("ACTIVA MODO AUDITOR. Revisa mi archivo.")

# --- CHAT LOOP ---
for m in st.session_state.messages:
    r = "assistant" if m["role"]=="model" else "user"
    with st.chat_message(r): st.markdown(m["content"])

# --- LÓGICA DE RESPUESTA ---
if prompt := st.chat_input("Escribe tu pregunta o respuesta..."):
    st.session_state.messages.append({"role":"user","content":prompt})
    st.rerun()

if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant"):
        with st.spinner("Analizando..."):
            try:
                msg_content = [st.session_state.messages[-1]["content"]]
                if archivo:
                    msg_content.append(types.Part.from_bytes(data=archivo.getvalue(), mime_type=archivo.type))
                
                res = st.session_state.chat.send_message(msg_content)
                st.markdown(res.text)
                st.session_state.messages.append({"role":"model","content":res.text})
            except Exception as e:
                st.error(f"Error: {e}")
