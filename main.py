import os
import random
import uuid
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response, Cookie, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from pydantic import BaseModel
import jwt
import aiosqlite
from passlib.context import CryptContext
from dotenv import load_dotenv

load_dotenv()

DB_NAME = os.getenv("DB_NAME", "/data/platform_data.db")
SECRET_KEY = os.getenv("SECRET_KEY", "fallback_secret_key_please_change_in_production")
ALGORITHM = "HS256"

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
ADMIN_EMAIL = "qureshidawood1505@gmail.com"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def init_db():
    os.makedirs(os.path.dirname(DB_NAME), exist_ok=True)
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("PRAGMA busy_timeout = 5000")
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE,
                phone TEXT UNIQUE,
                password TEXT,
                role TEXT DEFAULT 'owner',
                otp_code TEXT,
                pin_code TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS businesses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER,
                name TEXT,
                category TEXT DEFAULT 'Restaurant / Cafe',
                google_link TEXT,
                unique_link TEXT UNIQUE,
                status TEXT DEFAULT 'pending',
                positive_tags TEXT DEFAULT 'Fast Service,Friendly Staff,Clean,Great Ambiance,Value for Money',
                negative_tags TEXT DEFAULT 'Slow Service,Rude Staff,Dirty,Overpriced,Poor Quality',
                FOREIGN KEY(owner_id) REFERENCES users(id)
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                business_id INTEGER,
                customer_name TEXT,
                rating INTEGER,
                tags TEXT,
                feedback_text TEXT,
                ai_draft TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        async with db.execute("SELECT id FROM users WHERE email = ?", (ADMIN_EMAIL,)) as cursor:
            if not await cursor.fetchone():
                hashed_pw = pwd_context.hash('admin123')
                await db.execute("INSERT INTO users (email, password, role) VALUES (?, ?, 'admin')", 
                               (ADMIN_EMAIL, hashed_pw))
        
        await db.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(title="ReviewPlatform API", lifespan=lifespan)

def is_valid_email(email: str) -> bool:
    return bool(re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email))

def is_valid_phone(phone: str) -> bool:
    return bool(re.match(r"^\+?[0-9]{10,15}$", phone))

def send_otp_sync(to_identifier: str, otp_code: str, is_email: bool):
    if is_email:
        if not SMTP_USER or not SMTP_PASS:
            print(f"\n{'='*40}\n[MOCK EMAIL OTP] Code for {to_identifier} is: {otp_code}\n{'='*40}\n")
            return
        try:
            msg = MIMEMultipart()
            msg['From'] = SMTP_USER
            msg['To'] = to_identifier
            msg['Subject'] = "ReviewPlatform - Verification Code"
            msg.attach(MIMEText(f"Your 6-digit OTP code is: {otp_code}", 'plain'))
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
            server.quit()
        except Exception as e:
            print(f"Failed to send email: {e}")
            print(f"\n{'='*40}\n[EMERGENCY EMAIL OTP] Code for {to_identifier} is: {otp_code}\n{'='*40}\n")
    else:
        print(f"\n{'='*40}\n[MOCK SMS OTP] Code for phone {to_identifier} is: {otp_code}\n{'='*40}\n")

class RegisterOTPReq(BaseModel):
    identifier: str

class RegisterVerifyReq(BaseModel):
    identifier: str
    otp: str
    pin: Optional[str] = ""
    business_name: str
    category: str
    google_link: str

class LoginRequest(BaseModel):
    identifier: str
    password: Optional[str] = None
    otp: Optional[str] = None
    pin: Optional[str] = None

class SetPinRequest(BaseModel):
    pin: str

class OTPRequest(BaseModel):
    identifier: str

class BusinessCreate(BaseModel):
    name: str
    category: str
    google_link: str

class TagUpdate(BaseModel):
    business_id: int
    positive_tags: str
    negative_tags: str

class ReviewSubmit(BaseModel):
    business_link: str
    customer_name: str
    rating: int
    tags: List[str]
    feedback_text: Optional[str] = ""
    ai_draft: Optional[str] = ""

class BusinessToggle(BaseModel):
    business_id: int
    status: str

