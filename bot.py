from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import pandas as pd
import datetime
import os

app = Flask(__name__)

# Configuración Twilio
TWILIO_ACCOUNT_SID = 'AC2b5a756efff2c4bc1871f4bc1326b670'
TWILIO_AUTH_TOKEN = '3a0f83c360de5cd5b72106f101d166c6'
TWILIO_WHATSAPP_NUMBER = 'whatsapp:+14155238886'

# Estado temporal en memoria
estado_usuarios = {}

@app.route("/whatsapp", methods=["POST"])
def whatsapp_reply():
    numero = request.form.get("From", "").strip()
    mensaje = request.form.get("Body", "").strip()
    respuesta = MessagingResponse()

    # Verificar estado del usuario
    estado = estado_usuarios.get(numero, {})

    if not estado:
        estado_usuarios[numero] = {"etapa": "nombre"}
        respuesta.message("¡Hola! 😊 ¿Cuál es tu nombre?")
        return str(respuesta)

    elif estado["etapa"] == "nombre":
        estado_usuarios[numero]["nombre"] = mensaje
        estado_usuarios[numero]["etapa"] = "servicio"
        respuesta.message(f"¡Gracias {mensaje}! 🙌 ¿Qué servicio te interesa o sobre qué deseas información?")
        return str(respuesta)

    elif estado["etapa"] == "servicio":
        nombre_cliente = estado_usuarios[numero]["nombre"]
        servicio = mensaje

        # Cargar asesores
        archivo_asesores = "Asesores.xlsx"
        archivo_asignaciones = "Asignaciones.xlsx"

        try:
            df = pd.read_excel(archivo_asesores)
        except Exception as e:
            print(f"❌ Error al cargar asesores: {e}")
            respuesta.message("Ocurrió un problema interno al cargar los asesores.")
            return str(respuesta)

        # Buscar siguiente asesor
        try:
            if os.path.exists(archivo_asignaciones):
                asignaciones_df = pd.read_excel(archivo_asignaciones)
                ultimo = asignaciones_df.iloc[-1]["Asesor"]
                asesores = df.iloc[:, 0].tolist()
                idx_siguiente = (asesores.index(ultimo) + 1) % len(asesores)
            else:
                asignaciones_df = pd.DataFrame(columns=["Nombre", "Servicio", "WhatsApp", "Asesor", "Teléfono Asesor", "Fecha"])
                idx_siguiente = 0
        except Exception as e:
            print(f"❌ Error al procesar asignaciones: {e}")
            asignaciones_df = pd.DataFrame(columns=["Nombre", "Servicio", "WhatsApp", "Asesor", "Teléfono Asesor", "Fecha"])
            idx_siguiente = 0

        # Asignar asesor
        asesor_nombre = df.iloc[idx_siguiente, 0]
        asesor_telefono = str(df.iloc[idx_siguiente, 1]).strip()

        # Guardar asignación
        nueva = pd.DataFrame([{
            "Nombre": nombre_cliente,
            "Servicio": servicio,
            "WhatsApp": numero,
            "Asesor": asesor_nombre,
            "Teléfono Asesor": asesor_telefono,
            "Fecha": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }])
        asignaciones_df = pd.concat([asignaciones_df, nueva], ignore_index=True)
        asignaciones_df.to_excel(archivo_asignaciones, index=False)

        # Mensaje para cliente
        respuesta.message(f"Gracias {nombre_cliente} 🙌\nTu asesor será *Lic. {asesor_nombre}* 📞 ({asesor_telefono}). Muy pronto se comunicará contigo.")

        # Notificación al asesor
        try:
            telefono_formateado = f'whatsapp:+521{asesor_telefono.lstrip("52")}' if not asesor_telefono.startswith("+") else f'whatsapp:{asesor_telefono}'
            cliente_twilio = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            mensaje_asesor = (
                f"🔔 Nuevo cliente asignado:\n"
                f"Nombre: {nombre_cliente}\n"
                f"Servicio: {servicio}\n"
                f"WhatsApp: {numero}"
            )
            cliente_twilio.messages.create(
                body=mensaje_asesor,
                from_=TWILIO_WHATSAPP_NUMBER,
                to=telefono_formateado
            )
        except Exception as e:
            print(f"❌ No se pudo enviar al asesor: {e}")

        # Limpiar estado del cliente
        estado_usuarios.pop(numero)

        return str(respuesta)

    # Si algo raro ocurre
    respuesta.message("Lo siento, ocurrió un error. Por favor escribe 'Hola' para comenzar de nuevo.")
    return str(respuesta)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
