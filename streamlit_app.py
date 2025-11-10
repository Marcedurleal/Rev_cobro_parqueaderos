import streamlit as st
import pandas as pd
import yaml
import os

# ==============================
# 🔐 Cargar credenciales
# ==============================
def load_config():
    with open("config.yaml", "r") as file:
        return yaml.safe_load(file)["login"]

# ==============================
# 📋 Cargar conjuntos autorizados
# ==============================
def load_conjuntos_autorizados():
    if not os.path.exists("conjuntos_autorizados.txt"):
        return []
    with open("conjuntos_autorizados.txt", "r") as file:
        return [line.strip().upper() for line in file if line.strip()]

# ==============================
# 🔎 Validar hojas autorizadas
# ==============================
def validar_hojas(excel_path, conjuntos_autorizados):
    try:
        xls = pd.ExcelFile(excel_path)
        hojas_en_archivo = [h.upper() for h in xls.sheet_names]

        hojas_autorizadas = [h for h in hojas_en_archivo if h in conjuntos_autorizados]
        hojas_no_autorizadas = [h for h in hojas_en_archivo if h not in conjuntos_autorizados]

        return hojas_autorizadas, hojas_no_autorizadas
    except Exception as e:
        st.error(f"Error al leer el archivo Excel: {e}")
        return [], []

# ==============================
# 🧮 Procesar hojas autorizadas
# ==============================
def procesar_hojas(excel_path, hojas_autorizadas):
    for hoja in hojas_autorizadas:
        st.info(f"📄 Procesando hoja: {hoja}")
        df = pd.read_excel(excel_path, sheet_name=hoja)
        st.write(df.head())

# ==============================
# 🚀 Interfaz principal
# ==============================
def main():
    st.title("🧾 Control y ejecución de hojas autorizadas")

    # Cargar datos
    config = load_config()
    conjuntos_autorizados = load_conjuntos_autorizados()

    # Formulario de inicio de sesión
    st.subheader("Inicio de sesión")
    username = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")

    if st.button("Iniciar sesión"):
        if username == config["username"] and password == config["password"]:
            st.success("✅ Acceso concedido")

            # Subir archivo Excel
            st.subheader("Selecciona el archivo Excel para procesar")
            archivo_excel = st.file_uploader("Cargar archivo (.xlsx)", type=["xlsx"])

            if archivo_excel is not None:
                hojas_autorizadas, hojas_no_autorizadas = validar_hojas(archivo_excel, conjuntos_autorizados)

                if hojas_no_autorizadas:
                    st.warning("⚠️ Hojas no autorizadas detectadas:")
                    for h in hojas_no_autorizadas:
                        st.write(f"- {h}")

                if hojas_autorizadas:
                    st.success("✅ Hojas autorizadas para ejecución:")
                    for h in hojas_autorizadas:
                        st.write(f"- {h}")

                    procesar_hojas(archivo_excel, hojas_autorizadas)
                else:
                    st.error("❌ No se encontró ninguna hoja autorizada para procesar.")
        else:
            st.error("❌ Usuario o contraseña incorrectos")

if __name__ == "__main__":
    main()
