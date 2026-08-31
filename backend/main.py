from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import zipfile
import uuid
import os
from geometry import generate_all_files

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class InputData(BaseModel):
    length: float
    width: float
    height: float
    thickness: float
    bend1: float
    bend2: float

@app.post("/api/generate")
def generate(data: InputData):
    job_id = str(uuid.uuid4())[:8]
    results = generate_all_files(
        data.length, data.width, data.height, data.thickness, data.bend1, data.bend2, job_id
    )
    return {"job_id": job_id, "blank_size": results["blank_size"]}

@app.get("/api/download/{job_id}")
def download(job_id: str):
    folder = f"outputs/{job_id}"
    zip_path = f"outputs/{job_id}_pack.zip"

    with zipfile.ZipFile(zip_path, 'w') as z:
        for root, _, files in os.walk(folder):
            for f in files:
                z.write(os.path.join(root, f), arcname=f)

    return FileResponse(zip_path, filename=f"podium_sheet_metal_pack_{job_id}.zip")
