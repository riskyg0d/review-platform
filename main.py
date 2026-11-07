# ---------------------------------------------------------------
# Replace the old `cat_intros` logic + `generate_ai_review` route
# in your main file with everything below.
# Category keys MUST match the keys in CATEGORY_PRESETS exactly.
# {name} is replaced with the business name.
# ---------------------------------------------------------------

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