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

# Load environment variables from .env file
load_dotenv()

DB_NAME = os.getenv("DB_NAME", "platform_data.db")
SECRET_KEY = os.getenv("SECRET_KEY", "fallback_secret_key_please_change_in_production")
ALGORITHM = "HS256"

# Email Configuration
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
ADMIN_EMAIL = "qureshidawood1505@gmail.com"

# Secure password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# -----------------
# 1. DATABASE SETUP
# -----------------
async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("PRAGMA busy_timeout = 5000")
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE,
                password TEXT,
                role TEXT DEFAULT 'owner',
                otp_code TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS businesses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER,
                name TEXT,
                google_link TEXT,
                unique_link TEXT UNIQUE,
                status TEXT DEFAULT 'pending',
                positive_tags TEXT DEFAULT 'Fast Service,Friendly Staff,Clean,Great Ambiance,Value for Money,Quality Products,Professional',
                negative_tags TEXT DEFAULT 'Slow Service,Rude Staff,Dirty,Overpriced,Poor Quality,Unprofessional',
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

# -----------------
# 2. UTILS, MODELS & AUTH
# -----------------
def is_valid_email(email: str) -> bool:
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(pattern, email))

def send_otp_email_sync(to_email: str, otp_code: str):
    if not SMTP_USER or not SMTP_PASS:
        print(f"\n{'='*40}\n[MOCK EMAIL] OTP for {to_email} is: {otp_code}\n{'='*40}\n")
        return
        
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = to_email
        msg['Subject'] = "ReviewPlatform - Your Verification Code"
        
        body = f"Hello,\n\nYour 6-digit OTP code is: {otp_code}\n\nPlease enter this code to securely log in.\n\nThank you!"
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")
        # EMERGENCY BYPASS: Print the OTP to the Railway console so you aren't locked out!
        print(f"\n{'='*40}\n[EMERGENCY OTP] Code for {to_email} is: {otp_code}\n{'='*40}\n")


class RegisterOTPReq(BaseModel):
    email: str
class RegisterVerifyReq(BaseModel):
    email: str
    otp: str
    business_name: str
    google_link: str
class LoginRequest(BaseModel):
    email: str
    password: Optional[str] = None
    otp: Optional[str] = None
class OTPRequest(BaseModel):
    email: str
class BusinessCreate(BaseModel):
    name: str
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

# -----------------
# 3. HTML ROUTES
# -----------------
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
    if not user or user["role"] != "owner": return RedirectResponse(url="/")
    return FileResponse("dashboard.html")

@app.get("/admin", response_class=FileResponse)
async def serve_admin(request: Request, auth_token: Optional[str] = Cookie(None)):
    user = get_current_user(auth_token)
    if not user or user["role"] != "admin": return RedirectResponse(url="/")
    return FileResponse("admin.html")

@app.get("/review/{unique_link}", response_class=FileResponse)
async def serve_customer_review_ui(unique_link: str):
    return FileResponse("review.html")

# -----------------
# 4. API ROUTES
# -----------------
@app.post("/api/auth/register-otp")
async def register_request_otp(req: RegisterOTPReq, background_tasks: BackgroundTasks):
    if not is_valid_email(req.email): raise HTTPException(status_code=400, detail="Invalid email format")
    if req.email == ADMIN_EMAIL: raise HTTPException(status_code=400, detail="Cannot register as admin")
    
    otp_code = str(random.randint(100000, 999999))

    async with aiosqlite.connect(DB_NAME, timeout=10.0) as db:
        async with db.execute("SELECT id FROM users WHERE email = ?", (req.email,)) as cursor:
            if not await cursor.fetchone():
                await db.execute("INSERT INTO users (email, role, otp_code) VALUES (?, 'owner', ?)", (req.email, otp_code))
            else:
                await db.execute("UPDATE users SET otp_code = ? WHERE email = ?", (otp_code, req.email))
        await db.commit()
    
    background_tasks.add_task(send_otp_email_sync, req.email, otp_code)
    return {"message": "OTP sent."}

