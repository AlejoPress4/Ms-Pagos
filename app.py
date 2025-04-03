from flask import Flask, request, jsonify
import json
from dotenv import load_dotenv
from epaycosdk.epayco import Epayco
from flask_cors import CORS
from credenciales.logicPay import *


load_dotenv()  # carga las variables de entorno que estan en el archivo .env

app = Flask(__name__)  # Esta instancia se utiliza para configurar y ejecutar la aplicación web
CORS(app)  # Esto permite todas las solicitudes de cualquier origen


# enpoint para manejar todo el flujo de pago
@app.route('/proces_payment', methods=['POST'])
def handle_proces_payment():
    try:
        data = request.json

        # Validar datos requeridos
        required_fields = ['share_id', 'card_number', 'exp_year', 'exp_month', 'cvc',
                           'name', 'last_name', 'email', 'doc_number', 'city', 'address',
                           'phone', 'cell_phone']

        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"El campo {field} es requerido"}), 400

        # Obtener detalles de la factura
        quota_response = get_quota_details(data)
        if not quota_response['success']:
            return jsonify({"error": quota_response['error']}), 400

        # Crear token de tarjeta
        token_response = create_token(data)
        print("Token response:", json.dumps(token_response))

        if not token_response.get('status'):
            return jsonify({"error": "Error creando token de tarjeta",
                            "details": token_response.get('error')}), 500

        token_card = token_response['id']

        # Crear cliente
        customer_response = create_customer(token_card, data)
        print("Customer response:", json.dumps(customer_response))

        if 'error' in customer_response:
            return jsonify({"error": "Error creando cliente",
                            "details": customer_response['error']}), 500

        customer_id = customer_response['data']['customerId']

        # Procesar pago
        payment_response = proces_payment(data, customer_id, token_card, quota_response)
        print("Payment response:", json.dumps(payment_response))

        if 'error' in payment_response:
            return jsonify({"error": "Error procesando pago",
                            "details": payment_response['error']}), 500

        return jsonify({
            "status": "success",
            "message": "Pago procesado correctamente",
            "data": payment_response
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": "Error procesando el pago",
            "error": str(e)
        }), 500


if __name__== '__main__':
    app.run(debug=True, port=5051)  # Cambia el puerto si es necesario