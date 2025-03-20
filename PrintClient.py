from flask import Flask, request, jsonify
from escpos.printer import Usb, Network
import textwrap
import platform
import os
import subprocess

# Si es Windows, importar win32print para buscar la impresora por nombre
if platform.system() == "Windows":
    import win32print

app = Flask(__name__)

# 📌 Detectar el sistema operativo
SYSTEM_OS = platform.system()

# 📌 Configuración de la impresora para Windows o USB
printer_usb = None

def get_printer():
    """Intenta conectar la impresora por USB, luego por nombre en Windows si aplica."""
    try:
        # Intentar conexión USB (VID y PID de la impresora SAT 22TUS)
        return Usb(0x0416, 0x5011)
    except Exception as e:
        print(f"⚠️ No se encontró la impresora USB por VID/PID: {e}")
        
        # Si estamos en Windows, intentar conectar por nombre de impresora
        if SYSTEM_OS == "Windows":
            try:
                printer_name = "SAT 22TUS"  # Nombre de la impresora en Windows
                handle = win32print.OpenPrinter(printer_name)
                return win32print.GetPrinter(handle, 2)  # Obtener configuración
            except Exception as e:
                print(f"⚠️ No se encontró la impresora por nombre en Windows: {e}")  
                     
        return None  # Si falla, devolver None

printer_usb = get_printer()

# 📌 Función para imprimir en Mac usando CUPS
def print_text_mac(printer_name, text):
    try:
        with open("ticket_mac.txt", "w") as f:
            f.write(text)

        subprocess.run(["lp", "-d", printer_name, "ticket_mac.txt"], check=True)
        return {"status": "Success - Ticket enviado a impresora local en Mac"}, 200
    except Exception as e:
        return {"error": str(e)}, 500

# 📌 Función para imprimir el ticket
def print_receipt(data):
    if printer_usb is None and SYSTEM_OS != "Darwin":  # Darwin = macOS
        return {"error": "No se encontró una impresora USB o compatible"}, 500

    try:
        # 📌 Si es Mac, armar el texto y enviar a imprimir con lp
        if SYSTEM_OS == "Darwin":
            ticket = ""
            # 📌 Encabezado del establecimiento
            ticket += f"{data['EstablishmentName'].center(32)}\n"
            ticket += f"NIT: {data['establishmentNIT']}\n"
            ticket += f"{data['establishmentAddress']}\n"
            ticket += f"{data['establishmentProvince']}\n"
            ticket += f"Tel: {data['establishmentPhoneNumber']}\n"
            ticket += "--------------------------------\n"

            # 📌 Información del cliente
            ticket += "Cliente:\n"
            ticket += f"{data['movNombreCliente']}\n"
            ticket += f"Documento: {data['movDocumentoCliente']}\n"
            ticket += "--------------------------------\n"

            # 📌 Encabezado de productos
            ticket += "Cant  Descripción        Total\n"
            ticket += "--------------------------------\n"

            # 📌 Imprimir detalles del movimiento
            for item in data['detalleMovimiento']:
                cantidad = str(item['Cantidad']).ljust(3)
                descripcion = textwrap.shorten(item['DescripcionProducto'], width=18, placeholder="...")
                total = f"{item['Total']:,.2f}".rjust(7)
                ticket += f"{cantidad}  {descripcion.ljust(18)}  {total}\n"

            ticket += "--------------------------------\n"

            # 📌 Totales
            ticket += f"{'Total Cambio:'.rjust(24)} {data['movTotalCambio']:,.2f}\n"
            ticket += "--------------------------------\n"

            return print_text_mac("HP_Smart_Tank_500_series", ticket)

        # 📌 Si es Windows o USB
        p = printer_usb

        # 📌 Abrir el cajón SIEMPRE
        p.cashdraw(2)  # Señal para abrir el cajón

        # 📌 Si PrintTicket es False, solo abrimos el cajón y salimos
        if not data.get('PrintTicket', True):
            print("✅ Solo se abrió el cajón, no se imprimió el ticket")
            return {"status": "Success - Cajón abierto sin impresión"}, 200

        # 📌 Encabezado del establecimiento
        p.set(align="center", bold=True, width=2, height=2)
        p.text(f"{data['EstablishmentName']}\n")
        p.set(align="center", bold=False, width=1, height=1)
        p.text(f"NIT: {data['establishmentNIT']}\n")
        p.text(f"{data['establishmentAddress']}\n")
        p.text(f"{data['establishmentProvince']}\n")
        p.text(f"Tel: {data['establishmentPhoneNumber']}\n")
        p.text("--------------------------------\n")

        # 📌 Información del cliente
        p.set(align="left", bold=True)
        p.text("Cliente:\n")
        p.set(align="left", bold=False)
        p.text(f"{data['movNombreCliente']}\n")
        p.text(f"Documento: {data['movDocumentoCliente']}\n")
        p.text("--------------------------------\n")

        # 📌 Encabezado de productos
        p.set(align="left", bold=True)
        p.text("Cant  Descripción        Total\n")
        p.text("--------------------------------\n")

        # 📌 Imprimir detalles del movimiento
        p.set(align="left", bold=False)
        for item in data['detalleMovimiento']:
            cantidad = str(item['Cantidad']).ljust(3)
            descripcion = textwrap.shorten(item['DescripcionProducto'], width=18, placeholder="...")
            total = f"{item['Total']:,.2f}".rjust(7)
            p.text(f"{cantidad}  {descripcion}  {total}\n")

        p.text("--------------------------------\n")

        # 📌 Totales
        p.set(align="right", bold=True)
        p.text(f"Total Cambio: {data['movTotalCambio']:,.2f}\n")
        p.text("--------------------------------\n")

        # 📌 Cortar papel
        p.cut()

        return {"status": "Success - Ticket impreso y cajón abierto"}, 200

    except Exception as e:
        return {"error": str(e)}, 500

# 📌 Endpoint para recibir datos y ejecutar la impresión
@app.route('/print', methods=['POST'])
def print_ticket():
    data = request.json
    print(data)
    # 📌 Validar que los datos sean correctos
    required_keys = ["EstablishmentName", "establishmentNIT", "detalleMovimiento", "movTotalCambio"]
    for key in required_keys:
        if key not in data:
            return jsonify({"error": f"Falta el campo requerido: {key}"}), 400

    return print_receipt(data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