class AdminChangePassword(BaseModel):
    old_password: str
    new_password: str

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(auth_token: Optional[str] = Cookie(None)):
    if not auth_token: return None
    try:
        payload = jwt.decode(auth_token, SECRET_KEY, algorithms=[ALGORITHM])
        return {"id": payload.get("sub"), "role": payload.get("role")}
    except jwt.PyJWTError:
        return None

@app.get("/", response_class=FileResponse)
async def serve_index(request: Request, auth_token: Optional[str] = Cookie(None)):
    user = get_current_user(auth_token)
    if user:
        return RedirectResponse(url="/admin" if user["role"] == "admin" else "/dashboard")
    return FileResponse("login.html")

@app.get("/register", response_class=FileResponse)
async def serve_register(request: Request):
    return FileResponse("register.html")

@app.get("/dashboard", response_class=FileResponse)
async def serve_dashboard(request: Request, auth_token: Optional[str] = Cookie(None)):
    user = get_current_user(auth_token)
    if not user or user["role"] == "admin": return RedirectResponse(url="/")
    return FileResponse("dashboard.html")

@app.get("/admin", response_class=FileResponse)
async def serve_admin(request: Request, auth_token: Optional[str] = Cookie(None)):
    user = get_current_user(auth_token)
    if not user or user["role"] != "admin": return RedirectResponse(url="/")
    return FileResponse("admin.html")

@app.get("/review/{unique_link}", response_class=FileResponse)
async def serve_customer_review_ui(unique_link: str):
    return FileResponse("review.html")

@app.post("/api/auth/register-otp")
async def register_request_otp(req: RegisterOTPReq, background_tasks: BackgroundTasks):
    is_email = is_valid_email(req.identifier)
    is_phone = is_valid_phone(req.identifier)
    if not is_email and not is_phone:
        raise HTTPException(status_code=400, detail="Invalid email or phone format")
    
    otp_code = str(random.randint(100000, 999999))
    
    async with aiosqlite.connect(DB_NAME, timeout=10.0) as db:
        col = "email" if is_email else "phone"
        async with db.execute(f"SELECT id FROM users WHERE {col} = ?", (req.identifier,)) as cursor:
            if not await cursor.fetchone():
                await db.execute(f"INSERT INTO users ({col}, role, otp_code) VALUES (?, 'owner', ?)", (req.identifier, otp_code))
            else:
                await db.execute(f"UPDATE users SET otp_code = ? WHERE {col} = ?", (otp_code, req.identifier))
        await db.commit()
    
    background_tasks.add_task(send_otp_sync, req.identifier, otp_code, is_email)
    return {"message": "OTP sent."}

@app.post("/api/auth/register-verify")
async def register_verify(req: RegisterVerifyReq):
    is_email = is_valid_email(req.identifier)
    col = "email" if is_email else "phone"
    
    async with aiosqlite.connect(DB_NAME, timeout=10.0) as db:
        async with db.execute(f"SELECT id, otp_code FROM users WHERE {col} = ?", (req.identifier,)) as cursor:
            user = await cursor.fetchone()
            if not user or user[1] != req.otp:
                raise HTTPException(status_code=401, detail="Invalid OTP")
                
            owner_id = user[0]
            unique_slug = uuid.uuid4().hex[:12]
            
            pos = "Fast Service,Friendly Staff,Clean,Great Ambiance,Value for Money"
            neg = "Slow Service,Rude Staff,Dirty,Overpriced,Poor Quality"
            if req.category == "Salon / Spa":
                pos = "Professional,Relaxing,Clean,Skilled Stylist,Great Hygiene"
                neg = "Rude Staff,Unprofessional,Rushed Service,Expensive,Poor Results"
            elif req.category == "Retail / Shopping":
                pos = "Wide Variety,Helpful Staff,Good Discounts,Quality Products,Clean Store"
                neg = "Limited Stock,Rude Staff,Long Billing Queue,Expensive,Crowded"

            await db.execute(f"UPDATE users SET otp_code = NULL, pin_code = ? WHERE id = ?", (req.pin or None, owner_id))
            await db.execute("INSERT INTO businesses (owner_id, name, category, google_link, unique_link, status, positive_tags, negative_tags) VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)", 
                          (owner_id, req.business_name, req.category, req.google_link, unique_slug, pos, neg))
        await db.commit()
    return {"message": "Registration successful!"}

