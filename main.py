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

# Use DB_NAME from environment or fallback safely to a local relative file
DB_NAME = os.getenv("DB_NAME", "platform_data.db")
SECRET_KEY = os.getenv("SECRET_KEY", "fallback_secret_key_please_change_in_production")
ALGORITHM = "HS256"

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
ADMIN_EMAIL = "qureshidawood1505@gmail.com"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

CATEGORY_PRESETS = {
    "Restaurant / Cafe": {
        "pos": "Great Food,Fast Service,Clean,Friendly Staff,Good Ambiance,Value for Money,Fresh Ingredients,Tasty,Cozy Vibe,Great Portions,Authentic Taste,Hygienic,Prompt Delivery,Well Prepared,Scenic View",
        "neg": "Slow Service,Rude Staff,Cold Food,Dirty Tables,Overpriced,Small Portions,Noisy,Bland Taste,Poor Quality,Unhygienic,Stale Food,Wrong Order,Uncooked,Bad Smell,Cramped Seating"
    },
    "Salon / Spa": {
        "pos": "Professional,Relaxing,Clean,Skilled Stylist,Great Hygiene,Friendly Staff,Value for Money,Good Products,Punctual,Soothing Vibe,Expert Advice,Gentle Massage,Refreshing,Great Haircut,Skin Glowing",
        "neg": "Rude Staff,Unprofessional,Rushed Service,Dirty Tools,Expensive,Poor Results,Delayed Appointment,Unclean,Bad Haircut,Noisy,Skin Irritation,Wrong Treatment,Rough Handling,Unsanitary,Inexperienced"
    },
    "Retail / Shopping": {
        "pos": "Wide Variety,Helpful Staff,Good Discounts,Quality Products,Clean Store,Easy Checkout,Original Items,Great Exchange Policy,Spacious,Value for Money,Trendy Collection,Well Stocked,Fast Billing,Polite Cashier,Ample Parking",
        "neg": "Limited Stock,Rude Staff,Long Billing Queue,Expensive,Crowded,No Exchange,Damaged Items,Unhelpful,Messy Store,No Discounts,Broken Display,Expired Items,Hidden Charges,Poor Lighting,Long Waiting"
    },
    "Hotel / Resort": {
        "pos": "Comfortable Rooms,Luxurious Ambiance,Courteous Staff,Scenic Views,Clean Swimming Pool,Delicious Breakfast,Spacious Suite,Hygienic Bathrooms,Prompt Room Service,Peaceful Environment,Valet Parking,Great Hospitality,Modern Amenities,Secure Property,Fast Check-in",
        "neg": "Unclean Rooms,Rude Reception,No Hot Water,Slow Wi-Fi,Stains on Bedsheets,Bad Odor,Noisy Location,Expensive Food,Pests Found,Poor Maintenance,Late Check-in,Broken AC,Uncomfortable Bed,Bad Lighting,Rude Staff"
    },
    "Gym / Fitness Studio": {
        "pos": "Modern Equipment,Knowledgeable Trainers,Clean Changing Rooms,Motivating Environment,Spacious Workout Area,Flexible Timings,Hygienic Showers,Good Ventilation,Great Playlist,Effective Programs,Proper Sanitization,Friendly Community,Ample Weights,Locker Facility,Personal Attention",
        "neg": "Broken Machines,Overcrowded,Unprofessional Trainers,Dirty Mats,No AC,Bad Smell,Unfriendly Staff,Hidden Fees,No Parking,Outdated Gear,Slippery Floor,Loud Music,No Lockers,Unclean Showers,Poor Guidance"
    },
    "Healthcare / Clinic": {
        "pos": "Caring Doctor,Clean Clinic,Minimal Waiting Time,Friendly Nurses,Accurate Diagnosis,Affordable Fees,Polite Staff,Hygienic Instruments,Easy Booking,Clear Explanation,Well Equipped,Emergency Care,Calm Atmosphere,Reliable Pharmacy,Follow-up Care",
        "neg": "Rude Receptionist,Long Waiting Hours,Expensive Consultation,Dirty Waiting Room,Incorrect Billing,Uncaring Doctor,Unsanitary,Misdiagnosis,No Parking,Rushed Checkup,Outdated Tools,No Emergency Help,Unhelpful Staff,Poor Hygiene,No Follow-up"
    },
    "Auto Repair / Garage": {
        "pos": "Honest Mechanics,Fair Pricing,Fast Repair,Genuine Spare Parts,Clean Workshop,Expert Diagnosis,Reliable Service,Clear Quotation,Free Pickup,Punctual Delivery,Polite Owner,Good Advice,Warranty Offered,Well Equipped,Quality Work",
        "neg": "Overcharging,Delayed Delivery,Fake Parts,Rude Mechanic,Unresolved Issues,Messy Garage,Hidden Costs,Poor Workmanship,No Warranty,Ignorant Staff,No Invoice,Damaged Car,Rough Handling,Unprofessional,Ignored Instructions"
    },
    "Dental Clinic": {
        "pos": "Gentle Dentist,Painless Procedure,Clean Clinic,Modern Technology,Friendly Staff,Affordable Treatment,Hygienic Tools,Clear Guidance,No Waiting,Comfortable Chair,Polite Hygienist,Emergency Support,Sterile Environment,Great Results,Detailed Explanation",
        "neg": "Rough Handling,Severe Pain,Unclean Clinic,Extremely Expensive,Rude Dentist,Incorrect Procedure,Outdated Equipment,Long Delay,Hidden Charges,Unprofessional Nurses,Sterilization Issues,Bad Smell,No Emergency Care,Bleeding,Poor Aftercare"
    },
    "Real Estate Agency": {
        "pos": "Transparent Dealings,Professional Agents,Great Property Options,Helpful Support,Punctual Visits,Honest Advice,Smooth Documentation,Polite Staff,Good Negotiation,Verified Listings,Quick Response,Market Knowledge,Trustworthy,Clear Terms,End-to-End Service",
        "neg": "Hidden Brokerage,Pushy Agents,Fake Listings,Delayed Papers,Rude Staff,Unprofessional,Unkept Promises,Misleading Info,Poor Follow-up,No Communication,Legal Issues,Wasted Time,High Commission,Unresponsive,Unreliable"
    },
    "Bakery / Confectionery": {
        "pos": "Freshly Baked,Delicious Cakes,Mouthwatering Pastries,Hygienic Display,Friendly Baker,Custom Design,Reasonable Prices,Soft Bread,Great Aroma,Prompt Packing,Awesome Taste,Variety of Flavors,Clean Store,Polite Staff,Eggless Options",
        "neg": "Stale Items,Dry Cake,Overpriced,Rude Staff,Wrong Order,Too Sweet,Melted Frosting,Unhygienic Display,Broken Packaging,Bad Odor,Hair Found,Limited Options,Late Delivery,Poor Quality,Stale Bread"
    }
}

