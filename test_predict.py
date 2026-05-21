import requests, sys

BASE = 'http://localhost:8001'

# Obtain JWT token
resp = requests.post(f'{BASE}/token', data={'username': 'admin', 'password': 'costos1234'})
if resp.status_code != 200:
    print('Failed to get token:', resp.status_code, resp.text)
    sys.exit(1)

token = resp.json()['access_token']
print('Token obtained')

# Prediction payload
payload = {
    "producto": "grava",
    "tipo_producto": "NaN",
    "marca": "Ladrillera Virú",
    "categoria": "material_construccion",
    "cantidad": 5,
    "precio_unitario": 36.86,
    "metodo_pago": "efectivo",
    "comprobante": "boleta"
}

headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

# Send prediction request
resp2 = requests.post(f'{BASE}/predict', json=payload, headers=headers)
print('Predict status:', resp2.status_code)
print('Predict body:', resp2.text)
