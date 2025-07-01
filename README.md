# Subir y Procesar Imágenes con IA

Este proyecto es una aplicación web simple que permite subir una o varias imágenes, procesarlas con un modelo de IA desde LM Studio, y mostrar la descripción y las palabras clave generadas junto a cada imagen en tiempo real, gracias a Server-Sent Events (SSE).

---

## 📋 Características

- **Frontend ligero** en HTML, CSS y JavaScript puro.
- **Backend con FastAPI** en Python.
- **Subida de múltiples archivos** vía formulario.
- **Procesado en streaming** de tokens y eventos SSE para actualizar la UI al instante. Se usa LM Studio como servidor
- **Copia de los resultados en el portapapeles**
- **Salida en JSON y CSV** con 3 campos:
  - `Nombre de la imagen`
  - `Descripción`
  - `palabras_clave`
- **Modelo de IA usado** Puedes usar cualquiera que reconoaca imágenes. A mi me ha funcionado muy bien gemma-3-12b-it-qat
---

## 🚀 Instalación y puesta en marcha

1. **Clonar el repositorio**  

   git clone https://github.com/Pedropadillar/imagen_metadatos.git
   cd imagen_metadatos

2. **Crear y activar un entorno virtual, si se desea**

   python3 -m venv venv
   source venv/bin/activate     # Linux / macOS
   venv\Scripts\activate        # Windows

3. **Instalar dependencias**

   pip install -r requirements.txt

4. **Ejecutar la aplicación**

   uvicorn main:app --reload

5. **Abrir en el navegador**
   Navega a `http://localhost:8000` para ver la interfaz.

---

## ⚙️ Estructura del proyecto

├── main.py           # FastAPI + SSE + manejo de uploads

├── templates/

│   └── index.html    # Frontend: subida de imágenes y rendering SSE

├── temp/             # Carpeta donde se guardan los archivos temporales (imágenes subidas)

├── requirements.txt  # Dependencias Python

└── README.md         # Documentación del proyecto

└── dist/             # Fichero ejecutable como aplicación de escritorio


---

## 🖥️ Uso

1. Haz clic en **“Elegir archivos”** y selecciona una o varias imágenes.
2. Pulsa el botón **“Subir y Procesar”**.
3. Verás junto a cada miniatura el texto **“Procesando…”** mientras la IA trabaja.
4. Una vez lista la respuesta, se actualizará automáticamente con:

   * La descripción en texto plano.
   * La lista de palabras clave separadas por comas.
   * Los botones para copiar al portapapeles y exportar a JSON y CSV

---

## 🤝 Contribuciones

Este repositorio es una prueba piloto de las posibilidades del uso de la IA en la Administración pública, que puede ser extendido a otros ámbitos.

Únete al grupo de Telegram https://t.me/iadministracion

¡Todas las contribuciones son bienvenidas!

1. Abre un *issue* para reportar bugs o sugerir mejoras.
2. Haz un *fork*, crea una rama feature/tu-mejora y envía un *pull request*.



