import os, uuid, shutil
from fastapi import FastAPI, UploadFile, File, Form, Header, HTTPException
from fastapi.responses import FileResponse
from agent import run_agent

app = FastAPI(title="Excel Simulation Agent")
DATA_DIR = os.getenv("DATA_DIR", "/data")
API_KEY = os.getenv("AGENT_API_KEY")              # kunci akses sederhana


def check_auth(key):
    if API_KEY and key != API_KEY:
        raise HTTPException(401, "API key salah")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/simulate")
async def simulate(instruction: str = Form(...),
                   file: UploadFile | None = File(None),
                   x_api_key: str | None = Header(None)):
    check_auth(x_api_key)
    path = None
    if file:
        os.makedirs(f"{DATA_DIR}/uploads", exist_ok=True)
        path = f"{DATA_DIR}/uploads/{uuid.uuid4().hex}_{file.filename}"
        with open(path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    result = run_agent(instruction, path)
    if result["file_id"]:
        result["download_url"] = f"/download/{result['file_id']}"
    return result


@app.get("/download/{file_id}")
def download(file_id: str, x_api_key: str | None = Header(None)):
    check_auth(x_api_key)
    path = f"{DATA_DIR}/{file_id}.xlsx"
    if not file_id.isalnum() or not os.path.exists(path):
        raise HTTPException(404, "File tidak ditemukan")
    return FileResponse(path, filename=f"simulasi_{file_id}.xlsx",
                        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")