import uvicorn

if __name__ == "__main__":
    # Ejecutar la aplicación desde la raíz permite que las importaciones de 'src' funcionen correctamente
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
