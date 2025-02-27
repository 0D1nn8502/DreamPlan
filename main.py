import os
import shutil
import sqlite3

from fastapi import Depends, FastAPI, File, Form, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)  # Ensure upload directory exists

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="static/uploads"), name="uploads")

templates = Jinja2Templates(directory="templates")

def get_db():
    conn = sqlite3.connect("database.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS concerns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            media TEXT
        )
    """)
    conn.commit()
    return conn

@app.get("/")
def home(request: Request):
    db = get_db()
    concerns = db.execute("SELECT * FROM concerns").fetchall()
    db.close()
    
    return templates.TemplateResponse("index.html", {"request": request, "concerns": concerns})

@app.post("/add")
async def add_concern(text: str = Form(...), media: UploadFile = File(None)):
    db = get_db()
    media_path = None

    if media:
        file_ext = media.filename.split(".")[-1]
        file_name = f"{text[:10].replace(' ', '_')}_{media.filename}"  # Unique filename
        media_path = f"{UPLOAD_DIR}/{file_name}"
        
        with open(media_path, "wb") as buffer:
            shutil.copyfileobj(media.file, buffer)
        
        media_path = f"/uploads/{file_name}"  # Store relative path in DB

    db.execute("INSERT INTO concerns (text, media) VALUES (?, ?)", (text, media_path))
    db.commit()
    db.close()

    return RedirectResponse(url="/", status_code=303)


@app.post("/delete/{concern_id}")
def delete_concern(concern_id: int):
    db = get_db()
    concern = db.execute("SELECT media FROM concerns WHERE id = ?", (concern_id,)).fetchone()

    if concern and concern[0]:  # If media exists, delete file
        try:
            os.remove(concern[0])
        except FileNotFoundError:
            pass

    db.execute("DELETE FROM concerns WHERE id = ?", (concern_id,))
    db.commit()
    db.close()
    return RedirectResponse(url="/", status_code=303)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
