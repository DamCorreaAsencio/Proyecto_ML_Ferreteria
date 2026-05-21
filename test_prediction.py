import requests
import json

url = "http://127.0.0.1:8000/predict"
token = "fake-jwt-token" # In a real scenario we need a valid token, but the backend fake auth might accept anything if we didn't implement real JWT validation properly or if we use the login endpoint first.

# Let's try to login first to get a token
login_url = "http://127.0.0.1:8000/token"
login_data = {"username": "admin", "password": "costos1234"}
try:
    resp = requests.post(login_url, data=login_data)
    if resp.status_code == 200:
        token = resp.json()["access_token"]
        print(f"Got token: {token[:10]}...")
    else:
        print(f"Login failed: {resp.status_code} {resp.text}")
        exit(1)
except Exception as e:
    print(f"Could not connect to server: {e}")
    exit(1)

# Now predict
headers = {"Authorization": f"Bearer {token}"}
payload = {
    "producto": "cemento",
    "marca": "sol",
    "categoria": "material_construccion",
    "precio_unitario": 35.0,
    "tipo_producto": "saco 42.5kg",
    "metodo_pago": "efectivo",
    "comprobante": "boleta"
}

try:
    resp = requests.post(url, json=payload, headers=headers)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text}")
except Exception as e:
    print(f"Prediction failed: {e}")
