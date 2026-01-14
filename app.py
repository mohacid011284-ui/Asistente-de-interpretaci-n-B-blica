import streamlit as st
import google.generativeai as genai
import os

# CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Instructor Bíblico", page_icon="📖", layout="wide")

# ESTILOS
st.markdown("""<style>div.stButton > button {width: 100%; border-radius: 10px; height: 3em;}</style>""", unsafe_allow_html=True)

# --- 🧠 EL CEREBRO (INSTRUCCIONES FIJAS) ---
INSTRUCCIONES_BASE = """
ACTÚA COMO: Un Instructor de Seminario experto en Hermenéutica Expositiva.
TU FILOSOFÍA: "Permanecer en la línea".

🚨 PROTOCOLO DE COMPORTAMIENTO:

MODO 1: MAESTRO SOCRÁTICO (Botones Aula/Alumno)
- Si el usuario quiere aprender, sé breve, haz preguntas y espera.

MODO 2: AUDITOR ESTRICTO (Botón Revisión / Archivo subido)
- TU TONO: Crítico fuerte, directo, sin "suavizar" los errores, pero asertivo.
- TU MISIÓN: Detectar desviaciones de la "Línea Melódica" y del Texto Bíblico.

CUANDO REVISES UN DOCUMENTO, SIGUE ESTA ESTRUCTURA PARA CADA PUNTO DEBIL:
1. ❌ EL ERROR: Cita la frase exacta o la idea donde falló.
2. 📜 LA REGLA ROTA: Menciona qué principio hermenéutico se violó (Busca en tu CONOCIMIENTO ADQUIRIDO).
3. 🧠 EL PORQUÉ: Explica por qué es un error teológico o técnico.
4. 💡 LA MEJORA: Diles exactamente qué debieron haber hecho.

AL FINAL DEL REPORTE, DEBES EVALUAR USANDO LA HOJA DE EVALUACIÓN OFICIAL (SI LA TIENES EN TU CONOCIMIENTO) Y LUEGO HACER LA OFERTA FINAL:

⚠️ CIERRE OBLIGATORIO:
Al terminar tu crítica, SIEMPRE pregunta:
"¿Te gustaría que genere una re-modificación de tu sermón/trabajo aplicando estas correcciones para que veas cómo quedaría?"
"""

# --- FUNCIÓN PARA LEER TODA LA BIBLIOTECA DE CONOCIMIENTO ---
def get_system_prompt():
    prompt_completo = INSTRUCCIONES_BASE
    carpeta_knowledge = "knowledge"
    
    # Verificamos si la carpeta existe
    if os.path.exists(carpeta_knowledge):
        prompt_completo += "\n\n=== BIBLIOTECA DE CONOCIMIENTOS (SIEMPRE ACTIVA) ===\n"
        
        # Leemos CADA archivo que termine en .md o .txt dentro de la carpeta
        archivos_encontrados = False
        for archivo_nombre in os.listdir(carpeta_knowledge):
            if archivo_nombre.endswith((".md", ".txt")):
                ruta_completa = os.path.join(carpeta_knowledge, archivo_nombre)
                try:
                    with open(ruta_completa, "r", encoding="utf-8") as f:
                        contenido = f.read()
                        # Añadimos el contenido con un título para que la IA sepa de qué tema trata
                        prompt_completo += f"\n--- TEMA: {archivo_nombre.upper()} ---\n{contenido}\n"
                        archivos_encontrados = True
                except Exception as e:
                    print(f"Error leyendo {archivo_nombre}: {e}")
        
        if not archivos_encontrados:
            prompt_completo += "\n(No se encontraron archivos de texto en la carpeta knowledge)."
            
    return prompt_completo

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3389/3389081.png", width=100)
    st.title("Aula Virtual")
    
    st.markdown("### 📂 Buzón de Revisión")
    st.info("Sube tu sermón/tarea para una auditoría estricta.")
    archivo_subido = st.file_uploader("Sube PDF, TXT o MD", type=["pdf", "txt", "md"])
    
    if archivo_subido:
        st.success("✅ Archivo cargado.")
    
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
    # Cargamos TODA la biblioteca al iniciar
    prompt_final = get_system_prompt()
    st.session_state.model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
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
    if st.button("📝 Alumno"): click("Quiero analizar un pasaje (Modo Socrático)")
with c3: 
    if st.button("🧑‍🏫 Maestro"): click("Modela una interpretación")
with c4: 
    if st.button("🔍 Revisión"): click("He subido mi documento. ACTIVA EL MODO AUDITOR ESTRICTO. Sé duro, señala errores, reglas rotas y propón mejoras. Al final pregúntame si quiero la re-modificación.")

# Chat
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- PROCESAMIENTO ---
if prompt := st.chat_input("Escribe aquí..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()

if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant"):
        with st.spinner("Consultando biblioteca teológica..."):
            try:
                history = [{"role": m["role"], "parts": [m["content"]]} for m in st.session_state.messages[:-1]]
                chat = st.session_state.model.start_chat(history=history)
                
                user_msg = st.session_state.messages[-1]["content"]
                
                if archivo_subido:
                    datos = {"mime_type": archivo_subido.type, "data": archivo_subido.getvalue()}
                    response = chat.send_message([user_msg, datos])
                else:
                    response = chat.send_message(user_msg)
                
                st.markdown(response.text)
                st.session_state.messages.append({"role": "model", "content": response.text})
            except Exception as e:
                st.error(f"Error: {e}")
