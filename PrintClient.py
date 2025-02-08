from flask import Flask, request, jsonify
from escpos.printer import Usb, Network, Serial
import textwrap
import platform
import os

# Si es Windows, importar win32print para buscar la impresora por nombre
if platform.system() == "Windows":
    import win32print

app = Flask(__name__)

# Configuración de la impresora
def get_printer():
    """Intenta conectar la impresora por USB, luego por nombre en Windows."""
    try:
        # Intentar conexión USB (VID y PID de la impresora SAT 22TUS)
        return Usb(0x0416, 0x5011)
    except Exception as e:
        print(f"⚠️ No se encontró la impresora USB por VID/PID: {e}")
        
        # Si estamos en Windows, intentar conectar por nombre de impresora
        if platform.system() == "Windows":
            try:
                printer_name = "SAT 22TUS"  # Nombre de la impresora en Windows
                handle = win32print.OpenPrinter(printer_name)
                return win32print.GetPrinter(handle, 2)  # Obtener configuración
            except Exception as e:
                print(f"⚠️ No se encontró la impresora por nombre en Windows: {e}")
        
        return None  # Si falla, devolver None

# Obtener la impresora
p = get_printer()

# Función para imprimir el ticket formateado
def print_receipt(data):
    if p is None:
        return {"error": "No se encontró una impresora compatible"}, 500

    try:
        # Encabezado del establecimiento
        p.set(align="center", bold=True, width=2, height=2)
        p.text(f"{data['EstablishmentName']}\n")
        p.set(align="center", bold=False, width=1, height=1)
        p.text(f"NIT: {data['establishmentNIT']}\n")
        p.text(f"{data['establishmentAddress']}\n")
        p.text(f"{data['establishmentProvince']}\n")
        p.text(f"Tel: {data['establishmentPhoneNumber']}\n")
        p.text("--------------------------------\n")

        # Información del cliente
        p.set(align="left", bold=True)
        p.text("Cliente:\n")
        p.set(align="left", bold=False)
        p.text(f"{data['movNombreCliente']}\n")
        p.text(f"Documento: {data['movDocumentoCliente']}\n")
        p.text("--------------------------------\n")

        # Encabezado de productos
        p.set(align="left", bold=True)
        p.text("Cant  Descripción        Total\n")
        p.text("--------------------------------\n")

        # Imprimir detalles del movimiento
        p.set(align="left", bold=False)
        for item in data['detalleMovimiento']:
            cantidad = str(item['Cantidad']).ljust(3)
            descripcion = textwrap.shorten(item['DescripcionProducto'], width=18, placeholder="...")
            total = f"{item['Total']:,.2f}".rjust(7)
            p.text(f"{cantidad}  {descripcion}  {total}\n")

        p.text("--------------------------------\n")

        # Totales
        p.set(align="right", bold=True)
        p.text(f"Total Cambio: {data['movTotalCambio']:,.2f}\n")
        p.text("--------------------------------\n")

        # Abrir el cajón si es necesario
        if data.get('open_cash', False):
            p.cashdraw(2)  # Enviar señal para abrir el cajón

        # Cortar papel
        p.cut()

        return {"status": "Success"}, 200
    except Exception as e:
        return {"error": str(e)}, 500

# Endpoint para recibir datos y ejecutar la impresión
@app.route('/print', methods=['POST'])
def print_ticket():
    data = request.json
    print(data)
    # Validar que los datos sean correctos
    required_keys = ["EstablishmentName", "establishmentNIT", "detalleMovimiento", "movTotalCambio"]
    for key in required_keys:
        if key not in data:
            return jsonify({"error": f"Falta el campo requerido: {key}"}), 400

    return print_receipt(data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
