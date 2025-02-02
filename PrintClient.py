from flask import Flask, request
from escpos.printer import Usb
import os

app = Flask(__name__)

# Configurar la impresora (ajustar VID y PID según el modelo de la impresora)
try:
    p = Usb(0x0416, 0x5011)  # VID y PID de la impresora (cambia según el modelo)
except Exception as e:
    print(f"Error conectando a la impresora: {e}")
    p = None

@app.route('/print', methods=['POST'])
def print_ticket():
    if p is None:
        return {"error": "No se encontró la impresora"}, 500

    data = request.json
    ticket_text = data.get('text', '')
    open_cash = data.get('open_cash', False)
    #print("ticket_text", ticket_text)
    try:
        p.text(ticket_text + "\n")  # Imprimir texto
        if open_cash:
            p.cashdraw(2)  # Enviar comando de apertura del cajón monedero
        p.cut()  # Cortar el ticket
        return {"status": "Success"}, 200
    except Exception as e:
        return {"error": str(e)}, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
