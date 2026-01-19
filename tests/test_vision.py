import requests
import json
import time
import sys
import os

# Add project root to path if needed (though this test uses requests to localhost, so it might not need src imports directly, but good practice if it did)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_capture():
    url = "http://localhost:8000/api/v1/vision/capture"
    
    payload = {
        "prompt": "Describe detalladamente qué ventanas y aplicaciones se ven en la pantalla.",
        "monitor_index": 1
    }
    
    print(f"📡 Enviando petición a {url}...")
    print("⏳ Esto puede tardar unos segundos la primera vez (descarga/carga del modelo)...")
    
    start_time = time.time()
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        data = response.json()
        duration = time.time() - start_time
        
        print("\n✅ ¡Éxito!")
        print(f"⏱️ Tiempo de respuesta: {duration:.2f}s")
        print("\n📝 Descripción generada:")
        print("-" * 50)
        print(data["description"])
        print("-" * 50)
        
    except requests.exceptions.ConnectionError:
        print("❌ Error: No se pudo conectar con el servidor. Asegúrate de que 'python run.py' esté ejecutándose.")
    except Exception as e:
        print(f"❌ Error: {e}")
        if 'response' in locals():
            print(f"Detalle del servidor: {response.text}")

if __name__ == "__main__":
    test_capture()
