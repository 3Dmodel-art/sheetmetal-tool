from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uuid
import os
import zipfile
from geometry import generate_all_files

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PodiumRequest(BaseModel):
    length: float
    width: float
    height: float
    thickness: float
    bend1: float # Flange 1
    bend2: float # Flange 2

@app.post("/api/generate")
def generate_podium(data: PodiumRequest):
    try:
        job_id = str(uuid.uuid4())[:8]
        result = generate_all_files(
            length=data.length,
            width=data.width,
            height=data.height,
            thickness=data.thickness,
            bend1=data.bend1,
            bend2=data.bend2,
            job_id=job_id
        )
        return {"job_id": job_id, "blank_size": result["blank_size"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/download/{job_id}")
def download_package(job_id: str):
    folder = f"outputs/{job_id}"
    zip_path = f"outputs/podium_{job_id}.zip"
    
    if not os.path.exists(folder):
        raise HTTPException(status_code=404, detail="Job not found")

    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for root, _, files in os.walk(folder):
            for file in files:
                zipf.write(os.path.join(root, file), arcname=file)

    return FileResponse(zip_path, media_type="application/zip", filename=f"podium_{job_id}.zip")