@app.post("/api/auth/request-otp")
async def request_otp(req: OTPRequest, background_tasks: BackgroundTasks):
    is_email = is_valid_email(req.identifier)
    col = "email" if is_email else "phone"
    
    async with aiosqlite.connect(DB_NAME, timeout=10.0) as db:
        async with db.execute(f"SELECT id FROM users WHERE {col} = ?", (req.identifier,)) as cursor:
            if not await cursor.fetchone():
                raise HTTPException(status_code=404, detail="Account not found. Please register first.")
                
        otp_code = str(random.randint(100000, 999999))
        await db.execute(f"UPDATE users SET otp_code = ? WHERE {col} = ?", (otp_code, req.identifier))
        await db.commit()
        
    background_tasks.add_task(send_otp_sync, req.identifier, otp_code, is_email)
    return {"message": "OTP sent."}

@app.post("/api/auth/login")
async def login(req: LoginRequest, response: Response):
    async with aiosqlite.connect(DB_NAME, timeout=10.0) as db:
        async with db.execute("SELECT id, role, password, otp_code, pin_code FROM users WHERE email = ? OR phone = ?", (req.identifier, req.identifier)) as cursor:
            user = await cursor.fetchone()
            if not user:
                raise HTTPException(status_code=401, detail="Invalid credentials")
                
            user_id, role, password_hash, otp_code, pin_code = user
            
            if role == "admin":
                if not pwd_context.verify(req.password, password_hash):
                    raise HTTPException(status_code=401, detail="Invalid admin password")
            else:
                if req.pin:
                    if not pin_code or pin_code != req.pin:
                        raise HTTPException(status_code=401, detail="Invalid PIN")
                else:
                    if not req.otp or req.otp != otp_code:
                        raise HTTPException(status_code=401, detail="Invalid OTP")
                    await db.execute("UPDATE users SET otp_code = NULL WHERE id = ?", (user_id,))
        await db.commit()
        
    token = create_access_token({"sub": str(user_id), "role": role})
    response.set_cookie(key="auth_token", value=token, httponly=True, max_age=7*24*60*60, samesite="lax", secure=True)
    return {"role": role}

@app.post("/api/auth/set-pin")
async def set_pin(req: SetPinRequest, auth_token: Optional[str] = Cookie(None)):
    user = get_current_user(auth_token)
    if not user or user["role"] != "owner": raise HTTPException(status_code=401, detail="Unauthorized")
    
    async with aiosqlite.connect(DB_NAME, timeout=10.0) as db:
        await db.execute("UPDATE users SET pin_code = ? WHERE id = ?", (req.pin, user["id"]))
        await db.commit()
    return {"message": "PIN updated successfully"}

@app.post("/api/auth/logout")
async def logout(response: Response):
    response.delete_cookie(key="auth_token")
    return {"message": "Logged out"}

@app.get("/api/owner/businesses")
async def get_my_businesses(auth_token: Optional[str] = Cookie(None)):
    user = get_current_user(auth_token)
    if not user or user["role"] != "owner": raise HTTPException(status_code=401, detail="Unauthorized")
    
    async with aiosqlite.connect(DB_NAME, timeout=10.0) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM businesses WHERE owner_id = ?", (user["id"],)) as cursor:
            rows = await cursor.fetchall()
    return [dict(row) for row in rows]

