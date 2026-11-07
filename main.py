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

REVIEW_INTROS = {
    "Restaurant / Cafe": {
        "en": [
            "I recently visited {name} and the food and ambiance were incredible.",
            "Had a wonderful dining experience at {name} today with outstanding flavors.",
            "Absolute favorite spot in town! {name} never fails to impress with great quality.",
            "Came to {name} for lunch and everything from the service to the dishes was top-notch.",
            "A fantastic evening spent at {name}. Cozy atmosphere and delicious food.",
            "Every dish we ordered at {name} was cooked to perfection and served promptly.",
        ],
        "hi": [
            "मैंने हाल ही में {name} का दौरा किया और यहाँ का खाना और माहौल शानदार था।",
            "आज {name} में भोजन का अनुभव बहुत अच्छा रहा, बेहतरीन स्वाद।",
            "शहर में मेरी पसंदीदा जगह! {name} हमेशा उच्च गुणवत्ता से प्रभावित करता है।",
            "दोपहर के भोजन के लिए {name} आया और सेवा से लेकर व्यंजनों तक सब कुछ बेहतरीन था।",
        ],
        "mr": [
            "मी अलीकडेच {name} ला भेट दिली आणि येथील अन्न आणि वातावरण अप्रतिम होते.",
            "आज {name} मध्ये जेवणाचा अनुभव खूप छान होता, उत्तम चव.",
            "शहरातील माझे आवडते ठिकाण! {name} नेहमीच उत्तम गुणवत्ता देते.",
            "दुपारच्या जेवणासाठी {name} ला आलो आणि सर्व काही उत्तम होते.",
        ],
    },
    "Salon / Spa": {
        "en": [
            "I had a wonderful experience at {name}. The staff was professional and the service truly relaxing.",
            "Visited {name} for a salon session and left feeling refreshed. Skilled team and great hygiene.",
            "{name} is my go-to place for self-care. Friendly staff and excellent results every time.",
            "Loved the calm atmosphere at {name}. The stylists really listen and know their craft.",
            "Booked an appointment at {name} and they were right on time. Fantastic service from start to finish.",
        ],
        "hi": [
            "{name} में मेरा अनुभव बहुत शानदार रहा। स्टाफ प्रोफेशनल है और सेवा बेहद आरामदायक थी।",
            "सैलून सेवा के लिए {name} गया और तरोताज़ा महसूस करके लौटा। कुशल टीम और बेहतरीन स्वच्छता।",
            "{name} का माहौल बहुत शांत और सुकून भरा है। स्टाइलिस्ट अपने काम में माहिर हैं।",
            "समय पर अपॉइंटमेंट और शानदार सेवा, {name} हर बार संतुष्ट करता है।",
        ],
        "mr": [
            "{name} येथील अनुभव खूपच छान होता. कर्मचारी व्यावसायिक आहेत आणि सेवा अतिशय आरामदायी होती.",
            "सलून सेवेसाठी {name} ला गेलो आणि ताजेतवाने वाटले. कुशल टीम आणि उत्तम स्वच्छता.",
            "{name} चे वातावरण शांत आणि सुखद आहे. स्टायलिस्ट आपल्या कामात निपुण आहेत.",
            "वेळेवर अपॉइंटमेंट आणि उत्कृष्ट सेवा, {name} नेहमीच समाधान देते.",
        ],
    },
    "Retail / Shopping": {
        "en": [
            "Had a great shopping experience at {name}. Wide variety and very helpful staff.",
            "{name} has a fantastic collection and the prices are totally worth it.",
            "Loved shopping at {name}. The store is clean, well stocked and billing was quick.",
            "Found exactly what I was looking for at {name}. Genuine products and polite staff.",
            "{name} is my go-to store for quality products and great discounts.",
        ],
        "hi": [
            "{name} में खरीदारी का अनुभव बहुत अच्छा रहा। बड़ी वैरायटी और मददगार स्टाफ।",
            "{name} का कलेक्शन शानदार है और कीमतें भी बिल्कुल सही हैं।",
            "{name} में खरीदारी करना पसंद आया। स्टोर साफ-सुथरा है और बिलिंग तेज़ थी।",
            "जो चाहिए था वो {name} में मिल गया। असली प्रोडक्ट्स और विनम्र स्टाफ।",
        ],
        "mr": [
            "{name} मध्ये खरेदीचा अनुभव खूप छान होता. उत्तम व्हरायटी आणि मदत करणारा स्टाफ.",
            "{name} चे कलेक्शन अप्रतिम आहे आणि किंमतीही योग्य आहेत.",
            "{name} मध्ये खरेदी करायला आवडले. स्टोअर स्वच्छ आहे आणि बिलिंग जलद होते.",
            "हवे ते सर्व {name} मध्ये मिळाले. अस्सल उत्पादने आणि नम्र कर्मचारी.",
        ],
    },
    "Hotel / Resort": {
        "en": [
            "Our stay at {name} was wonderful. Comfortable rooms and truly courteous staff.",
            "{name} offers a peaceful, luxurious experience. Check-in was smooth and the rooms spotless.",
            "Had a memorable getaway at {name}. Great hospitality, delicious breakfast and lovely views.",
            "Highly impressed by {name}. Clean, spacious rooms and prompt room service throughout our stay.",
            "A perfect stay at {name}. Modern amenities and a relaxing environment made it special.",
        ],
        "hi": [
            "{name} में हमारा ठहराव शानदार रहा। आरामदायक कमरे और बेहद विनम्र स्टाफ।",
            "{name} शांत और आलीशान अनुभव देता है। चेक-इन आसान था और कमरे बेहद साफ थे।",
            "{name} में यादगार छुट्टी बिताई। बेहतरीन मेहमाननवाज़ी, स्वादिष्ट नाश्ता और सुंदर नज़ारे।",
            "{name} ने बहुत प्रभावित किया। साफ, खुले कमरे और तुरंत रूम सर्विस।",
        ],
        "mr": [
            "{name} मधील आमचा मुक्काम अप्रतिम होता. आरामदायी खोल्या आणि अतिशय सौजन्यशील कर्मचारी.",
            "{name} शांत आणि आलिशान अनुभव देते. चेक-इन सुलभ होते आणि खोल्या अतिशय स्वच्छ होत्या.",
            "{name} मध्ये संस्मरणीय सुट्टी घालवली. उत्कृष्ट आदरातिथ्य, चविष्ट नाश्ता आणि सुंदर दृश्ये.",
            "{name} ने खूप प्रभावित केले. स्वच्छ, प्रशस्त खोल्या आणि तत्पर रूम सर्व्हिस.",
        ],
    },
    "Gym / Fitness Studio": {
        "en": [
            "{name} is a fantastic gym. Modern equipment and very knowledgeable trainers.",
            "Joined {name} recently and the motivating environment keeps me coming back.",
            "Great workout space at {name}. Clean changing rooms, spacious floor and flexible timings.",
            "The trainers at {name} give real personal attention and effective programs.",
            "Best fitness studio around! {name} is hygienic, well ventilated and has a friendly community.",
        ],
        "hi": [
            "{name} एक शानदार जिम है। आधुनिक उपकरण और बहुत जानकार ट्रेनर्स।",
            "हाल ही में {name} जॉइन किया और यहाँ का प्रेरक माहौल मुझे बार-बार खींच लाता है।",
            "{name} में वर्कआउट की बढ़िया जगह है। साफ चेंजिंग रूम, खुली जगह और लचीला समय।",
            "{name} के ट्रेनर्स व्यक्तिगत ध्यान देते हैं और प्रोग्राम बहुत असरदार हैं।",
        ],
        "mr": [
            "{name} हे एक उत्कृष्ट जिम आहे. आधुनिक उपकरणे आणि अतिशय जाणकार ट्रेनर्स.",
            "नुकतेच {name} जॉइन केले आणि येथील प्रेरणादायी वातावरण पुन्हा पुन्हा येण्यास भाग पाडते.",
            "{name} मध्ये वर्कआउटसाठी उत्तम जागा आहे. स्वच्छ चेंजिंग रूम, प्रशस्त जागा आणि लवचिक वेळा.",
            "{name} चे ट्रेनर्स वैयक्तिक लक्ष देतात आणि प्रोग्राम्स खूप प्रभावी आहेत.",
        ],
    },
    "Healthcare / Clinic": {
        "en": [
            "I had a great experience at {name}. The doctor was caring and explained everything clearly.",
            "{name} is a clean, well-equipped clinic with very friendly staff and minimal waiting time.",
            "Visited {name} for a checkup and felt completely at ease. Accurate diagnosis and polite team.",
            "Grateful for the attentive care at {name}. Booking was easy and the follow-up was excellent.",
            "Highly trustworthy clinic. {name} offers affordable fees and a calm, hygienic environment.",
        ],
        "hi": [
            "{name} में मेरा अनुभव बहुत अच्छा रहा। डॉक्टर ने ध्यान से सब कुछ स्पष्ट समझाया।",
            "{name} साफ-सुथरा और सुसज्जित क्लिनिक है। स्टाफ मिलनसार है और इंतज़ार कम करना पड़ा।",
            "जाँच के लिए {name} गया और पूरी तरह सहज महसूस किया। सही निदान और विनम्र टीम।",
            "{name} की देखभाल के लिए आभारी हूँ। बुकिंग आसान थी और फॉलो-अप बेहतरीन रहा।",
        ],
        "mr": [
            "{name} मधील माझा अनुभव खूप चांगला होता. डॉक्टरांनी काळजीपूर्वक सर्व काही स्पष्ट समजावले.",
            "{name} हे स्वच्छ आणि सुसज्ज क्लिनिक आहे. कर्मचारी मैत्रीपूर्ण आहेत आणि प्रतीक्षा कमी होती.",
            "तपासणीसाठी {name} ला गेलो आणि निश्चिंत वाटले. अचूक निदान आणि नम्र टीम.",
            "{name} मधील काळजीबद्दल आभारी आहे. बुकिंग सोपे होते आणि फॉलो-अप उत्कृष्ट होता.",
        ],
    },
    "Auto Repair / Garage": {
        "en": [
            "{name} did an excellent job on my vehicle. Honest mechanics and fair pricing.",
            "Fast, reliable repair at {name}. They gave a clear quotation and delivered on time.",
            "Very happy with {name}. Genuine spare parts, expert diagnosis and quality workmanship.",
            "Finally found a trustworthy garage! {name} explained the issue and fixed it properly.",
            "{name} is clean, well equipped and professional. My car runs like new.",
        ],
        "hi": [
            "{name} ने मेरी गाड़ी का बेहतरीन काम किया। ईमानदार मैकेनिक और उचित दाम।",
            "{name} में तेज़ और भरोसेमंद मरम्मत हुई। स्पष्ट कोटेशन दिया और समय पर डिलीवरी की।",
            "{name} से बहुत खुश हूँ। असली स्पेयर पार्ट्स, सही जाँच और उम्दा काम।",
            "आखिरकार भरोसेमंद गैराज मिला! {name} ने समस्या समझाई और ठीक से सुधारी।",
        ],
        "mr": [
            "{name} ने माझ्या गाडीचे उत्कृष्ट काम केले. प्रामाणिक मेकॅनिक आणि योग्य किंमत.",
            "{name} मध्ये जलद आणि विश्वासार्ह दुरुस्ती झाली. स्पष्ट कोटेशन दिले आणि वेळेवर डिलिव्हरी केली.",
            "{name} बद्दल खूप समाधानी आहे. अस्सल स्पेअर पार्ट्स, अचूक तपासणी आणि दर्जेदार काम.",
            "शेवटी विश्वासू गॅरेज सापडले! {name} ने समस्या समजावली आणि व्यवस्थित दुरुस्त केली.",
        ],
    },
    "Dental Clinic": {
        "en": [
            "I had a great visit to {name}. The dentist was gentle and the procedure was painless.",
            "{name} is a clean, modern dental clinic with a friendly and caring team.",
            "Was nervous about my treatment, but {name} made me comfortable and explained every step.",
            "Excellent results at {name}. Hygienic tools, no long wait and very fair pricing.",
            "Highly recommend {name} for dental care. Professional, sterile and truly gentle.",
        ],
        "hi": [
            "{name} में मेरा अनुभव बहुत अच्छा रहा। डेंटिस्ट सौम्य थे और प्रक्रिया बिल्कुल दर्दरहित रही।",
            "{name} साफ और आधुनिक डेंटल क्लिनिक है, जहाँ टीम मिलनसार और देखभाल करने वाली है।",
            "इलाज को लेकर घबराहट थी, लेकिन {name} ने सहज महसूस कराया और हर कदम समझाया।",
            "{name} में बेहतरीन नतीजे मिले। साफ औज़ार, कम इंतज़ार और उचित कीमत।",
        ],
        "mr": [
            "{name} ला दिलेली भेट खूप छान होती. दंतवैद्य सौम्य होते आणि प्रक्रिया वेदनारहित होती.",
            "{name} हे स्वच्छ आणि आधुनिक डेंटल क्लिनिक आहे, येथील टीम मैत्रीपूर्ण आणि काळजी घेणारी आहे.",
            "उपचारांची भीती वाटत होती, पण {name} ने सहज वाटू दिले आणि प्रत्येक टप्पा समजावला.",
            "{name} मध्ये उत्कृष्ट परिणाम मिळाले. स्वच्छ साधने, कमी प्रतीक्षा आणि योग्य किंमत.",
        ],
    },
    "Real Estate Agency": {
        "en": [
            "{name} made our property search smooth and stress-free. Transparent and professional agents.",
            "Had a great experience with {name}. Verified listings, honest advice and quick responses.",
            "Highly recommend {name} for property deals. Documentation was handled smoothly end to end.",
            "The team at {name} understands the market well and negotiated a great deal for us.",
            "Trustworthy and punctual. {name} showed us excellent property options that matched our needs.",
        ],
        "hi": [
            "{name} ने हमारी प्रॉपर्टी की खोज आसान और तनावमुक्त बना दी। पारदर्शी और पेशेवर एजेंट।",
            "{name} के साथ अनुभव बहुत अच्छा रहा। सत्यापित लिस्टिंग, ईमानदार सलाह और त्वरित जवाब।",
            "प्रॉपर्टी डील के लिए {name} की सिफारिश करता हूँ। दस्तावेज़ी काम शुरू से अंत तक आसानी से हुआ।",
            "{name} की टीम बाज़ार को अच्छी तरह समझती है और हमारे लिए शानदार डील करवाई।",
        ],
        "mr": [
            "{name} ने आमचा प्रॉपर्टी शोध सोपा आणि तणावमुक्त केला. पारदर्शक आणि व्यावसायिक एजंट.",
            "{name} सोबतचा अनुभव खूप चांगला होता. पडताळलेल्या लिस्टिंग, प्रामाणिक सल्ला आणि जलद प्रतिसाद.",
            "प्रॉपर्टी व्यवहारांसाठी {name} ची शिफारस करतो. कागदपत्रांचे काम सुरुवातीपासून शेवटपर्यंत सुरळीत झाले.",
            "{name} ची टीम बाजाराला चांगले ओळखते आणि आमच्यासाठी उत्तम डील करून दिली.",
        ],
    },
    "Bakery / Confectionery": {
        "en": [
            "The cakes at {name} are absolutely delicious and always freshly baked.",
            "Ordered a custom cake from {name} and it looked and tasted amazing.",
            "{name} has the softest bread and the most mouthwatering pastries in town.",
            "Walked into {name} and the aroma alone won me over. Great variety and reasonable prices.",
            "Our go-to bakery for every celebration. {name} never disappoints on taste or freshness.",
        ],
        "hi": [
            "{name} के केक बेहद स्वादिष्ट हैं और हमेशा ताज़ा बेक किए होते हैं।",
            "{name} से कस्टम केक ऑर्डर किया और वह दिखने और स्वाद में लाजवाब था।",
            "{name} में शहर की सबसे मुलायम ब्रेड और मुँह में पानी लाने वाली पेस्ट्री मिलती है।",
            "{name} में कदम रखते ही खुशबू ने दिल जीत लिया। बढ़िया वैरायटी और उचित दाम।",
        ],
        "mr": [
            "{name} चे केक अतिशय चविष्ट आहेत आणि नेहमी ताजे बेक केलेले असतात.",
            "{name} कडून कस्टम केक ऑर्डर केला आणि तो दिसायला आणि चवीला अप्रतिम होता.",
            "{name} मध्ये शहरातील सर्वात मऊ ब्रेड आणि तोंडाला पाणी आणणाऱ्या पेस्ट्री मिळतात.",
            "{name} मध्ये पाऊल ठेवताच सुगंधाने मन जिंकले. उत्तम व्हरायटी आणि योग्य किंमती.",
        ],
    },
}

