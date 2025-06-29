import os
import uuid
import queue
import openai 
import time
import asyncio
import tempfile
from typing import List
import base64
import mimetypes # To infer mimetype from file extension

from fastapi import FastAPI, File, UploadFile, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

# pip install openai>=0.27.0
# You might need Pillow for image preprocessing if you want to resize/optimize images before sending.
# from PIL import Image # pip install Pillow

# Custom system prompt - THIS IS CRUCIAL AND MUST BE ADAPTED FOR YOUR MULTIMODAL MODEL
# Ensure your LM Studio model is capable of vision input and can extract keywords.
sistema = """
Examina detenidamente la imagen proporcionada. Dame una descripción y extrae las palabras clave que describan los objetos, escenas y sujetos principales presentes en la imagen.
Devuelve los resultados en formato JSON y en español.
Escribe directamente la descripción y las palabras clave, sin respuestas adicionales o explicaciones innecesarias como "Aquí tienes la descripción y las palabras clave de la imagen:".
"""
# Configure the client for LM Studio
client = openai.OpenAI(
    base_url="http://localhost:1234/v1",  # your LM Studio endpoint
    api_key="not-needed"                  # LM Studio does not require a key
)

app = FastAPI()

# Create a 'static' directory if it doesn't exist
if not os.path.exists("static"):
    os.makedirs("static")

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def serve_index():
    return FileResponse("static/index.html")

# Store queues per task_id (each task_id will now represent a batch of images)
tasks_queues: dict[str, queue.Queue] = {}

@app.post("/upload")
async def upload_files(background_tasks: BackgroundTasks, files: List[UploadFile] = File(...)):
    if not files:
        print("¡No se han recibido archivos en el endpoint /upload!")
        return {"error": "No se han recibido archivos."}

    print(f"Recibido/s {len(files)} fichero/s.")

    task_id = str(uuid.uuid4())
    tmp_dir = tempfile.gettempdir()
    uploaded_image_info = []

    for file in files:
        if not (file.content_type and file.content_type.startswith("image/")):
            continue
        if not file.content_type.startswith("image/"):
            print(f"Skipping non-image file: {file.filename} ({file.content_type})")
            continue # Skip non-image files

        image_id = str(uuid.uuid4())
        # Use a more robust temporary file naming to avoid conflicts and simplify cleanup
        temp_file_name = (
    f"{task_id}_{image_id}_"
    + (file.filename or "")
        .replace("/", "_")
        .replace("\\", "_")
)
        dest_path = os.path.join(tmp_dir, temp_file_name)

        try:
            content = await file.read()
            with open(dest_path, "wb") as f:
                f.write(content)
            uploaded_image_info.append({"image_id": image_id, "file_path": dest_path, "filename": file.filename})
            print(f"Saved temporary file: {dest_path}")
        except Exception as e:
            print(f"Error saving file {file.filename}: {e}")
            # Optionally, you could add an error event to the queue for this specific image

    if not uploaded_image_info:
        print("No valid image files were uploaded.")
        return {"error": "No valid image files uploaded."}

    q = queue.Queue()
    tasks_queues[task_id] = q
    # Start the background task to process images
    background_tasks.add_task(process_images, task_id, uploaded_image_info)
    response_data = {"task_id": task_id, "uploaded_images": [{"image_id": img["image_id"], "filename": img["filename"]} for img in uploaded_image_info]}
    print(f"Sending initial response to client for task_id {task_id}: {response_data}")
    return response_data

