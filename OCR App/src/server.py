#Tasks to be performed by app:
#1.Serving HTML templates. Functionality- HTTP GET 
#2.API endpoint to perform OCR

from click import File
from fastapi import FastAPI, Request, UploadFile,BackgroundTasks
from fastapi.templating import Jinja2Templates
import shutil
import os
import ocr
import uuid

app=FastAPI()

templates=Jinja2Templates(directory="templates")

@app.get("/")#location of get call will be the home location
def home(request: Request):#standard request object provided by FastAPI
    return templates.TemplateResponse("index.html",{"request":request})

@app.post("/api/v1/extract_text")
async def perform_ocr(image: UploadFile=File(...)):#UploadFile is a special data type provided by FastAPI again, "..." is pyhton data type called Ellipsis which used as a placeholder usually 
    temp_file=_save_file_to_disk(image, path="temp", save_as="temp")
    text= await ocr.read_image(temp_file) #'await' is a python keyword that will tell the program to not hold request from other next users if this first user's request is on hold
    #the function awaiting must also be async function. ocr's read_image functions must also be async.
    return {"filename":image.filename, "text":text}

#the below function will queue the most intensive task in the background and immediately returns the response, this will make the API speed not slow
@app.post("/api/v1/bulk_extract_text")
async def bulk_extract_text(request: Request, bg_task: BackgroundTasks):
    images = await request.form()
    folder_name = str(uuid.uuid4())
    os.mkdir(folder_name)

    for image in images.values():
        temp_file = _save_file_to_disk(image, path=folder_name, save_as=image.filename)

    bg_task.add_task(ocr.read_images_from_dir, folder_name, write_to_file=True)
    return {"task_id": folder_name, "num_files": len(images)}



@app.get("/api/v1/bulk_output/{task_id}")#this api will bee pinged every 3 seconds and it will identify all the images that have benn converted till this time.
#Suppose you 100 images to be converted to text, every 3-6 seconds few images will show those images, 
# like this the user doesn't have to wait till all  100 images have been converted to see the first few that already have been converted.
async def bulk_output(task_id):
    text_map = {}
    for file_ in os.listdir(task_id):
        if file_.endswith("txt"):
            text_map[file_]=open(os.path.join(task_id, file_)).read()
        return {"task_id": task_id, "output": text_map}
    
    

def _save_file_to_disk(uploaded_file, path=".", save_as="default"):
    extension = os.path.splitext(uploaded_file.filename)[-1]
    temp_file = os.path.join(path, save_as + extension)
    with open(temp_file, "wb") as buffer:
        shutil.copyfileobj(uploaded_file.file, buffer)
    return temp_file

