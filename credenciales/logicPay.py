import json
import requests
from epaycosdk.epayco import Epayco
import os

# Instancia la clase Epayco con las credenciales de la cuenta
epayco = Epayco({
    'apiKey': os.getenv('EPAYCO_PUBLIC_KEY'),
    'privateKey': os.getenv('EPAYCO_PRIVATE_KEY'),
    'lenguage': 'ES',  # lenjuage de los mensajes
    'test': os.getenv('EPAYCO_TEST') == 'true',  # "Aqui hay un cambio" "#definir de modo de prueba a produccion

})

def get_quota_details(data):
    try:
        share_id = data.get('share_id')
        if not share_id:
            return {
                'success': False,
                'error': 'El ID de la factura es requerido'
            }

        # Hacer la petición al MS de negocios
        business_ms_base_url = os.getenv('NOTIFICATION_SERVICE_URL')
        business_ms_url = f"{business_ms_base_url}/shares/{share_id}"

        response = requests.get(business_ms_url)
        print("Respuesta del microservicio:", response.status_code, response.text)

        if response.status_code == 200: 
            quota_data = response.json()
            print(f"Datos recibidos de la factura: {quota_data}")

            # if 'quota' not in quota_data:
            #     return {
            #         'success': False,
            #         'error': 'No se encontró la clave "quota" en la respuesta del microservicio'
            #     }

            return {
                'success': True,
                # 'quota': quota_data['quota'],
                'amount': quota_data['amount']
            }
        else:
            return {
                'success': False,
                'error': 'No se pudo obtener la información de la factura'
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


# metodo para el token de la targeta
def create_token(data):
    try:
        card_info = {
            "card[number]": data['card_number'],
            "card[exp_year]": data['exp_year'],
            "card[exp_month]": data['exp_month'],
            "card[cvc]": data['cvc'],
            "hasCvv": True  # hasCvv: validar codigo de seguridad en la transacción
        }
        token = epayco.token.create(card_info)
        return token
    except Exception as e:
        
        return {'error': str(e)}



    # metodo para crear un cliente
def create_customer(token, data):
    customer_info = {
        'name': data['name'],
        'last_name': data['last_name'],
        'email': data['email'],
        'phone': data['phone'],
        'default': True
    }
    customer_info['token_card'] = token
    try:
        customer = epayco.customer.create(customer_info)
        return customer
    except Exception as e:
        return {'error': str(e)}


def proces_payment(data, customer_id, token_card, quota_data):
    try:
        payment_info = {
            'token_card': token_card,
            'customer_id': customer_id,
            "doc_type": "CC",
            'doc_number': data['doc_number'],
            'name': data['name'],
            'last_name': data['last_name'],
            'email': data['email'],
            'city': data['city'],
            'address': data['address'],
            'phone': data['phone'],
            'cell_phone': data['cell_phone'],
            'description': f'Pago de factura {data.get("share_id", "ID no proporcionado")}',
            'value': str(quota_data['amount']),
            'tax': '0',
            'tax_base': str(quota_data['amount']),
            'currency': 'COP'
        }
        print(f"Payment Info: {json.dumps(payment_info, indent=4)}")
        response = epayco.charge.create(payment_info)

        if response.get('status') is True:
            update_quota_status(data['share_id'], response.get('data', {}))
        return response
    except Exception as e:
        return {'error': str(e)}


def update_quota_status(share_id, payment_data):
    try:
        # URL del sistema de notificaciones
        notification_url = os.getenv('NOTIFICATION_SERVICE_URL')
        response = requests.post(notification_url + "/send_payment_info", json=email_data)
        # Datos del correo
        email_data = {
            "recipient":payment_data['email'],  # Cambia esto por el correo del cliente
            "subject": f"Confirmación de pago para la factura {share_id}",
            "message": f"Su pago ha sido procesado exitosamente. Referencia: {payment_data.get('ref_payco')}",
            "status": True
        }

        # Enviar solicitud al sistema de notificaciones
        response = requests.post(notification_url+"/send_payment_info", json=email_data)

        if response.status_code == 200:
            print("Correo enviado exitosamente")
            return True
        else:
            print(f"Error enviando correo: {response.status_code}, {response.text}")
            return False
    except Exception as e:
        print(f"Error actualizando factura: {str(e)}")
        return False