@app.post("/api/auth/register-verify")
async def register_verify(req: RegisterVerifyReq):
    async with aiosqlite.connect(DB_NAME, timeout=10.0) as db:
        async with db.execute("SELECT id, otp_code FROM users WHERE email = ?", (req.email,)) as cursor:
            user = await cursor.fetchone()
            if not user or user[1] != req.otp:
                raise HTTPException(status_code=401, detail="Invalid OTP")
                
            owner_id = user[0]
            unique_slug = uuid.uuid4().hex[:12]
            await db.execute("UPDATE users SET otp_code = NULL WHERE id = ?", (owner_id,))
            await db.execute("INSERT INTO businesses (owner_id, name, google_link, unique_link, status) VALUES (?, ?, ?, ?, 'pending')", 
                          (owner_id, req.business_name, req.google_link, unique_slug))
        await db.commit()
    return {"message": "Registration successful!"}

@app.post("/api/auth/request-otp")
async def request_otp(req: OTPRequest, background_tasks: BackgroundTasks):
    if not is_valid_email(req.email): raise HTTPException(status_code=400, detail="Invalid email format")
    if req.email == ADMIN_EMAIL: raise HTTPException(status_code=400, detail="Admin uses password, not OTP.")
    
    async with aiosqlite.connect(DB_NAME, timeout=10.0) as db:
        async with db.execute("SELECT id FROM users WHERE email = ?", (req.email,)) as cursor:
            if not await cursor.fetchone():
                raise HTTPException(status_code=404, detail="Email not found. Please register first.")
                
        otp_code = str(random.randint(100000, 999999))
        await db.execute("UPDATE users SET otp_code = ? WHERE email = ?", (otp_code, req.email))
        await db.commit()
        
    background_tasks.add_task(send_otp_email_sync, req.email, otp_code)
    return {"message": "OTP sent."}