def process_images(task_id: str, image_info_list: List[dict]):
    q = tasks_queues[task_id]

    q.put({"event": "status", "data": f"Processing {len(image_info_list)} images..."})
    time.sleep(0.3)

    for img_info in image_info_list:
        image_id = img_info["image_id"]
        file_path = img_info["file_path"]
        filename = img_info["filename"]

        q.put({"event": "status", "data": f"Extracting features from {filename}...", "image_id": image_id})
        time.sleep(0.1)

        base64_image = None
        media_type = None

        try:
            with open(file_path, "rb") as image_file:
                image_bytes = image_file.read()

            # Infer media type from file extension
            media_type, _ = mimetypes.guess_type(filename)
            if not media_type or not media_type.startswith("image/"):
                media_type = "application/octet-stream" # Fallback

            base64_image = base64.b64encode(image_bytes).decode("utf-8")
            image_url_data = f"data:{media_type};base64,{base64_image}"

        except Exception as e:
            print(f"Error reading or encoding image {filename}: {str(e)}")
            q.put({"event": "error", "image_id": image_id, "data": f"Error reading image {filename}: {str(e)}"})
            if os.path.exists(file_path):
                os.remove(file_path) # Clean up file even on read error
            continue # Skip to next image

        q.put({"event": "status", "data": f"Sending {filename} to model...", "image_id": image_id})

        # --- OPENAI API CALL FOR IMAGE ANALYSIS ---
        # THIS PART IS HIGHLY DEPENDENT ON YOUR LM STUDIO MODEL'S CAPABILITIES AND API
        messages = [
            {"role": "system", "content": sistema},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What are the main objects in this image? Provide keywords."},
                    {"type": "image_url", "image_url": {"url": image_url_data}}
                ]
            }
        ]

        try:
            # IMPORTANT: Replace "your-multimodal-model-name" with the actual model you are running in LM Studio
            # For example, "llava-v1.6-34b" or "gpt-4-vision-preview" if you're using a compatible local proxy
            response = client.chat.completions.create(
                model="your-multimodal-model-name", # <--- *** CHANGE THIS ***
                messages=messages,
                stream=True,
                max_tokens=4000 # Limit response length to avoid excessively long outputs
            )
            extracted_keywords = ""
            for chunk in response:
                tok = getattr(chunk.choices[0].delta, "content", "")
                if tok:
                    extracted_keywords += tok
                    # Send tokens with image_id so client knows which image it belongs to
                    #print(f"[{image_id} - {filename}] Token: {tok}") # Debugging
                    q.put({"event": "token", "image_id": image_id, "data": tok})
            # Send a final 'image_complete' event for each image
            final_keywords = extracted_keywords.strip()
            #print(f"[{image_id} - {filename}] Processing complete. Keywords: {final_keywords}") # Debugging
            q.put({"event": "image_complete", "image_id": image_id, "keywords": final_keywords})

        except openai.OpenAIError as api_error:
            # Catch specific OpenAI API errors (e.g., model not found, invalid request)
            print(f"API Error processing {filename} (image_id: {image_id}): {api_error}")
            q.put({"event": "error", "image_id": image_id, "data": f"API Error: {str(api_error)}"})
        except Exception as e:
            # Catch any other unexpected errors during model interaction
            print(f"Unexpected error processing {filename} (image_id: {image_id}): {e}")
            q.put({"event": "error", "image_id": image_id, "data": f"Unexpected error: {str(e)}"})
        finally:
            # Clean up the temporary image file after processing, regardless of success or failure
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Cleaned up temporary file: {file_path}")

    q.put({"event": "status", "data": "Process completed for all images."})
    q.put({"event": "end", "data": ""}) # Signal the end of the batch processing

@app.get("/stream/{task_id}")
async def stream(task_id: str):
    async def event_generator():
        # Wait until the queue for this task_id is initialized
        while task_id not in tasks_queues:
            await asyncio.sleep(0.1)
        q = tasks_queues[task_id]

        # Continuously yield events until 'end' is received
        while True:
            item = q.get()
            # Format as Server-Sent Event. Use .get to avoid KeyError if 'data' is missing
            if "image_id" in item:
                # We send 'id' field for consistency with EventSource's lastEventId property
                yield f"event: {item.get('event','')}\nid: {item.get('image_id','')}\ndata: {item.get('data','')}\n\n"
            else:
                # Global status messages don't need an image_id
                yield f"event: {item.get('event','')}\ndata: {item.get('data','')}\n\n"

            if item.get("event") == "end":
                # Clean up the queue for this task_id after processing is complete
                # This helps prevent memory leaks for long-running services
                if task_id in tasks_queues:
                    del tasks_queues[task_id]
                    print(f"Cleaned up queue for task_id: {task_id}")
                break

    return StreamingResponse(event_generator(), media_type="text/event-stream")