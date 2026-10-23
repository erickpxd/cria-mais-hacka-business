from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

from PIL import Image
import numpy as np
import cv2

from ollama import Client


app = FastAPI()

client = Client(host='http://ollama:11434')

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/upload")
async def process_image(file: UploadFile = File(...), target_lang: str = "pt"):
    # 1. Read the uploaded file into bytes
    contents = await file.read()
    
    # 2. Convert bytes to a numpy array (OpenCV format)
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    

    return {
        "filename": file.filename,

    }


#CHANGE: Retrabalhar toda essa rota para que ela seja sobre formatação de imagem
@app.post("/api/uploadHandwriting")
async def readHandwriting(file: UploadFile = File(...)):
    image = await file.read()
    response = client.chat(
        #CHANGE: trocar esse model
    model='deepseek-ocr',
    messages=[{
        'role': 'user',
        'content': 'Extract all text from this image and format it as JSON.',
        'images': [image]
        }]
    )
    extracted_text = response['message']['content']

    return {
        "filename": file.filename,
        "text": extracted_text
    }



@app.get("/api")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}