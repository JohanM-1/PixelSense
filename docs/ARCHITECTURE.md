# Arquitectura Técnica - PixelSense

## Diagrama de Alto Nivel

```mermaid
graph TD
    User[Usuario / Cliente] -->|HTTP Request| API[FastAPI Server]
    API -->|Trigger| Capture[Módulo de Captura (MSS)]
    API -->|Image + Prompt| ModelEngine[Motor de Inferencia (Qwen2.5-VL)]
    ModelEngine -->|Load Model| GPU[GPU (PyTorch/CUDA)]
    ModelEngine -->|Text Response| API
    API -->|JSON Response| User
```

## Componentes del Sistema

### 1. Entorno y Gestión de Dependencias
- Uso de `micromamba` para aislar el entorno.
- Canal `conda-forge` y `pytorch` para dependencias binarias optimizadas.

### 2. Módulo de API (`src/api`)
- **Framework**: FastAPI.
- **Responsabilidad**: Manejar peticiones HTTP, validación de datos (Pydantic), orquestación básica.
- **Endpoints**:
    - `POST /v1/chat/completions`: Compatible con estilo OpenAI (futuro).
    - `POST /vision/describe`: Endpoint simplificado para descripción de imágenes.

### 3. Motor de Inferencia (`src/model`)
- **Librería**: Hugging Face Transformers.
- **Modelo**: `Qwen/Qwen2.5-VL-3B-Instruct`.
- **Optimizaciones**:
    - Carga en `bfloat16` o `int4/int8` (bitsandbytes) para reducir VRAM.
    - `device_map="auto"` para distribución automática en GPU/CPU.
- **Clase `VisionModel`**: Singleton que mantiene el modelo cargado en memoria.

### 4. Módulo de Captura (`src/core`)
- **Librería**: `mss` (rápido y multiplataforma).
- **Funciones**:
    - Capturar monitor específico.
    - Capturar región (bounding box).
    - Conversión directa a PIL Image para el modelo.

## Flujo de Datos
1.  **Inicio**: El servidor FastAPI arranca y carga el modelo en VRAM (warm-up).
2.  **Petición**: Cliente solicita `/vision/describe` con `{"task": "describe_screen"}`.
3.  **Captura**: `CaptureService` toma un screenshot -> Objeto `PIL.Image`.
4.  **Procesamiento**:
    - La imagen se preprocesa (`process_vision_info`).
    - Se genera el prompt template de Qwen2.5-VL.
5.  **Inferencia**: El modelo genera tokens.
6.  **Respuesta**: Se decodifica el texto y se envía JSON al cliente.