async def init_db():
    db_dir = os.path.dirname(DB_NAME)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
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
                positive_tags TEXT DEFAULT '',
                negative_tags TEXT DEFAULT '',
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
    category: Optional[str] = "Restaurant / Cafe"
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
    category: Optional[str] = "Restaurant / Cafe"
    google_link: str

class TagUpdate(BaseModel):
    business_id: int
    positive_tags: List[str]
    negative_tags: List[str]

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
            
            cat = req.category or "Restaurant / Cafe"
            preset = CATEGORY_PRESETS.get(cat, CATEGORY_PRESETS["Restaurant / Cafe"])
            pos_list = [t.strip() for t in preset["pos"].split(',') if t.strip()][:5]
            neg_list = [t.strip() for t in preset["neg"].split(',') if t.strip()][:5]
            pos = ",".join(pos_list)
            neg = ",".join(neg_list)

            await db.execute(f"UPDATE users SET otp_code = NULL, pin_code = ? WHERE id = ?", (req.pin or None, owner_id))
            await db.execute(
                "INSERT INTO businesses (owner_id, name, category, google_link, unique_link, status, positive_tags, negative_tags) VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)", 
                (owner_id, req.business_name, cat, req.google_link, unique_slug, pos, neg)
            )
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
    response.delete_cookie(key="auth_token", path="/", samesite="lax", secure=True, httponly=True)
    return {"message": "Logged out"}

@app.get("/api/owner/businesses")
async def get_my_businesses(auth_token: Optional[str] = Cookie(None)):
    user = get_current_user(auth_token)
    if not user or user["role"] != "owner": raise HTTPException(status_code=401, detail="Unauthorized")
    
    async with aiosqlite.connect(DB_NAME, timeout=10.0) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM businesses WHERE owner_id = ?", (user["id"],)) as cursor:
            rows = await cursor.fetchall()
            
        result = []
        for row in rows:
            b_dict = dict(row)
            b_dict['positive_tags'] = [t.strip() for t in b_dict['positive_tags'].split(',') if t.strip()]
            b_dict['negative_tags'] = [t.strip() for t in b_dict['negative_tags'].split(',') if t.strip()]
            
            preset = CATEGORY_PRESETS.get(b_dict['category'], CATEGORY_PRESETS["Restaurant / Cafe"])
            b_dict['preset_positive'] = [t.strip() for t in preset['pos'].split(',')]
            b_dict['preset_negative'] = [t.strip() for t in preset['neg'].split(',')]
            result.append(b_dict)
    return result

@app.post("/api/owner/businesses")
async def add_business_inside_dashboard(req: BusinessCreate, auth_token: Optional[str] = Cookie(None)):
    user = get_current_user(auth_token)
    if not user or user["role"] != "owner": raise HTTPException(status_code=401, detail="Unauthorized")
    
    cat = req.category or "Restaurant / Cafe"
    preset = CATEGORY_PRESETS.get(cat, CATEGORY_PRESETS["Restaurant / Cafe"])
    pos_list = [t.strip() for t in preset["pos"].split(',') if t.strip()][:5]
    neg_list = [t.strip() for t in preset["neg"].split(',') if t.strip()][:5]
    pos = ",".join(pos_list)
    neg = ",".join(neg_list)

    unique_slug = uuid.uuid4().hex[:12]
    async with aiosqlite.connect(DB_NAME, timeout=10.0) as db:
        await db.execute("INSERT INTO businesses (owner_id, name, category, google_link, unique_link, status, positive_tags, negative_tags) VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)", 
                      (user["id"], req.name, cat, req.google_link, unique_slug, pos, neg))
        await db.commit()
    return {"message": "Added"}

