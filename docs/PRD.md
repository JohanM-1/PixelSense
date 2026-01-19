# Product Requirements Document (PRD) - PixelSense

## 1. Visión del Producto
PixelSense es un asistente de visión multimodal local que "ve" lo que sucede en la pantalla del usuario y proporciona descripciones, análisis y asistencia en tiempo real. Se ejecuta completamente en local utilizando modelos de vanguardia (Qwen2.5-VL) para garantizar la privacidad y baja latencia, expuesto a través de una API flexible.

## 2. Objetivos del MVP
- **Inferencia Local**: Ejecutar Qwen2.5-VL-3B/7B (dependiendo del hardware) localmente.
- **Captura de Pantalla**: Capacidad para capturar pantalla completa o regiones.
- **API Propia**: Servicio FastAPI que desacopla la inferencia de la interfaz.
- **Privacidad**: Todo el procesamiento ocurre en el dispositivo.

## 3. Stack Tecnológico
- **Gestión de Entorno**: Micromamba.
- **Lenguaje**: Python 3.10+.
- **Framework DL**: PyTorch (con soporte CUDA).
- **Modelo**: Qwen2.5-VL (Qwen/Qwen2.5-VL-3B-Instruct o 7B).
- **Backend**: FastAPI + Uvicorn.
- **Captura**: MSS / PyAutoGUI.
- **Librerías Clave**: `transformers`, `accelerate`, `pillow`, `qwen-vl-utils`.

## 4. Funcionalidades Principales
1.  **Endpoint `/analyze`**: Recibe una imagen (base64 o path) y un prompt. Devuelve la descripción.
2.  **Endpoint `/capture_and_analyze`**: Captura la pantalla actual y la analiza inmediatamente.
3.  **Soporte de Streaming**: (Opcional para MVP) Respuestas token a token.

## 5. Requerimientos de Hardware (Estimados)
- **GPU**: NVIDIA RTX con al menos 6GB VRAM (para 3B cuantizado) o 12GB+ (para 7B).
- **RAM**: 16GB+.
- **Almacenamiento**: ~10GB para modelos y entorno.