@app.post("/api/owner/businesses")
async def add_business_inside_dashboard(req: BusinessCreate, auth_token: Optional[str] = Cookie(None)):
    user = get_current_user(auth_token)
    if not user or user["role"] != "owner": raise HTTPException(status_code=401, detail="Unauthorized")
    
    pos = "Fast Service,Friendly Staff,Clean,Great Ambiance,Value for Money"
    neg = "Slow Service,Rude Staff,Dirty,Overpriced,Poor Quality"
    if req.category == "Salon / Spa":
        pos = "Professional,Relaxing,Clean,Skilled Stylist,Great Hygiene"
        neg = "Rude Staff,Unprofessional,Rushed Service,Expensive,Poor Results"
    elif req.category == "Retail / Shopping":
        pos = "Wide Variety,Helpful Staff,Good Discounts,Quality Products,Clean Store"
        neg = "Limited Stock,Rude Staff,Long Billing Queue,Expensive,Crowded"

    unique_slug = uuid.uuid4().hex[:12]
    async with aiosqlite.connect(DB_NAME, timeout=10.0) as db:
        await db.execute("INSERT INTO businesses (owner_id, name, category, google_link, unique_link, status, positive_tags, negative_tags) VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)", 
                      (user["id"], req.name, req.category, req.google_link, unique_slug, pos, neg))
        await db.commit()
    return {"message": "Added"}

@app.post("/api/owner/businesses/tags")
async def update_business_tags(req: TagUpdate, auth_token: Optional[str] = Cookie(None)):
    user = get_current_user(auth_token)
    if not user or user["role"] != "owner": raise HTTPException(status_code=401, detail="Unauthorized")
    
    async with aiosqlite.connect(DB_NAME, timeout=10.0) as db:
        async with db.execute("SELECT id FROM businesses WHERE id = ? AND owner_id = ?", (req.business_id, user["id"])) as cursor:
            if not await cursor.fetchone():
                raise HTTPException(status_code=403, detail="Forbidden")
                
        await db.execute("UPDATE businesses SET positive_tags = ?, negative_tags = ? WHERE id = ?", 
                         (req.positive_tags, req.negative_tags, req.business_id))
        await db.commit()
    return {"message": "Tags updated successfully"}

@app.get("/api/owner/reviews/{business_id}")
async def get_reviews_for_business(business_id: int, auth_token: Optional[str] = Cookie(None)):
    user = get_current_user(auth_token)
    if not user or user["role"] != "owner": raise HTTPException(status_code=401, detail="Unauthorized")
    
    async with aiosqlite.connect(DB_NAME, timeout=10.0) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT id FROM businesses WHERE id = ? AND owner_id = ?", (business_id, user["id"])) as cursor:
            if not await cursor.fetchone():
                raise HTTPException(status_code=403, detail="Forbidden")
        async with db.execute("SELECT * FROM reviews WHERE business_id = ? ORDER BY timestamp DESC", (business_id,)) as cursor:
            rows = await cursor.fetchall()
    return [dict(row) for row in rows]

@app.post("/api/admin/change-password")
async def change_admin_password(req: AdminChangePassword, auth_token: Optional[str] = Cookie(None)):
    user = get_current_user(auth_token)
    if not user or user["role"] != "admin": raise HTTPException(status_code=401, detail="Unauthorized")
    
    async with aiosqlite.connect(DB_NAME, timeout=10.0) as db:
        async with db.execute("SELECT password FROM users WHERE id = ?", (user["id"],)) as cursor:
            row = await cursor.fetchone()
            if not row: raise HTTPException(status_code=404, detail="Admin not found")
            if not pwd_context.verify(req.old_password, row[0]):
                raise HTTPException(status_code=400, detail="Incorrect current password")
            hashed_pw = pwd_context.hash(req.new_password)
            await db.execute("UPDATE users SET password = ? WHERE id = ?", (hashed_pw, user["id"]))
            await db.commit()
    return {"message": "Password updated successfully"}

@app.get("/api/admin/businesses")
async def get_all_businesses(auth_token: Optional[str] = Cookie(None)):
    user = get_current_user(auth_token)
    if not user or user["role"] != "admin": raise HTTPException(status_code=401, detail="Unauthorized")
    
    async with aiosqlite.connect(DB_NAME, timeout=10.0) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('''
            SELECT b.*, COALESCE(u.email, u.phone) as owner_email 
            FROM businesses b 
            JOIN users u ON b.owner_id = u.id
        ''') as cursor:
            rows = await cursor.fetchall()
    return [dict(row) for row in rows]

