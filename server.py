# Запуск: uvicorn server:app --reload --port 8000
from fastapi import FastAPI, Depends, HTTPException, Header
from pydantic import BaseModel
import sqlite3
import secrets

app = FastAPI(title="Glide Sync Server - Secure")

# Инициализация БД
conn = sqlite3.connect("glide_sync.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        token TEXT
    )
""")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS sync_data (
        user_id TEXT PRIMARY KEY,
        bookmarks TEXT,
        settings TEXT,
        vault TEXT,
        last_sync TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
conn.commit()

class AuthPayload(BaseModel):
    username: str

class SyncPayload(BaseModel):
    payload: dict

def verify_token(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token format")
    token = authorization.replace("Bearer ", "")
    
    cursor.execute("SELECT username FROM users WHERE token = ?", (token,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return row[0] # Возвращаем username

@app.post("/api/auth/register_or_login")
async def authenticate(data: AuthPayload):
    username = data.username
    if not username:
        raise HTTPException(status_code=400, detail="Username required")
        
    cursor.execute("SELECT token FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    if row:
        return {"token": row[0], "msg": "Logged in"}
    
    # Регистрация нового
    new_token = secrets.token_hex(32)
    cursor.execute("INSERT INTO users (username, token) VALUES (?, ?)", (username, new_token))
    conn.commit()
    return {"token": new_token, "msg": "Registered"}

@app.post("/api/sync/push")
async def push_data(data: SyncPayload, user_id: str = Depends(verify_token)):
    payload = data.payload
    
    fields = []
    values = []
    for key in ["bookmarks", "settings", "vault"]:
        if key in payload:
            fields.append(f"{key} = ?")
            values.append(payload[key])
            
    if not fields:
        return {"status": "no_data_updated"}

    values.append(user_id)
    query = f"UPDATE sync_data SET {', '.join(fields)}, last_sync = CURRENT_TIMESTAMP WHERE user_id = ?"
    
    cursor.execute(query, values)
    if cursor.rowcount == 0:
        cols = ", ".join(payload.keys())
        placeholders = ", ".join(["?"] * len(payload))
        insert_values = list(payload.values())
        insert_values.insert(0, user_id)
        cursor.execute(f"INSERT INTO sync_data (user_id, {cols}) VALUES (?, {placeholders})", insert_values)
        
    conn.commit()
    return {"status": "success"}

@app.get("/api/sync/pull")
async def pull_data(user_id: str = Depends(verify_token)):
    cursor.execute("SELECT bookmarks, settings, vault FROM sync_data WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        return {"payload": {}}
    return {"payload": {"bookmarks": row[0], "settings": row[1], "vault": row[2]}}
