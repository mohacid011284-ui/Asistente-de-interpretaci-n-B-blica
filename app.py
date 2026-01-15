import streamlit as st
from google import genai
from google.genai import types
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Instructor Bíblico", page_icon="📖", layout="wide")
st.markdown("""<style>div.stButton > button {width: 100%; border-radius: 10px; height: 3em;}</style>""", unsafe_allow_html=True)

# --- API KEY ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except:
    st.error("⚠️ Falta API Key")
    st.stop()

if "client" not in st.session_state:
    st.session_state.client = genai.Client(api_key=api_key)

# --- CEREBRO (PROMPT) ---
INSTRUCCIONES_BASE = """
ROL: Eres un Instructor de Seminario de Hermenéutica Expositiva.
INSTRUCCIÓN SUPREMA: NO INVENTES CONTENIDO. Sigue estrictamente las secciones del archivo cargado.

CUANDO EL USUARIO PRESIONE UN BOTÓN, ACTÚA ASÍ:

🟢 MODO AULA (Botón 'Aula')
1. Busca en el archivo actual la sección que dice "### [CONTENIDO_AULA]".
2. Exponlo tal cual está escrito.
3. Al final, haz ÚNICAMENTE la pregunta que aparece en "### [PREGUNTA_AULA]".

🟡 MODO ALUMNO (Botón 'Alumno' - Socrático)
1. Busca la sección "### [GUIA_SOCRATICA]".
2. Usa esas preguntas específicas para guiar al alumno. No le des la respuesta.

🔴 MODO REVISIÓN (Botón 'Revisión')
1. Busca la sección "### [CRITERIO_EVALUACION]".
2. Usa esos puntos para calificar lo que el alumno escribió.

🔵 MODO MAESTRO (Botón 'Maestro')
1. Modela la respuesta correcta basándote en la teoría.
"""

def get_prompt():
    texto = INSTRUCCIONES_BASE
    texto += "\n\n=== CONTENIDO DE LA LECCIÓN ACTUAL ===\n"
    
    if os.path.exists("knowledge"):
        archivos_ordenados = sorted([f for f in os.listdir("knowledge") if f.endswith((".md", ".txt"))])
        for f in archivos_ordenados:
            try: 
                with open(f"knowledge/{f}","r",encoding="utf-8") as x: 
                    texto += f"\n--- ARCHIVO: {f} ---\n{x.read()}\n"
            except: pass
    return texto

# --- CHAT ---
if "chat" not in st.session_state or st.session_state.chat is None:
    st.session_state.chat = st.session_state.client.chats.create(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(system_instruction=get_prompt(), temperature=0.2)
    )

if "messages" not in st.session_state: st.session_state.messages = []

# --- CALLBACKS ---
def enviar_mensaje(texto):
    st.session_state.messages.append({"role": "user", "content": texto})

def reiniciar():
    st.session_state.chat = None
    st.session_state.messages = []

# --- INTERFAZ ---
st.title("📖 Instructor de Interpretación Bíblica")

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3389/3389081.png", width=100)
    st.title("Panel de Control")
    archivo = st.file_uploader("📂 Subir Tarea", type=["pdf","txt","md"])
    if archivo: st.success("✅ Archivo recibido")
    
    st.markdown("---")
    st.button("🗑️ Reiniciar Chat", type="primary", on_click=reiniciar)

# --- BOTONES ---
c1,c2,c3,c4 = st.columns(4)

with c1: 
    st.button("🎓 Aula", on_click=enviar_mensaje, args=("MODO AULA: Expón la lección actual siguiendo el guion de [CONTENIDO_AULA] y termina con [PREGUNTA_AULA].",))
with c2: 
    st.button("📝 Alumno", on_click=enviar_mensaje, args=("MODO ALUMNO: Inicia el diálogo socrático usando la [GUIA_SOCRATICA].",))
with c3: 
    st.button("🧑‍🏫 Maestro", on_click=enviar_mensaje, args=("MODO MAESTRO: Muestra cómo se hace.",))
with c4: 
    st.button("🔍 Revisión", on_click=enviar_mensaje, args=("MODO REVISIÓN: Evalúa mi respuesta usando [CRITERIO_EVALUACION].",))

# --- MOSTRAR CHAT (CON FILTRO DE INVISIBILIDAD) ---
for m in st.session_state.messages:
    # 🕵️‍♂️ TRUCO DE MAGIA: Si el mensaje empieza con "MODO ", NO lo mostramos en pantalla
    # pero la IA sí lo recuerda en su memoria.
    if m["role"] == "user" and m["content"].startswith("MODO "):
        continue 
    
    r = "assistant" if m["role"]=="model" else "user"
    with st.chat_message(r): st.markdown(m["content"])

# --- INPUT ---
if prompt := st.chat_input("Escribe tu respuesta..."):
    st.session_state.messages.append({"role":"user","content":prompt})
    st.rerun()

# --- RESPUESTA ---
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant"):
        with st.spinner("..."):
            try:
                msg_content = [st.session_state.messages[-1]["content"]]
                if archivo: msg_content.append(types.Part.from_bytes(data=archivo.getvalue(), mime_type=archivo.type))
                res = st.session_state.chat.send_message(msg_content)
                st.markdown(res.text)
                st.session_state.messages.append({"role":"model","content":res.text})
            except Exception as e: st.error(f"Error: {e}")