@app.post("/api/admin/businesses/toggle")
async def toggle_business(req: BusinessToggle, auth_token: Optional[str] = Cookie(None)):
    user = get_current_user(auth_token)
    if not user or user["role"] != "admin": raise HTTPException(status_code=401, detail="Unauthorized")
    
    async with aiosqlite.connect(DB_NAME, timeout=10.0) as db:
        await db.execute("UPDATE businesses SET status = ? WHERE id = ?", (req.status, req.business_id))
        await db.commit()
    return {"message": f"Business {req.status}"}

@app.get("/api/admin/reviews")
async def get_all_reviews(auth_token: Optional[str] = Cookie(None)):
    user = get_current_user(auth_token)
    if not user or user["role"] != "admin": raise HTTPException(status_code=401, detail="Unauthorized")
    
    async with aiosqlite.connect(DB_NAME, timeout=10.0) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('''
            SELECT r.*, b.name as business_name 
            FROM reviews r 
            JOIN businesses b ON r.business_id = b.id 
            ORDER BY r.timestamp DESC
        ''') as cursor:
            rows = await cursor.fetchall()
    return [dict(row) for row in rows]

@app.get("/api/business/public/{unique_link}")
async def get_business_public(unique_link: str):
    async with aiosqlite.connect(DB_NAME, timeout=10.0) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT id, name, category, google_link, status, unique_link, positive_tags, negative_tags FROM businesses WHERE unique_link = ?", (unique_link,)) as cursor:
            row = await cursor.fetchone()
    if not row: raise HTTPException(status_code=404, detail="Not found")
    if row['status'] != 'approved': raise HTTPException(status_code=403, detail="Disabled or Pending")
    return dict(row)

@app.post("/api/reviews/submit")
async def submit_review(req: ReviewSubmit):
    async with aiosqlite.connect(DB_NAME, timeout=10.0) as db:
        async with db.execute("SELECT id FROM businesses WHERE unique_link = ?", (req.business_link,)) as cursor:
            row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Business not found")
        b_id = row[0]
        tags_joined = ",".join(req.tags)
        await db.execute(
            "INSERT INTO reviews (business_id, customer_name, rating, tags, feedback_text, ai_draft) VALUES (?, ?, ?, ?, ?, ?)",
            (b_id, req.customer_name, req.rating, tags_joined, req.feedback_text, req.ai_draft)
        )
        await db.commit()
    return {"status": "success"}

@app.post("/api/ai/generate-review")
async def generate_ai_review(req: dict):
    b_name = req.get('business_name', 'this establishment')
    name = req.get('customer_name', 'A happy customer')
    tags = req.get('tags', [])
    lang = req.get('lang', 'en')
    
    if lang == 'hi':
        intros = [f"मैंने हाल ही में {b_name} का दौरा किया और यह एक शानदार अनुभव था।", f"{b_name} के लिए पाँच सितारे!"]
        middles = [f"उन्होंने वास्तव में {', '.join(tags)} को बेहतरीन तरीके से निभाया।"] if tags else []
        outros = ["अत्यधिक अनुशंसित!", "निश्चित रूप से जल्द ही वापस आऊंगा।"]
        review = random.choice(intros) + (" " + random.choice(middles) if middles else "") + " " + random.choice(outros)
        return {"review": review}
    elif lang == 'mr':
        intros = [f"मी अलीकडेच {b_name} ला भेट दिली आणि हा एक अद्भुत अनुभव होता.", f"{b_name} साठी पाच तारे!"]
        middles = [f"त्यांनी खरोखरच {', '.join(tags)} उत्तम प्रकारे हाताळले."] if tags else []
        outros = ["अत्यंत शिफारस केलेले!", "नक्कीच लवकरच परत येईल."]
        review = random.choice(intros) + (" " + random.choice(middles) if middles else "") + " " + random.choice(outros)
        return {"review": review}
    else:
        intros = [f"I recently visited {b_name} and it was a wonderful experience.", f"Five stars for {b_name}!"]
        middles = [f"They completely nailed the {', '.join(tags)}."] if tags else []
        outros = ["Highly recommended!", "Will definitely be coming back soon."]
        review = random.choice(intros) + (" " + random.choice(middles) if middles else "") + " " + random.choice(outros)
        return {"review": review}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