TAG_LEADS = {
    "en": "Highlights: {tags}.",
    "hi": "मुख्य विशेषताएँ: {tags}।",
    "mr": "प्रमुख वैशिष्ट्ये: {tags}.",
}

CLOSINGS = {
    "en": ["Highly recommended!", "Will definitely visit again!", "Totally worth it!"],
    "hi": ["अत्यधिक अनुशंसित!", "मैं दोबारा ज़रूर आऊँगा!", "बिल्कुल पैसा वसूल!"],
    "mr": ["अत्यंत शिफारस केलेले!", "मी नक्कीच पुन्हा येईन!", "अगदी पैसा वसूल!"],
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

# NOTE: `app` must be created BEFORE any @app.get / @app.post decorator below.
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


# ---------------------------------------------------------------
# AI review generator (category-aware). Must stay AFTER `app = FastAPI(...)`.
# ---------------------------------------------------------------
@app.post("/api/ai/generate-review")
async def generate_ai_review(req: dict):
    b_name = req.get("business_name") or "this establishment"
    category = req.get("category") or "Restaurant / Cafe"
    tags = req.get("tags") or []
    lang = req.get("lang") or "en"

    if lang not in TAG_LEADS:
        lang = "en"

    cat_dict = REVIEW_INTROS.get(category, REVIEW_INTROS["Restaurant / Cafe"])
    intros = cat_dict.get(lang) or cat_dict["en"]

    review = random.choice(intros).format(name=b_name)

    if tags:
        review += " " + TAG_LEADS[lang].format(tags=", ".join(tags))

    review += " " + random.choice(CLOSINGS[lang])

    return {"review": review}