@app.post("/api/auth/login")
async def login(req: LoginRequest, response: Response):
    if not is_valid_email(req.email): raise HTTPException(status_code=400, detail="Invalid email format")
    
    async with aiosqlite.connect(DB_NAME, timeout=10.0) as db:
        async with db.execute("SELECT id, role, password, otp_code FROM users WHERE email = ?", (req.email,)) as cursor:
            user = await cursor.fetchone()
            if not user:
                raise HTTPException(status_code=401, detail="Invalid credentials")
                
            user_id, role, password_hash, otp_code = user
            if role == "admin":
                if not pwd_context.verify(req.password, password_hash):
                    raise HTTPException(status_code=401, detail="Invalid admin password")
            else:
                if not req.otp or req.otp != otp_code:
                    raise HTTPException(status_code=401, detail="Invalid OTP")
                await db.execute("UPDATE users SET otp_code = NULL WHERE id = ?", (user_id,))
        await db.commit()
        
    token = create_access_token({"sub": str(user_id), "role": role})
    response.set_cookie(key="auth_token", value=token, httponly=True, max_age=7*24*60*60, samesite="lax", secure=True)
    return {"role": role}

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
    
    unique_slug = uuid.uuid4().hex[:12]
    async with aiosqlite.connect(DB_NAME, timeout=10.0) as db:
        await db.execute("INSERT INTO businesses (owner_id, name, google_link, unique_link, status) VALUES (?, ?, ?, ?, 'pending')", 
                      (user["id"], req.name, req.google_link, unique_slug))
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
            SELECT b.*, u.email as owner_email 
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
        async with db.execute("SELECT id, name, google_link, status, unique_link, positive_tags, negative_tags FROM businesses WHERE unique_link = ?", (unique_link,)) as cursor:
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
        intros = [
            f"मैंने हाल ही में {b_name} का दौरा किया और यह एक शानदार अनुभव था।",
            f"{b_name} के लिए पाँच सितारे!",
            f"मैं {b_name} के बारे में पर्याप्त अच्छी बातें नहीं कह सकता।"
        ]
        middles = []
        if tags:
            tag_str = ", ".join(tags)
            middles = [
                f"उन्होंने वास्तव में {tag_str} को बेहतरीन तरीके से निभाया।",
                f"मैं {tag_str} से पूरी तरह प्रभावित था।"
            ]
        outros = [
            f"अत्यधिक अनुशंसित! - {name}",
            f"निश्चित रूप से जल्द ही वापस आऊंगा। - {name}",
            f"10/10 दोबारा आना चाहूंगा। - {name}"
        ]
        review = random.choice(intros)
        if middles: review += " " + random.choice(middles)
        review += " " + random.choice(outros)
        return {"review": review}

    elif lang == 'mr':
        intros = [
            f"मी अलीकडेच {b_name} ला भेट दिली आणि हा एक अद्भुत अनुभव होता.",
            f"{b_name} साठी पाच तारे!",
            f"मी {b_name} बद्दल कितीही सांगू तितके कमी आहे."
        ]
        middles = []
        if tags:
            tag_str = ", ".join(tags)
            middles = [
                f"त्यांनी खरोखरच {b_name} मध्ये {tag_str} उत्तम प्रकारे हाताळले.",
                f"मला {tag_str} खूप आवडले."
            ]
        outros = [
            f"अत्यंत शिफारस केलेले! - {name}",
            f"नक्कीच लवकरच परत येईल. - {name}",
            f"पुन्हा नक्की भेट देईन. - {name}"
        ]
        review = random.choice(intros)
        if middles: review += " " + random.choice(middles)
        review += " " + random.choice(outros)
        return {"review": review}

    else:
        intros = [
            f"I recently visited {b_name} and it was a wonderful experience.",
            f"Five stars for {b_name}!",
            f"Can't say enough good things about {b_name}.",
            f"My new favorite spot is definitely {b_name}.",
            f"Had a really solid experience at {b_name} today.",
            f"Just left {b_name} and I am so impressed."
        ]
        
        middles = []
        if tags:
            tag_str = " and ".join([", ".join(tags[:-1]), tags[-1]] if len(tags) > 1 else tags)
            middles = [
                f"They completely nailed the {tag_str}.",
                f"I was really blown away by the {tag_str}.",
                f"If you're looking for great {tag_str}, this is the place to go.",
                f"The {tag_str} made the whole visit totally worth it.",
                f"Special shoutout to the team for the excellent {tag_str}!"
            ]
            
        outros = [
            f"Highly recommended! - {name}",
            f"Will definitely be coming back soon. - {name}",
            f"Check it out if you're in the area! - {name}",
            f"Thanks to the team for a great time. - {name}",
            f"10/10 would visit again. - {name}"
        ]
        
        review = random.choice(intros)
        if middles:
            review += " " + random.choice(middles)
        review += " " + random.choice(outros)
        
        return {"review": review}
=======
    intros = [
        f"I recently visited {b_name} and it was a wonderful experience.",
        f"Five stars for {b_name}!",
        f"Can't say enough good things about {b_name}."
    ]
    
    middles = []
    if tags:
        tag_str = " and ".join([", ".join(tags[:-1]), tags[-1]] if len(tags) > 1 else tags)
        middles = [
            f"They completely nailed the {tag_str}.",
            f"If you're looking for great {tag_str}, this is the place to go."
        ]
        
    outros = [
        f"Highly recommended! - {name}",
        f"Will definitely be coming back soon. - {name}",
        f"10/10 would visit again. - {name}"
    ]
    
    review = random.choice(intros)
    if middles:
        review += " " + random.choice(middles)
    review += " " + random.choice(outros)
    
    return {"review": review}
>>>>>>> 27556739546df7581e81e2d92a6d0a816ccdbe07

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