@app.post("/api/owner/businesses/tags")
async def update_business_tags(req: TagUpdate, auth_token: Optional[str] = Cookie(None)):
    user = get_current_user(auth_token)
    if not user or user["role"] != "owner": raise HTTPException(status_code=401, detail="Unauthorized")
    
    pos_joined = ",".join(req.positive_tags)
    neg_joined = ",".join(req.negative_tags)
    
    async with aiosqlite.connect(DB_NAME, timeout=10.0) as db:
        async with db.execute("SELECT id FROM businesses WHERE id = ? AND owner_id = ?", (req.business_id, user["id"])) as cursor:
            if not await cursor.fetchone():
                raise HTTPException(status_code=403, detail="Forbidden")
                
        await db.execute("UPDATE businesses SET positive_tags = ?, negative_tags = ? WHERE id = ?", 
                         (pos_joined, neg_joined, req.business_id))
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
    
    b_dict = dict(row)
    b_dict['positive_tags'] = [t.strip() for t in b_dict['positive_tags'].split(',') if t.strip()]
    b_dict['negative_tags'] = [t.strip() for t in b_dict['negative_tags'].split(',') if t.strip()]
    
    preset = CATEGORY_PRESETS.get(b_dict['category'], CATEGORY_PRESETS["Restaurant / Cafe"])
    b_dict['preset_positive'] = [t.strip() for t in preset['pos'].split(',')]
    b_dict['preset_negative'] = [t.strip() for t in preset['neg'].split(',')]
    
    return b_dict

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
    category = req.get('category', 'Restaurant / Cafe')
    tags = req.get('tags', [])
    lang = req.get('lang', 'en')
    
    cat_intros = {
        "Restaurant / Cafe": {
            "en": [
                f"I recently visited {b_name} and the food and ambiance were incredible.",
                f"Had a wonderful dining experience at {b_name} today with outstanding flavors.",
                f"Absolute favorite spot in town! {b_name} never fails to impress with great quality.",
                f"Came to {b_name} for lunch and everything from the service to the dishes was top-notch.",
                f"The culinary delights at {b_name} are truly unmatched. Highly recommend trying their specials.",
                f"A fantastic evening spent at {b_name}. Cozy atmosphere and delicious food.",
                f"Every dish we ordered at {b_name} was cooked to perfection and served promptly.",
                f"Superb hospitality and mouthwatering dishes make {b_name} a must-visit destination.",
                f"Impressed by the cleanliness and exceptional taste at {b_name}. Will definitely return.",
                f"Dining at {b_name} was an absolute treat for the taste buds. Truly wonderful."
            ],
            "hi": [
                f"मैंने हाल ही में {b_name} का दौरा किया और यहाँ का खाना और माहौल शानदार था।",
                f"आज {b_name} में भोजन का अनुभव बहुत अच्छा रहा, बेहतरीन स्वाद।",
                f"शहर में मेरी पसंदीदा जगह! {b_name} हमेशा उच्च गुणवत्ता से प्रभावित करता है।",
                f"दोपहर के भोजन के लिए {b_name} आया और सेवा से लेकर व्यंजनों तक सब कुछ बेहतरीन था।",
                f"{b_name} में पाक कला वास्तव में बेजोड़ है।",
                f"{b_name} में एक शानदार शाम बिताई। आरामदायक माहौल और स्वादिष्ट खाना।",
                f"{b_name} पर हमने जो भी ऑर्डर किया, वह बेहतरीन तरीके से पकाया गया था।",
                f"शानदार आतिथ्य और लजीज व्यंजन {b_name} को देखने लायक बनाते हैं।",
                f"{b_name} में स्वच्छता और असाधारण स्वाद से प्रभावित हूँ।",
                f"{b_name} में भोजन करना एक अद्भुत अनुभव था।"
            ],
            "mr": [
                f"मी अलीकडेच {b_name} ला भेट दिली आणि येथील अन्न आणि वातावरण अप्रतिम होते.",
                f"आज {b_name} मध्ये जेवणाचा अनुभव खूप छान होता, उत्तम चव.",
                f"शहरातील माझे आवडते ठिकाण! {b_name} नेहमीच उत्तम गुणवत्ता देते.",
                f"दुपारच्या जेवणासाठी {b_name} ला आलो आणि सर्व काही उत्तम होते.",
                f"{b_name} मधील जेवणाची चव खरोखरच अप्रतिम आहे.",
                f"{b_name} मध्ये एक छान संध्याकाळ घालवली. आरामदायक वातावरण आणि स्वादिष्ट अन्न.",
                f"{b_name} वर ऑर्डर केलेले प्रत्येक अन्न उत्तम प्रकारे बनवले होते.",
                f"उत्कृष्ट आतिथ्य आणि चवदार पदार्थांमुळे {b_name} भेट देण्यासारखे आहे.",
                f"{b_name} मधील स्वच्छता आणि चव पाहून खूप आनंद झाला.",
                f"{b_name} मध्ये जेवणे हा एक विलक्षण अनुभव होता."
            ]
        },
        "Salon / Spa": {
            "en": [
                f"My session at {b_name} was extremely relaxing and professional.",
                f"Completely refreshed after visiting {b_name}. Outstanding service.",
                f"The staff at {b_name} are true experts. Loved the rejuvenating treatment.",
                f"Such a soothing environment at {b_name}. Highly professional stylists.",
                f"Felt so pampered and well taken care of during my visit to {b_name}.",
                f"Exceptional grooming and spa treatments at {b_name}. Worth every penny.",
                f"Clean, calming, and top-quality care at {b_name}.",
                f"My hair and skin look glowing after my appointment at {b_name}.",
                f"Absolute perfection! {b_name} provides the ultimate relaxation experience.",
                f"Professionalism at its finest. {b_name} is my go-to place now."
            ],
            "hi": [
                f"{b_name} में मेरा सत्र बेहद आरामदायक और पेशेवर था।",
                f"{b_name} जाने के बाद मैं पूरी तरह तरोताजा महसूस कर रहा हूँ। उत्कृष्ट सेवा।",
                f"{b_name} के कर्मचारी वास्तविक विशेषज्ञ हैं। कायाकल्प उपचार पसंद आया।",
                f"{b_name} में बहुत शांत वातावरण। अत्यधिक पेशेवर स्टाइलिस्ट।",
                f"{b_name} की मेरी यात्रा के दौरान बहुत अच्छा लगा।",
                f"{b_name} पर असाधारण स्पा उपचार। हर पैसे के लायक।",
                f"{b_name} में स्वच्छ, शांत और उच्च गुणवत्ता की देखभाल।",
                f"{b_name} में मेरी नियुक्ति के बाद मेरे बाल और त्वचा चमक रहे हैं।",
                f"पूर्णता! {b_name} परम विश्राम अनुभव प्रदान करता है।",
                f"{b_name} अब मेरी पसंदीदा जगह है।"
            ],
            "mr": [
                f"{b_name} मधील माझे सत्र अत्यंत आरामदायक आणि व्यावसायिक होते.",
                f"{b_name} ला भेट दिल्यानंतर एकदम फ्रेश वाटले. उत्कृष्ट सेवा.",
                f"{b_name} मधील कर्मचारी खरोखर तज्ज्ञ आहेत.",
                f"{b_name} मध्ये खूप शांत वातावरण आहे.",
                f"{b_name} मधील भेटीदरम्यान खूप छान काळजी घेतली गेली.",
                f"{b_name} वर अपवादात्मक स्पा उपचार. प्रत्येक पैशाचे मूल्य.",
                f"{b_name} मध्ये स्वच्छ आणि उच्च दर्जाची काळजी.",
                f"{b_name} मधील भेटीनंतर माझे केस आणि त्वचा चमकत आहेत.",
                f"परिपूर्णता! {b_name} अंतिम विश्रांतीचा अनुभव देते.",
                f"{b_name} हे आता माझे आवडते ठिकाण बनले आहे."
            ]
        },
        "Retail / Shopping": {
            "en": [
                f"Shopping at {b_name} was a fantastic experience with great options.",
                f"Found exactly what I needed at {b_name} with helpful staff assistance.",
                f"Amazing collection and wonderful discounts at {b_name}.",
                f"Clean store, huge variety, and smooth checkout at {b_name}.",
                f"Quality products and genuine items available at {b_name}.",
                f"Always a pleasure shopping at {b_name}. Well stocked and organized.",
                f"Polite cashiers and quick billing make {b_name} my favorite store.",
                f"Top-tier shopping experience at {b_name}. Highly recommend.",
                f"Found trendy collections and great prices at {b_name}.",
                f"Excellent customer service and wide variety at {b_name}."
            ],
            "hi": [
                f"{b_name} पर खरीदारी करना शानदार अनुभव था, बहुत अच्छे विकल्प मिले।",
                f"सहायक कर्मचारियों की मदद से मुझे {b_name} पर बिल्कुल वही मिला जिसकी तलाश थी।",
                f"{b_name} पर अद्भुत संग्रह और शानदार छूट।",
                f"{b_name} में साफ स्टोर, विशाल विविधता और आसान चेकआउट।",
                f"{b_name} पर गुणवत्तापूर्ण उत्पाद और वास्तविक वस्तुएं उपलब्ध हैं।",
                f"{b_name} पर खरीदारी करना हमेशा एक सुखद अनुभव होता है।",
                f"विनम्र कैशियर और त्वरित बिलिंग {b_name} को मेरा पसंदीदा स्टोर बनाते हैं।",
                f"{b_name} पर बेहतरीन खरीदारी अनुभव। अत्यधिक अनुशंसित।",
                f"{b_name} पर ट्रेंडी कलेक्शन और बेहतरीन कीमतें मिलीं।",
                f"{b_name} पर उत्कृष्ट ग्राहक सेवा और व्यापक विविधता।"
            ],
            "mr": [
                f"{b_name} मध्ये खरेदी करणे हा एक छान अनुभव होता, खूप चांगले पर्याय मिळाले.",
                f"कर्मचाऱ्यांच्या मदतीने मला {b_name} वर हवे असलेले सामान मिळाले.",
                f"{b_name} वर आश्चर्यकारक संकलन आणि छान सूट.",
                f"{b_name} मध्ये स्वच्छ दुकान, मोठी विविधता आणि सोपे बिलिंग.",
                f"{b_name} वर दर्जेदार उत्पादने आणि अस्सल वस्तू उपलब्ध आहेत.",
                f"{b_name} मध्ये खरेदी करणे नेहमीच आनंददायी असते.",
                f"नम्र कॅशियर आणि जलद बिलिंगमुळे {b_name} हे माझे आवडते दुकान आहे.",
                f"{b_name} वर उच्च दर्जाचा खरेदीचा अनुभव. अत्यंत शिफारस करतो.",
                f"{b_name} वर ट्रेंडी कलेक्शन आणि छान किंमती मिळाल्या.",
                f"{b_name} वर उत्कृष्ट ग्राहक सेवा."
            ]
        },
        "Hotel / Resort": {
            "en": [
                f"Our stay at {b_name} was exceptionally comfortable and luxurious.",
                f"Loved the hospitality, scenic views, and rooms at {b_name}.",
                f"A peaceful getaway at {b_name}. Impeccable cleanliness and service.",
                f"Delicious breakfast and prompt room service during our stay at {b_name}.",
                f"Modern amenities and secure property made {b_name} unforgettable.",
                f"Stunning ambiance and courteous staff at {b_name}.",
                f"Fast check-in and luxurious suites at {b_name} exceeded expectations.",
                f"Tranquil environment and top-tier hospitality at {b_name}.",
                f"A wonderful resort experience at {b_name}. Highly recommended.",
                f"Everything about {b_name} was pristine and relaxing."
            ],
            "hi": [
                f"{b_name} में हमारा प्रवास बेहद आरामदायक और शानदार रहा।",
                f"मुझे {b_name} का आतिथ्य सत्कार, सुंदर दृश्य और कमरे बहुत पसंद आए।",
                f"{b_name} में एक शांतिपूर्ण छुट्टी। त्रुटिहीन स्वच्छता और सेवा।",
                f"{b_name} में हमारे प्रवास के दौरान स्वादिष्ट नाश्ता और त्वरित रूम सर्विस।",
                f"आधुनिक सुविधाओं और सुरक्षित संपत्ति ने {b_name} को अविस्मरणीय बना दिया।",
                f"{b_name} में शानदार माहौल और विनम्र कर्मचारी।",
                f"{b_name} पर तेज चेक-इन और शानदार सुइट्स।",
                f"{b_name} में शांत वातावरण और उच्च स्तर का आतिथ्य।",
                f"{b_name} पर एक अद्भुत रिसॉर्ट अनुभव। अत्यधिक अनुशंसित।",
                f"{b_name} के बारे में सब कुछ प्राचीन और आरामदायक था।"
            ],
            "mr": [
                f"{b_name} मधील आमचा मुक्काम अत्यंत आरामदायी आणि विलासी होता.",
                f"मला {b_name} मधील आतिथ्य, निसर्गरम्य दृश्ये आणि खोल्या खूप आवडल्या.",
                f"{b_name} मध्ये एक शांत सुट्टी. निर्दोष स्वच्छता आणि सेवा.",
                f"{b_name} मधील मुक्कामादरम्यान स्वादिष्ट नाश्ता आणि रूम सर्व्हिस.",
                f"आधुनिक सुविधा आणि सुरक्षित मालमत्तेने {b_name} अविस्मरणीय बनवले.",
                f"{b_name} मध्ये सुंदर वातावरण आणि नम्र कर्मचारी.",
                f"{b_name} वर जलद चेक-इन आणि विलासी सुइट्स.",
                f"{b_name} मध्ये शांत वातावरण आणि उच्च दर्जाचे आतिथ्य.",
                f"{b_name} वर एक अद्भुत रिसॉर्ट अनुभव. अत्यंत शिफारस केलेले.",
                f"{b_name} बद्दल सर्वकाही स्वच्छ आणि आरामदायी होते."
            ]
        },
        "Gym / Fitness Studio": {
            "en": [
                f"Working out at {b_name} is always motivating and energizing.",
                f"Great equipment, clean changing rooms, and expert trainers at {b_name}.",
                f"Fantastic fitness community and well-maintained weights at {b_name}.",
                f"Spacious workout area and effective programs at {b_name}.",
                f"Proper sanitization and flexible timings at {b_name} make it the best gym.",
                f"Knowledgeable trainers and modern gear at {b_name}.",
                f"Always an incredible workout session at {b_name}.",
                f"Clean showers, great playlist, and motivating vibe at {b_name}.",
                f"Top-notch fitness studio! {b_name} helps you reach your goals.",
                f"Ample equipment and professional guidance at {b_name}."
            ],
            "hi": [
                f"{b_name} में वर्कआउट करना हमेशा ऊर्जावान और प्रेरणादायक होता है।",
                f"{b_name} में बेहतरीन उपकरण, साफ चेंजिंग रूम और विशेषज्ञ ट्रेनर हैं।",
                f"{b_name} पर शानदार फिटनेस समुदाय और अच्छी तरह से रखरखाव वाले वजन।",
                f"{b_name} में विशाल कसरत क्षेत्र और प्रभावी कार्यक्रम।",
                f"{b_name} में उचित सैनिटाइजेशन और लचीला समय इसे सबसे अच्छा जिम बनाता है।",
                f"{b_name} पर ज्ञानी प्रशिक्षक और आधुनिक गियर।",
                f"{b_name} पर हमेशा एक अविश्वसनीय कसरत सत्र।",
                f"{b_name} में साफ शॉवर, बेहतरीन प्लेलिस्ट और प्रेरक माहौल।",
                f"शीर्ष स्तर का फिटनेस स्टूडियो! {b_name} आपको अपने लक्ष्यों तक पहुँचने में मदद करता है।",
                f"{b_name} पर प्रचुर उपकरण और व्यावसायिक मार्गदर्शन।"
            ],
            "mr": [
                f"{b_name} मध्ये कसरत करणे नेहमीच ऊर्जावान आणि प्रेरणादायी असते.",
                f"{b_name} मध्ये उत्तम उपकरणे, स्वच्छ बदलण्याची खोली आणि तज्ज्ञ प्रशिक्षक आहेत.",
                f"{b_name} वर छान फिटनेस समुदाय.",
                f"{b_name} मध्ये मोकळी कसरत जागा आणि प्रभावी कार्यक्रम.",
                f"{b_name} मधील योग्य स्वच्छता आणि लवचिक वेळ यामुळे हे सर्वोत्तम जिम बनते.",
                f"{b_name} वर जाणकार प्रशिक्षक आणि आधुनिक उपकरणे.",
                f"{b_name} वर नेहमीच एक अविश्वसनीय कसरत सत्र.",
                f"{b_name} मध्ये स्वच्छ शॉवर आणि प्रेरक वातावरण.",
                f"अव्वल दर्जाचे फिटनेस स्टुडिओ! {b_name} तुम्हाला ध्येय गाठण्यास मदत करते.",
                f"{b_name} वर भरपूर उपकरणे आणि व्यावसायिक मार्गदर्शन."
            ]
        },
        "Healthcare / Clinic": {
            "en": [
                f"The care and attention at {b_name} made me feel so secure.",
                f"Very professional, clean clinic with minimal waiting time at {b_name}.",
                f"Caring doctor and polite nursing staff at {b_name}.",
                f"Accurate diagnosis and affordable consultation fees at {b_name}.",
                f"Well-equipped clinic with a calm and reassuring atmosphere.",
                f"Reliable pharmacy and excellent follow-up care at {b_name}.",
                f"Prompt appointments and compassionate treatment at {b_name}.",
                f"Exceptional healthcare service and clean instruments at {b_name}.",
                f"Dr. and staff at {b_name} are wonderfully supportive.",
                f"Trusted clinic for all health needs. Highly recommend {b_name}."
            ],
            "hi": [
                f"{b_name} पर मिलने वाली देखभाल से मुझे बहुत राहत मिली।",
                f"{b_name} न्यूनतम प्रतीक्षा समय के साथ एक बहुत ही पेशेवर, स्वच्छ क्लिनिक है।",
                f"{b_name} पर देखभाल करने वाले डॉक्टर और विनम्र नर्सिंग स्टाफ।",
                f"{b_name} पर सटीक निदान और किफायती परामर्श शुल्क।",
                f"शांत और आश्वस्त करने वाले माहौल के साथ सुसज्जित क्लिनिक।",
                f"{b_name} पर विश्वसनीय फार्मेसी और उत्कृष्ट फॉलो-अप देखभाल।",
                f"{b_name} पर त्वरित अपॉइंटमेंट और करुणामय उपचार।",
                f"{b_name} पर असाधारण स्वास्थ्य सेवा और स्वच्छ उपकरण।",
                f"{b_name} में डॉक्टर और स्टाफ बहुत मददगार हैं।",
                f"सभी स्वास्थ्य आवश्यकताओं के लिए विश्वसनीय क्लिनिक। {b_name} की अत्यधिक अनुशंसा करते हैं।"
            ],
            "mr": [
                f"{b_name} येथील काळजी आणि लक्ष यामुळे मला खूप सुरक्षित वाटले.",
                f"{b_name} ही कमी प्रतीक्षा वेळेसह अतिशय व्यावसायिक आणि स्वच्छ क्लिनिक आहे.",
                f"{b_name} वर काळजी घेणारे डॉक्टर आणि नम्र कर्मचारी.",
                f"{b_name} वर अचूक निदान आणि परवडणारी फी.",
                f"शांत वातावरणासह सुसज्ज क्लिनिक.",
                f"{b_name} वर विश्वसनीय फार्मसी आणि उत्कृष्ट काळजी.",
                f"{b_name} वर तात्काळ अपॉइंटमेंट आणि उत्तम उपचार.",
                f"{b_name} वर अपवादात्मक आरोग्य सेवा आणि स्वच्छ उपकरणे.",
                f"{b_name} मधील डॉक्टर आणि कर्मचारी खूप मदतनीस आहेत.",
                f"सर्व आरोग्य गरजांसाठी विश्वसनीय क्लिनिक. {b_name} ची शिफारस करतो."
            ]
        },
        "Auto Repair / Garage": {
            "en": [
                f"Got my vehicle fixed quickly and honestly at {b_name}.",
                f"Fair pricing, genuine spare parts, and expert mechanics at {b_name}.",
                f"Reliable service with transparent quotations at {b_name}.",
                f"Punctual delivery and spotless workshop at {b_name}.",
                f"Honest advice and top-quality repair work at {b_name}.",
                f"Free pickup and drop service made things so easy at {b_name}.",
                f"My car runs like new after visiting {b_name}.",
                f"Professional garage with warranty offered on repairs.",
                f"Trustworthy mechanics and great communication at {b_name}.",
                f"Outstanding auto repair shop. Highly recommend {b_name}."
            ],
            "hi": [
                f"{b_name} पर मेरी गाड़ी की मरम्मत बहुत जल्दी और ईमानदारी से की गई।",
                f"{b_name} पर उचित मूल्य, वास्तविक स्पेयर पार्ट्स और विशेषज्ञ मैकेनिक।",
                f"{b_name} पर पारदर्शी कोटेशन के साथ विश्वसनीय सेवा।",
                f"{b_name} पर समय पर डिलीवरी और बेदाग कार्यशाला।",
                f"{b_name} पर ईमानदार सलाह और उच्च गुणवत्ता का मरम्मत कार्य।",
                f"{b_name} पर मुफ्त पिकअप और ड्रॉप सेवा ने चीजों को बहुत आसान बना दिया।",
                f"{b_name} जाने के बाद मेरी कार नए जैसी चलती है।",
                f"मरम्मत पर वारंटी के साथ पेशेवर गैराज।",
                f"{b_name} पर भरोसेमंद मैकेनिक और बेहतरीन संचार।",
                f"उत्कृष्ट ऑटो मरम्मत की दुकान। {b_name} की अत्यधिक अनुशंसा करें।"
            ],
            "mr": [
                f"{b_name} वर माझ्या गाडीची दुरुस्ती अतिशय जलद आणि प्रामाणिकपणे केली.",
                f"{b_name} वर योग्य किंमत, अस्सल स्पेयर पार्ट्स आणि तज्ज्ञ मेकॅनिक.",
                f"{b_name} वर पारदर्शक कोटेशनसह विश्वसनीय सेवा.",
                f"{b_name} वर वेळेवर डिलिव्हरी आणि स्वच्छ कार्यशाळा.",
                f"{b_name} वर प्रामाणिक सल्ला आणि दर्जेदार दुरुस्ती काम.",
                f"{b_name} वर मोफत पिकअप आणि ड्रॉप सेवेमुळे गोष्टी सोप्या झाल्या.",
                f"{b_name} ला भेट दिल्यानंतर माझी कार नवीनसारखी चालते.",
                f"दुरुस्तीवर वारंटी देणारा व्यावसायिक गॅरेज.",
                f"{b_name} वर विश्वासू मेकॅनिक आणि उत्तम संवाद.",
                f"उत्कृष्ट ऑटो रिपेअर दुकान. {b_name} ची शिफारस करतो."
            ]
        },
        "Dental Clinic": {
            "en": [
                f"My dental procedure at {b_name} was completely painless and smooth.",
                f"Gentle dentist and ultra-clean modern clinic at {b_name}.",
                f"Affordable treatment and clear guidance at {b_name}.",
                f"No waiting time and comfortable chairs at {b_name}.",
                f"Sterile environment and reassuring staff at {b_name}.",
                f"Detailed explanation of procedures and great results.",
                f"Painless root canal and polite hygienist at {b_name}.",
                f"State-of-the-art technology and expert dental care at {b_name}.",
                f"Best dental clinic experience I've ever had.",
                f"Very professional dentist. Highly recommend {b_name}."
            ],
            "hi": [
                f"{b_name} पर मेरी दांतों की प्रक्रिया पूरी तरह से दर्दमुक्त और सहज रही।",
                f"{b_name} में सौम्य डेंटिस्ट और अति-स्वच्छ आधुनिक क्लिनिक।",
                f"{b_name} पर किफायती इलाज और स्पष्ट मार्गदर्शन।",
                f"{b_name} पर कोई प्रतीक्षा समय और आरामदायक कुर्सियां नहीं।",
                f"{b_name} पर बाँझ वातावरण और आश्वस्त करने वाला स्टाफ।",
                f"प्रक्रियाओं का विस्तृत विवरण और बेहतरीन परिणाम।",
                f"{b_name} पर दर्द रहित रूट कैनाल और विनम्र हाइजेनिस्ट।",
                f"{b_name} पर अत्याधुनिक तकनीक और विशेषज्ञ दंत चिकित्सा देखभाल।",
                f"अब तक का सबसे अच्छा दंत चिकित्सा क्लिनिक अनुभव।",
                f"बहुत पेशेवर डेंटिस्ट। {b_name} की अत्यधिक अनुशंसा करते हैं।"
            ],
            "mr": [
                f"{b_name} येथील माझी दातांची प्रक्रिया पूर्णपणे वेदनारहित आणि सुलभ झाली.",
                f"{b_name} मध्ये सौम्य दंतवैद्य आणि अतिशय स्वच्छ आधुनिक क्लिनिक.",
                f"{b_name} वर परवडणारा उपचार आणि स्पष्ट मार्गदर्शन.",
                f"{b_name} वर प्रतीक्षा वेळ नाही आणि आरामदायी खुर्च्या.",
                f"{b_name} वर निर्जंतुक वातावरण.",
                f"प्रक्रियांचे तपशीलवार स्पष्टीकरण आणि उत्तम निकाल.",
                f"{b_name} वर वेदनारहित रूट कॅनाल आणि नम्र कर्मचारी.",
                f"{b_name} वर अत्याधुनिक तंत्रज्ञान आणि तज्ज्ञ दंत काळजी.",
                f"माझा आतापर्यंतचा सर्वोत्तम दंत क्लिनिक अनुभव.",
                f"अतिशय व्यावसायिक दंतवैद्य. {b_name} ची शिफारस करतो."
            ]
        },
        "Real Estate Agency": {
            "en": [
                f"Finding a property through {b_name} was completely hassle-free.",
                f"Professional agents and transparent dealings at {b_name}.",
                f"Great property options and verified listings at {b_name}.",
                f"Smooth documentation and helpful support throughout.",
                f"Punctual visits and honest market advice from {b_name}.",
                f"Quick response and excellent negotiation skills by agents.",
                f"Trustworthy and reliable real estate service at {b_name}.",
                f"Clear terms and end-to-end service made buying easy.",
                f"Exceptional real estate agency with great market knowledge.",
                f"Very satisfied with {b_name}. Highly recommend."
            ],
            "hi": [
                f"{b_name} के माध्यम से संपत्ति ढूंढना बेहद आसान और झंझट-मुक्त था।",
                f"{b_name} पर एजेंट बहुत पेशेवर और पारदर्शी हैं।",
                f"{b_name} पर महान संपत्ति विकल्प और सत्यापित लिस्टिंग।",
                f"सुगम दस्तावेजीकरण और पूरे समय मददगार समर्थन।",
                f"{b_name} से समय पर विजिट और ईमानदार बाजार सलाह।",
                f"एजेंटों द्वारा त्वरित प्रतिक्रिया और उत्कृष्ट बातचीत कौशल।",
                f"{b_name} पर भरोसेमंद और विश्वसनीय रियल एस्टेट सेवा।",
                f"स्पष्ट शर्तों और एंड-टू-एंड सेवा ने खरीदारी को आसान बना दिया।",
                f"शानदार बाजार ज्ञान के साथ असाधारण रियल एस्टेट एजेंसी।",
                f"{b_name} से बहुत संतुष्ट हैं। अत्यधिक अनुशंसा करते हैं।"
            ],
            "mr": [
                f"{b_name} द्वारे मालमत्ता शोधणे अत्यंत सोपे आणि त्रासमुक्त होते.",
                f"{b_name} वर एजंट अतिशय व्यावसायिक आणि पारदर्शक आहेत.",
                f"{b_name} वर उत्तम मालमत्ता पर्याय आणि सत्यापित याद्या.",
                f"सुगम कागदपत्रे आणि मदतशीर समर्थन.",
                f"{b_name} कडून वेळेवर भेटी आणि प्रामाणिक बाजार सल्ला.",
                f"त्वरित प्रतिसाद आणि उत्कृष्ट वाटाघाटी कौशल्ये.",
                f"{b_name} वर विश्वासू आणि भरवशाची रिअल इस्टेट सेवा.",
                f"स्पष्ट अटी आणि एन्ड-टू-एन्ड सेवेमुळे खरेदी सोपी झाली.",
                f"उत्कृष्ट बाजार ज्ञानासह अपवादात्मक रिअल इस्टेट एजन्सी.",
                f"{b_name} बद्दल खूप समाधान वाटले. शिफारस करतो."
            ]
        },
        "Bakery / Confectionery": {
            "en": [
                f"The baked goods and cakes from {b_name} are exceptionally delicious.",
                f"Freshly baked pastries and mouthwatering treats at {b_name}.",
                f"Friendly baker and stunning custom design cakes.",
                f"Reasonable prices, soft bread, and great aroma.",
                f"Prompt packing and awesome taste at {b_name}.",
                f"Huge variety of flavors and eggless options available.",
                f"Clean store and hygienic display of treats.",
                f"The cake from {b_name} made our celebration extra special.",
                f"Absolute heaven for sweet lovers! {b_name} is the best.",
                f"Fresh and mouthwatering treats always at {b_name}."
            ],
            "hi": [
                f"{b_name} के बेक किए हुए उत्पाद और केक बेहद स्वादिष्ट हैं।",
                f"{b_name} पर ताजे बेक किए हुए पेस्ट्री और मुंह में पानी लाने वाले व्यंजन।",
                f"मिलनसार बेकर और शानदार कस्टम डिजाइन केक।",
                f"उचित कीमतें, नरम ब्रेड और शानदार खुशबू।",
                f"{b_name} पर तुरंत पैकिंग और शानदार स्वाद।",
                f"विभिन्न प्रकार के स्वाद और बिना अंडे के विकल्प उपलब्ध हैं।",
                f"साफ स्टोर और व्यंजनों का स्वच्छ प्रदर्शन।",
                f"{b_name} के केक ने हमारे जश्न को और भी खास बना दिया।",
                f"मीठे प्रेमियों के लिए पूर्ण स्वर्ग! {b_name} सबसे अच्छा है।",
                f"{b_name} पर हमेशा ताजे और लजीज व्यंजन मिलते हैं।"
            ],
            "mr": [
                f"{b_name} कडून मिळालेले बेक केलेले पदार्थ आणि केक अत्यंत स्वादिष्ट आहेत.",
                f"{b_name} वर ताजे बेक केलेले पेस्ट्री आणि चवदार पदार्थ.",
                f"मित्रत्वाचा बेकर आणि सुंदर कस्टम डिझाइन केक.",
                f"वाजवी किंमती, मऊ ब्रेड आणि छान सुवास.",
                f"{b_name} वर तात्काळ पॅकिंग आणि छान चव.",
                f"विविध फ्लेवर्स आणि विना अंड्याचे पर्याय उपलब्ध.",
                f"स्वच्छ दुकान आणि पदार्थांचे आरोग्यदायी प्रदर्शन.",
                f"{b_name} च्या केकमुळे आमचा सण आणखी खास झाला.",
                f"गोडप्रेमींसाठी स्वर्गाचे ठिकाण! {b_name} सर्वोत्तम आहे.",
                f"{b_name} वर नेहमी ताजे आणि चवदार पदार्थ मिळतात."
            ]
        }
    }

    cat_dict = cat_intros.get(category, cat_intros["Restaurant / Cafe"])
    intros = cat_dict.get(lang, cat_dict["en"])
    
    tag_str = ", ".join(tags) if tags else ""
    
    if lang == 'hi':
        middles = [f"उन्होंने वास्तव में {tag_str} को बेहतरीन तरीके से निभाया।"] if tags else []
        outros = ["अत्यधिक अनुशंसित!", "निश्चित रूप से जल्द ही वापस आऊंगा।"]
    elif lang == 'mr':
        middles = [f"त्यांनी खरोखरच {tag_str} उत्तम प्रकारे हाताळले."] if tags else []
        outros = ["अत्यंत शिफारस केलेले!", "नक्कीच लवकरच परत येईल."]
    else:
        middles = [f"They completely nailed the {tag_str}."] if tags else []
        outros = ["Highly recommended!", "Will definitely be coming back soon."]

    review = random.choice(intros)
    if middles:
        review += " " + random.choice(middles)
    review += " " + random.choice(outros)
    
    return {"review": review}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
