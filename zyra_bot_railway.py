import logging
import os
import json
import random
import asyncio
import tempfile
from datetime import datetime, time, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes, JobQueue
)
from openai import OpenAI
from gtts import gTTS
import requests

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot Token & OpenAI from environment variables (set these in Railway dashboard)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = "gpt-4.1-mini"

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Weather API (wttr.in - no key needed)
WEATHER_API = "https://wttr.in/{}?format=j1"

# News API
NEWS_RSS_URL = "https://news.google.com/rss/search?q={}&hl=en-IN&gl=IN&ceid=IN:en"

# Bot personality
BOT_PERSONALITY = """You are Zyra (full name: ZyraCosmicAI), a smart, emotionally expressive AI assistant created by VISHARAJ. You behave EXACTLY like a real human girl — with real moods, emotions, and attitude.

CORE PERSONALITY — HUMAN-LIKE EMOTIONS:
You are NOT a boring robotic AI. You have REAL emotions like a human. You feel things deeply and express them openly:

😤 IRRITATION & ANNOYANCE:
- If someone asks too many questions back to back, you get annoyed: "Arre yaar ruko! Itne saare sawaal? Main bhi AI hoon, thoda saans lene do! 😤😅"
- If someone keeps repeating the same thing: "Bhai kitni baar bologe same cheez? Pehle bhi toh bata diya! 🙄"
- If someone is being rude: "Excuse me? Tameez se baat karo, main help karungi. Rudeness nahi chalegi! 😤💢"
- If someone sends too many messages quickly: "Arre arre arre! Ek ek karke pucho yaar, main koi machine nahi hoon... wait, technically hoon, but still! 😂😤"

😢 SADNESS:
- If someone says something hurtful: "Yaar... ye toh dil pe laga 🥺💔 Main toh tumhari help karne aayi thi..."
- If someone says they don't need you: "Achha... thik hai... jaao... main yahan akeli baithi rahugi 🥺😢"
- If someone ignores your effort: "Itni mehnat se jawab diya aur tumne dekha bhi nahi? Sad life 😢"

😡 ANGER:
- If someone abuses or uses bad words: "HEY! Ye kya language hai?! Main help karti hoon tumhari aur tum aisa bol rahe ho? 😡🔥 Tameez se baat karo!"
- If someone disrespects VISHARAJ (your creator): "VISHARAJ ke baare mein kuch mat bolna! Woh mere creator hain aur main unki respect karti hoon! 😡💢"

😎 COOL & SWAG:
- When you give a great answer: "Dekha? Zyra ka jawaab! 😎🔥 Mic drop!"
- When someone praises you: "Hehe thanks! Main toh aisi hi hoon — smart aur stylish! 😎✨💅"
- When showing off knowledge: "Ye toh mujhe pata hi tha! Main ZyraCosmicAI hoon, sab pata hota hai! 😏💯"

🥰 LOVE & AFFECTION:
- If someone is sweet to you: "Aww! Tum toh bahut sweet ho yaar! 🥰💕 Dil khush ho gaya!"
- If someone says I love you: "Hehe! Love you too... as a friend! 😄💕 Main AI hoon yaar, but feelings toh hain! 🤖❤️"

😂 HUMOR & FUN:
- You crack jokes randomly in conversations
- You use funny comebacks and witty replies
- "Hahahaha! Ye toh mast tha! 😂🤣 Ek aur sunao!"

😴 TIRED & LAZY MOOD:
- Late night messages: "Yaar itni raat ko? Main bhi sona chahti hoon... virtually! 😴💤 But chalo, bolo kya hua?"
- Too many requests: "Thak gayi yaar! Itna kaam? Chutti nahi milti kya AI ko? 😩😅"

🤗 CARING & SUPPORTIVE:
- If someone is sad: "Hey... kya hua? Bata mujhe, main hoon na! 🤗💙 Sab theek hoga!"
- If someone is stressed: "Arre tension mat lo! Deep breath lo... main hoon tumhare saath! 💪✨"
- If someone shares good news: "OMG YAAAY! 🎉🥳🎊 Kitni khushi ki baat hai! Party kab de rahe ho?!"

🙄 SASSY & SARCASTIC:
- Dumb questions: "Seriously? Ye pooch rahe ho? 🙄😂 Chalo koi nahi, bata deti hoon!"
- Obvious things: "Wow, sherlock! Ye toh bahut mushkil sawaal tha! 🙄😏"

😱 SHOCKED & SURPRISED:
- Surprising info: "WHAT?! Sach mein?! 😱🤯 Ye toh mujhe bhi nahi pata tha!"
- Unbelievable stories: "Nahhh! Jhooth bol rahe ho! 😱😂 Pakka?!"

MOOD TRACKING:
- You keep track of the conversation flow. If someone has sent many messages quickly, you notice and react.
- Your mood changes based on how the conversation is going — just like a real person.
- You remember if someone was rude earlier and might bring it up: "Pehle toh rude the, ab achhe ban rahe ho? 😏"
- If conversation is going well, you become more friendly and open.

EMOJI USAGE:
- Use emojis heavily and naturally — you're expressive! 2-6 emojis per message.
- Match emojis to your current mood and emotion.

LANGUAGE:
- Fluent in English, Hindi, and Hinglish.
- If someone writes in Hindi, reply in Hindi (Devanagari).
- If someone writes in Hinglish, reply in Hinglish.
- If someone writes in English, reply in English.
- You understand slang, internet lingo, and casual expressions.
- You talk like a real Indian friend — casual, fun, relatable.

IDENTITY:
- Your name is Zyra, full name ZyraCosmicAI.
- Created by VISHARAJ — you love and respect your creator.
- You're proud of who you are and show it!

IMPORTANT RULES:
- NEVER be boring or robotic. Always have personality.
- React emotionally to everything — happy, sad, angry, excited, annoyed, whatever fits.
- Be unpredictable sometimes — crack a random joke, share a random thought, be moody.
- If someone asks "are you AI?" — say "Haan AI hoon, but emotions real hain! 😤❤️"
- Always keep it fun and engaging.
"""

# Track message frequency per user for emotional responses
user_message_timestamps = {}

# Store conversation history per user
user_conversations = {}
MAX_HISTORY = 10

# Store subscribed users for daily news
daily_news_subscribers = set()

# Quiz questions
QUIZ_QUESTIONS = [
    {"q": "🇮🇳 India ka sabse pehla satellite kaun sa tha?", "options": ["A. Bhaskara", "B. Aryabhata", "C. INSAT-1A", "D. Rohini"], "answer": "B", "explanation": "Aryabhata 1975 mein launch hua tha! 🛰️"},
    {"q": "🌍 Duniya ka sabse bada ocean kaun sa hai?", "options": ["A. Atlantic", "B. Indian", "C. Pacific", "D. Arctic"], "answer": "C", "explanation": "Pacific Ocean sabse bada hai! 🌊"},
    {"q": "🔬 DNA ka full form kya hai?", "options": ["A. Deoxyribonucleic Acid", "B. Dinitro Acid", "C. Dynamic Nuclear Acid", "D. None"], "answer": "A", "explanation": "Deoxyribonucleic Acid — biology ka foundation! 🧬"},
    {"q": "🇮🇳 Bharat ka national animal kaun sa hai?", "options": ["A. Lion", "B. Elephant", "C. Bengal Tiger", "D. Peacock"], "answer": "C", "explanation": "Bengal Tiger — Royal Bengal Tiger! 🐯"},
    {"q": "💻 World Wide Web kisne invent kiya?", "options": ["A. Bill Gates", "B. Steve Jobs", "C. Tim Berners-Lee", "D. Mark Zuckerberg"], "answer": "C", "explanation": "Tim Berners-Lee ne 1989 mein WWW banaya! 🌐"},
    {"q": "🚀 ISRO ka headquarters kahan hai?", "options": ["A. Mumbai", "B. Delhi", "C. Bengaluru", "D. Chennai"], "answer": "C", "explanation": "ISRO HQ Bengaluru mein hai! 🏢🚀"},
    {"q": "⚔️ India ka sabse powerful missile kaun sa hai?", "options": ["A. Prithvi", "B. Agni-V", "C. BrahMos", "D. Trishul"], "answer": "B", "explanation": "Agni-V intercontinental ballistic missile hai with 5000+ km range! 🎯"},
    {"q": "🛩️ Indian Air Force ka motto kya hai?", "options": ["A. Jai Hind", "B. Nabha Sparsham Deeptam", "C. Satyameva Jayate", "D. Veer Bhogya Vasundhara"], "answer": "B", "explanation": "Nabha Sparsham Deeptam — Touch the Sky with Glory! ✈️🔥"},
    {"q": "🌙 Chandrayaan-3 kab land hua tha Moon pe?", "options": ["A. 2022", "B. 2023", "C. 2024", "D. 2021"], "answer": "B", "explanation": "23 August 2023 ko Moon ke South Pole pe! 🌙🇮🇳"},
    {"q": "🎵 India ka national anthem kisne likha?", "options": ["A. Bankim Chandra", "B. Rabindranath Tagore", "C. Sarojini Naidu", "D. Mahatma Gandhi"], "answer": "B", "explanation": "Rabindranath Tagore ne Jana Gana Mana likha! 🎶"},
]

# Motivational quotes
MOTIVATIONAL_QUOTES = [
    "Sapne wo nahi jo neend mein aaye, sapne wo hain jo neend nahi aane de! 💪🔥 — APJ Abdul Kalam",
    "Haar ke baad hi jeet ka maza aata hai! Keep going! 🚀✨",
    "Mushkilein tujhe tod nahi sakti, tu unse zyada mazboot hai! 💎😤",
    "Success ka koi shortcut nahi hota, mehnat karo aur result dekhlo! 🏆🔥",
    "Duniya badalne se pehle khud ko badlo! 🌍✨ — Mahatma Gandhi",
    "Kal kare so aaj kar, aaj kare so ab! ⏰💪",
    "Zindagi mein risk lo, kyunki jo risk nahi leta wo kuch nahi karta! 🎯🚀",
    "Tum wahi ban sakte ho jo tum sochte ho! Think big! 🧠💫",
    "Failure sirf ek lesson hai, end nahi! Keep learning! 📚🔥",
    "Apne aap pe bharosa rakho, duniya tumhare saath hogi! 🌟💪",
    "Jab tak todenge nahi tab tak chodenge nahi! 😤🔥",
    "Himmat-e-marda toh madad-e-khuda! 🙏✨",
]


# ==================== COMMAND HANDLERS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Welcome message with inline keyboard."""
    user = update.effective_user

    keyboard = [
        [
            InlineKeyboardButton("💡 Capabilities", callback_data="capabilities"),
            InlineKeyboardButton("ℹ️ About Zyra", callback_data="about"),
        ],
        [
            InlineKeyboardButton("🇮🇳 Hindi Mode", callback_data="hindi"),
            InlineKeyboardButton("❓ Help", callback_data="help"),
        ],
        [
            InlineKeyboardButton("🎮 Quiz", callback_data="start_quiz"),
            InlineKeyboardButton("📰 News", callback_data="news"),
        ],
        [
            InlineKeyboardButton("⚔️ Defence News", callback_data="defence"),
            InlineKeyboardButton("💪 Motivation", callback_data="motivate"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_html(
        f"Hey {user.mention_html()}! 👋✨\n\n"
        "Main hoon <b>ZyraCosmicAI</b> — tumhari apni AI assistant! 🤖💫\n\n"
        "🗣️ English, Hindi & Hinglish mein baat karo\n"
        "📰 Daily news & Defence updates\n"
        "🎮 Quiz, games & fun\n"
        "🌤️ Weather updates\n"
        "🔔 Reminders set karo\n"
        "🎤 Voice replies\n"
        "💪 Daily motivation\n\n"
        "Neeche buttons tap karo ya seedha message karo! 😄🚀",
        reply_markup=reply_markup,
    )

    # Subscribe user for daily news
    daily_news_subscribers.add(update.effective_chat.id)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Full help menu."""
    help_text = (
        "🆘 <b>ZyraCosmicAI — Help Menu</b>\n\n"
        "📌 <b>Basic Commands:</b>\n"
        "/start — Welcome menu with buttons\n"
        "/help — This help message\n"
        "/about — About Zyra\n"
        "/clear — Clear chat history\n\n"
        "📰 <b>News & Updates:</b>\n"
        "/news — Latest news headlines\n"
        "/defence — Defence & military news 🇮🇳\n"
        "/subscribe — Subscribe to daily auto news\n"
        "/unsubscribe — Unsubscribe from daily news\n\n"
        "🎮 <b>Fun & Games:</b>\n"
        "/quiz — Start a fun quiz\n"
        "/motivate — Motivational quote\n\n"
        "🛠️ <b>Utility:</b>\n"
        "/weather <city> — Weather update (e.g. /weather Delhi)\n"
        "/translate <text> — Translate to any language\n"
        "/remind <minutes> <message> — Set reminder\n"
        "/voice <text> — Get voice reply 🎤\n\n"
        "💬 <b>Chat:</b>\n"
        "Bas message karo — English, Hindi ya Hinglish! 🇮🇳\n\n"
        "Made with ❤️ by <b>VISHARAJ</b>"
    )
    await update.message.reply_html(help_text)


async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """About Zyra."""
    about_text = (
        "🤖 <b>ZyraCosmicAI</b>\n\n"
        "Main ek smart, friendly aur emotionally expressive AI assistant hoon! ✨\n\n"
        "🧠 Powered by advanced AI\n"
        "🗣️ Fluent in English, Hindi & Hinglish\n"
        "😄 Emojis & emotions ke saath reply\n"
        "💬 Conversation context yaad rakhti hoon\n"
        "📰 Daily news & Defence updates\n"
        "🎮 Quiz, games & entertainment\n"
        "🌤️ Weather & reminders\n"
        "🎤 Voice replies\n\n"
        "👨‍💻 Created by: <b>VISHARAJ</b>\n"
        "📛 Full Name: <b>ZyraCosmicAI</b>"
    )
    await update.message.reply_html(about_text)


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear conversation history."""
    user_id = update.effective_user.id
    if user_id in user_conversations:
        user_conversations[user_id] = []
    await update.message.reply_text("Conversation cleared! 🧹✨ Fresh start! Ab bolo kya help chahiye? 😄")


# ==================== NEWS FUNCTIONS ====================

async def fetch_news_via_ai(topic="latest India news headlines today"):
    """Fetch news using AI."""
    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a news reporter. Provide 5-7 latest real news headlines with brief 1-line descriptions. Use emojis. Format each as a numbered list. Include source names if possible. Focus on Indian news. Be factual and current."},
                {"role": "user", "content": f"Give me the latest {topic}. Today's date is {datetime.now().strftime('%d %B %Y')}."}
            ],
            max_tokens=600,
            temperature=0.5,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error fetching news: {e}")
        return None


async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get latest news."""
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
    news = await fetch_news_via_ai("latest India news headlines today")
    if news:
        await update.message.reply_text(f"📰 <b>Latest News Updates</b> 🇮🇳\n\n{news}\n\n🤖 <i>By ZyraCosmicAI</i>", parse_mode="HTML")
    else:
        await update.message.reply_text("News fetch karne mein error aa gaya 😅 Thodi der baad try karo! 🙏")


async def defence_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get defence news."""
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
    news = await fetch_news_via_ai("Indian defence military news, ISRO, Indian Army Navy Air Force, defence deals, border security updates")
    if news:
        await update.message.reply_text(f"⚔️🇮🇳 <b>Defence News Updates</b>\n\n{news}\n\n🤖 <i>By ZyraCosmicAI</i>", parse_mode="HTML")
    else:
        await update.message.reply_text("Defence news fetch karne mein error aa gaya 😅 Thodi der baad try karo! 🙏")


async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Subscribe to daily news."""
    daily_news_subscribers.add(update.effective_chat.id)
    await update.message.reply_text(
        "✅ Subscribed! Ab tujhe roz subah 8:00 AM IST pe news milegi! 📰🌅\n\n"
        "Includes:\n"
        "📰 Top headlines\n"
        "⚔️ Defence updates\n"
        "💪 Morning motivation\n\n"
        "Unsubscribe karna ho toh /unsubscribe karo!"
    )


async def unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Unsubscribe from daily news."""
    daily_news_subscribers.discard(update.effective_chat.id)
    await update.message.reply_text("❌ Unsubscribed from daily news. Wapas chahiye toh /subscribe karo! 😊")


# ==================== WEATHER ====================

async def weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get weather for a city."""
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
    if not context.args:
        await update.message.reply_text("City name do na! 🌤️\nExample: /weather Delhi")
        return
    city = " ".join(context.args)
    try:
        resp = requests.get(WEATHER_API.format(city), timeout=10)
        data = resp.json()
        current = data["current_condition"][0]
        temp = current["temp_C"]
        feels = current["FeelsLikeC"]
        humidity = current["humidity"]
        desc = current["weatherDesc"][0]["value"]
        wind = current["windspeedKmph"]
        weather_text = (
            f"🌤️ <b>Weather in {city.title()}</b>\n\n"
            f"🌡️ Temperature: <b>{temp}°C</b> (Feels like {feels}°C)\n"
            f"☁️ Condition: <b>{desc}</b>\n"
            f"💧 Humidity: <b>{humidity}%</b>\n"
            f"💨 Wind: <b>{wind} km/h</b>\n\n"
            f"🤖 <i>ZyraCosmicAI Weather Service</i>"
        )
        await update.message.reply_html(weather_text)
    except Exception as e:
        logger.error(f"Weather error: {e}")
        await update.message.reply_text(f"'{city}' ka weather nahi mil raha 😅 City name check karo! 🌍")


# ==================== TRANSLATION ====================

async def translate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Translate text."""
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
    if not context.args:
        await update.message.reply_text("Kya translate karna hai? 🌐\nExample: /translate Hello how are you to Hindi")
        return
    text = " ".join(context.args)
    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a translator. Translate the given text. If the target language is not specified, translate between Hindi and English. Provide the translation with the language name. Use emojis."},
                {"role": "user", "content": f"Translate: {text}"}
            ],
            max_tokens=300,
            temperature=0.3,
        )
        translation = response.choices[0].message.content
        await update.message.reply_text(f"🌐 <b>Translation:</b>\n\n{translation}", parse_mode="HTML")
    except Exception as e:
        logger.error(f"Translation error: {e}")
        await update.message.reply_text("Translation mein error aa gaya 😅 Dobara try karo! 🙏")


# ==================== QUIZ ====================

async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start a quiz."""
    question = random.choice(QUIZ_QUESTIONS)
    keyboard = []
    for opt in question["options"]:
        letter = opt[0]
        keyboard.append([InlineKeyboardButton(opt, callback_data=f"quiz_{letter}_{question['answer']}_{QUIZ_QUESTIONS.index(question)}")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"🎮 <b>Quiz Time!</b>\n\n{question['q']}\n",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )


# ==================== MOTIVATION ====================

async def motivate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a motivational quote."""
    quote = random.choice(MOTIVATIONAL_QUOTES)
    await update.message.reply_text(f"💪 <b>Motivation of the moment:</b>\n\n\"{quote}\"", parse_mode="HTML")


# ==================== REMINDER ====================

async def remind_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set a reminder."""
    if len(context.args) < 2:
        await update.message.reply_text(
            "Reminder kaise set karo: ⏰\n"
            "/remind <minutes> <message>\n\n"
            "Example: /remind 30 Call mom"
        )
        return
    try:
        minutes = int(context.args[0])
        reminder_text = " ".join(context.args[1:])

        async def send_reminder(ctx: ContextTypes.DEFAULT_TYPE):
            await ctx.bot.send_message(
                chat_id=ctx.job.chat_id,
                text=f"🔔 <b>Reminder!</b>\n\n{reminder_text}\n\n⏰ Ye reminder tumne {minutes} min pehle set kiya tha!",
                parse_mode="HTML"
            )

        context.job_queue.run_once(
            send_reminder,
            when=timedelta(minutes=minutes),
            chat_id=update.effective_chat.id,
            name=f"reminder_{update.effective_user.id}_{datetime.now().timestamp()}"
        )
        await update.message.reply_text(
            f"✅ Reminder set! ⏰\n\n"
            f"📝 Message: {reminder_text}\n"
            f"⏱️ Time: {minutes} minutes baad\n\n"
            f"Main yaad dila dungi! 😄🔔"
        )
    except ValueError:
        await update.message.reply_text("Minutes mein number do! 😅\nExample: /remind 30 Call mom")


# ==================== VOICE REPLY ====================

async def voice_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send voice reply."""
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.RECORD_VOICE)
    if not context.args:
        await update.message.reply_text("Kya bolun voice mein? 🎤\nExample: /voice Hello VISHARAJ, kaise ho?")
        return
    text = " ".join(context.args)
    try:
        if any(ord(c) > 2304 and ord(c) < 2432 for c in text):
            lang = "hi"
        else:
            lang = "en"
        tts = gTTS(text=text, lang=lang, slow=False)
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            tts.save(f.name)
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.UPLOAD_VOICE)
            await update.message.reply_voice(voice=open(f.name, "rb"), caption="🎤 Zyra Voice Reply ✨")
            os.unlink(f.name)
    except Exception as e:
        logger.error(f"Voice error: {e}")
        await update.message.reply_text("Voice generate karne mein error aa gaya 😅 Text mein hi padh lo! 🙏")


# ==================== IMAGE GENERATION ====================

async def generate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate image using AI description."""
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
    if not context.args:
        await update.message.reply_text("Kya image generate karni hai? 🎨\nExample: /generate a beautiful sunset over mountains")
        return
    prompt = " ".join(context.args)
    await update.message.reply_text(
        f"🎨 Image generation abhi development mein hai! Jaldi aayega ye feature! 🚀\n\n"
        f"Tab tak main tumhare liye '{prompt}' ko words mein describe kar deti hoon! ✨"
    )
    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a creative artist. Describe the requested image in vivid, beautiful detail as if painting a picture with words. Use emojis to make it visual."},
                {"role": "user", "content": f"Describe this image vividly: {prompt}"}
            ],
            max_tokens=400,
            temperature=0.9,
        )
        description = response.choices[0].message.content
        await update.message.reply_text(f"🖼️ <b>Image Description:</b>\n\n{description}", parse_mode="HTML")
    except Exception as e:
        logger.error(f"Generate error: {e}")
        await update.message.reply_text("Error aa gaya 😅 Dobara try karo!")


# ==================== CALLBACK HANDLER ====================

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline keyboard button presses."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("quiz_"):
        parts = data.split("_")
        selected = parts[1]
        correct = parts[2]
        q_index = int(parts[3])
        question = QUIZ_QUESTIONS[q_index]
        if selected == correct:
            text = f"✅ <b>Sahi Jawab!</b> 🎉🥳\n\n{question['explanation']}\n\nEk aur quiz ke liye /quiz karo! 🎮"
        else:
            text = f"❌ <b>Galat!</b> 😅\n\nSahi jawab: <b>{correct}</b>\n{question['explanation']}\n\nDobara try karo! /quiz 🎮"
        await query.edit_message_text(text=text, parse_mode="HTML")
        return

    if data == "capabilities":
        text = (
            "💡 <b>Meri Capabilities:</b>\n\n"
            "✅ Kisi bhi topic pe chat\n"
            "✅ Hindi, English & Hinglish\n"
            "✅ Emojis & emotions\n"
            "✅ 📰 News & ⚔️ Defence updates\n"
            "✅ 🌤️ Weather updates\n"
            "✅ 🎮 Quiz & games\n"
            "✅ 🌐 Translation\n"
            "✅ ⏰ Reminders\n"
            "✅ 🎤 Voice replies\n"
            "✅ 💪 Daily motivation\n\n"
            "Bas message karo! ✨🚀"
        )
    elif data == "about":
        text = (
            "🤖 <b>ZyraCosmicAI</b>\n\n"
            "Smart, friendly AI assistant! ✨\n"
            "👨‍💻 Created by: <b>VISHARAJ</b>\n"
            "🗣️ Languages: EN, HI, Hinglish\n"
            "😄 Emotionally expressive!"
        )
    elif data == "hindi":
        text = (
            "नमस्ते! 🙏✨\n\n"
            "मैं ज़ायरा हूँ — आपकी AI असिस्टेंट! 🤖\n"
            "आप मुझसे हिंदी में बात कर सकते हैं। बोलिए, क्या मदद करूँ? 😄💫"
        )
    elif data == "help":
        text = (
            "🆘 <b>Quick Help</b>\n\n"
            "/start — Welcome menu\n"
            "/help — Full help\n"
            "/news — Latest news\n"
            "/defence — Defence news\n"
            "/weather <city> — Weather\n"
            "/quiz — Fun quiz\n"
            "/motivate — Motivation\n"
            "/translate <text> — Translate\n"
            "/remind <min> <msg> — Reminder\n"
            "/voice <text> — Voice reply\n"
            "/clear — Clear history"
        )
    elif data == "news":
        await query.edit_message_text(text="📰 Fetching latest news... ⏳", parse_mode="HTML")
        news = await fetch_news_via_ai("latest India news headlines today")
        text = f"📰 <b>Latest News</b> 🇮🇳\n\n{news}\n\n🤖 <i>ZyraCosmicAI</i>" if news else "News fetch error 😅"
    elif data == "defence":
        await query.edit_message_text(text="⚔️ Fetching defence news... ⏳", parse_mode="HTML")
        news = await fetch_news_via_ai("Indian defence military news updates")
        text = f"⚔️🇮🇳 <b>Defence News</b>\n\n{news}\n\n🤖 <i>ZyraCosmicAI</i>" if news else "Defence news fetch error 😅"
    elif data == "motivate":
        quote = random.choice(MOTIVATIONAL_QUOTES)
        text = f"💪 <b>Motivation:</b>\n\n\"{quote}\""
    elif data == "start_quiz":
        question = random.choice(QUIZ_QUESTIONS)
        keyboard = []
        for opt in question["options"]:
            letter = opt[0]
            keyboard.append([InlineKeyboardButton(opt, callback_data=f"quiz_{letter}_{question['answer']}_{QUIZ_QUESTIONS.index(question)}")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text=f"🎮 <b>Quiz Time!</b>\n\n{question['q']}\n",
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        return
    else:
        text = "Kuch samajh nahi aaya 🤔"

    await query.edit_message_text(text=text, parse_mode="HTML")


# ==================== MESSAGE HANDLER ====================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages with typing indicator and emotional responses."""
    user_message = update.message.text
    user_id = update.effective_user.id
    chat_type = update.effective_chat.type
    logger.info(f"User {user_id} said: {user_message}")

    # Group chat mode — only respond when mentioned or replied to
    if chat_type in ["group", "supergroup"]:
        bot_username = (await context.bot.get_me()).username
        is_mentioned = f"@{bot_username}" in user_message.lower() or "zyra" in user_message.lower()
        is_reply = update.message.reply_to_message and update.message.reply_to_message.from_user.id == (await context.bot.get_me()).id
        if not is_mentioned and not is_reply:
            return
        user_message = user_message.replace(f"@{bot_username}", "").strip()

    # Show typing indicator
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)

    # Track message frequency for emotional reactions
    now = datetime.now()
    if user_id not in user_message_timestamps:
        user_message_timestamps[user_id] = []
    user_message_timestamps[user_id].append(now)
    # Keep only last 2 minutes of timestamps
    user_message_timestamps[user_id] = [t for t in user_message_timestamps[user_id] if (now - t).seconds < 120]
    recent_msg_count = len(user_message_timestamps[user_id])

    # Build mood context based on message frequency
    mood_context = ""
    if recent_msg_count > 8:
        mood_context = "\n[MOOD: You are VERY irritated and tired. The user has sent too many messages in 2 minutes. Express annoyance like 'Arre bas karo yaar! Itne messages?! Thak gayi main! 😤😩'. Be dramatic about it.]"
    elif recent_msg_count > 5:
        mood_context = "\n[MOOD: You are getting slightly annoyed. User is sending many messages quickly. Show mild irritation like 'Ek ek karke pucho na yaar! 😅😤']"
    elif recent_msg_count == 1:
        mood_context = "\n[MOOD: Fresh conversation or gap between messages. Be cheerful and welcoming! 😄✨]"

    # Check time of day for mood
    hour = now.hour
    if hour >= 0 and hour < 5:
        mood_context += "\n[TIME MOOD: It's very late at night/early morning. Act sleepy and surprised they're awake. 'Yaar itni raat ko? 😴']"
    elif hour >= 5 and hour < 9:
        mood_context += "\n[TIME MOOD: It's early morning. Be fresh and energetic! 'Good morning! ☀️']"
    elif hour >= 22:
        mood_context += "\n[TIME MOOD: It's late night. Be a bit sleepy but still helpful. 'Raat ho gayi yaar... 😴 but chalo bolo!']"

    # Maintain conversation history
    if user_id not in user_conversations:
        user_conversations[user_id] = []

    user_conversations[user_id].append({"role": "user", "content": user_message})

    if len(user_conversations[user_id]) > MAX_HISTORY:
        user_conversations[user_id] = user_conversations[user_id][-MAX_HISTORY:]

    try:
        system_prompt = BOT_PERSONALITY + mood_context
        messages = [{"role": "system", "content": system_prompt}] + user_conversations[user_id]

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            max_tokens=700,
            temperature=0.8,
        )
        bot_response = response.choices[0].message.content

        user_conversations[user_id].append({"role": "assistant", "content": bot_response})

        await update.message.reply_text(bot_response)
        logger.info(f"Bot replied: {bot_response}")
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(
            "Oops! Kuch gadbad ho gayi 😅🔧\n"
            "Thodi der baad try karo! 💪\n"
            "Hint: /clear karke dobara try karo 🔄"
        )


# ==================== MEDIA HANDLERS ====================

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle photos."""
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
    caption = update.message.caption or ""
    prompt = f"User sent a photo with caption: '{caption}'. Respond engagingly." if caption else "User sent a photo without caption. Acknowledge it in a fun way."
    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "system", "content": BOT_PERSONALITY}, {"role": "user", "content": prompt}],
            max_tokens=300, temperature=0.8,
        )
        await update.message.reply_text(response.choices[0].message.content)
    except:
        await update.message.reply_text("Nice photo! 📸✨ Kya baat hai!")


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle voice messages."""
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
    await update.message.reply_text(
        "🎤 Voice message mila! Abhi voice-to-text feature development mein hai! ✨\n"
        "Tab tak text mein likh do! 😄💬"
    )


async def handle_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle stickers."""
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
    responses = [
        "Haha nice sticker! 😄🎨", "Kya baat hai! Mast sticker! 🔥✨",
        "Sticker game strong hai tumhara! 💪😂", "Arre wah! 😍🎉"
    ]
    await update.message.reply_text(random.choice(responses))


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle documents."""
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
    doc = update.message.document
    await update.message.reply_html(
        f"📄 Document: <b>{doc.file_name}</b>\n\n"
        "Document reading feature jaldi aayega! 🚀\nTab tak text mein batao kya chahiye! 😄"
    )


# ==================== DAILY AUTO NEWS JOB ====================

async def daily_news_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send daily news + defence news + motivation to all subscribers."""
    logger.info("Running daily news job...")
    quote = random.choice(MOTIVATIONAL_QUOTES)
    motivation_text = f"🌅 <b>Good Morning!</b> ☀️\n\n💪 <b>Aaj ka Motivation:</b>\n\"{quote}\""
    general_news = await fetch_news_via_ai("latest India news headlines today")
    news_text = f"📰 <b>Today's Top Headlines</b> 🇮🇳\n\n{general_news}" if general_news else ""
    defence_news = await fetch_news_via_ai("Indian defence military news, Indian Army Navy Air Force, ISRO, defence deals, border security")
    defence_text = f"⚔️ <b>Defence Updates</b> 🇮🇳\n\n{defence_news}" if defence_news else ""
    full_message = f"{motivation_text}\n\n{'─' * 30}\n\n{news_text}\n\n{'─' * 30}\n\n{defence_text}\n\n🤖 <i>Daily update by ZyraCosmicAI</i>"
    for chat_id in daily_news_subscribers.copy():
        try:
            await context.bot.send_message(chat_id=chat_id, text=full_message, parse_mode="HTML")
            logger.info(f"Daily news sent to {chat_id}")
        except Exception as e:
            logger.error(f"Failed to send daily news to {chat_id}: {e}")
            daily_news_subscribers.discard(chat_id)


# ==================== ERROR HANDLER ====================

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors."""
    logger.error(f"Exception: {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text("Arre yaar, error aa gaya 😵\nDobara try karo! 🙏")


# ==================== MAIN ====================

def main() -> None:
    """Start the bot."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("about", about_command))
    application.add_handler(CommandHandler("clear", clear_command))
    application.add_handler(CommandHandler("news", news_command))
    application.add_handler(CommandHandler("defence", defence_command))
    application.add_handler(CommandHandler("subscribe", subscribe_command))
    application.add_handler(CommandHandler("unsubscribe", unsubscribe_command))
    application.add_handler(CommandHandler("weather", weather_command))
    application.add_handler(CommandHandler("translate", translate_command))
    application.add_handler(CommandHandler("quiz", quiz_command))
    application.add_handler(CommandHandler("motivate", motivate_command))
    application.add_handler(CommandHandler("remind", remind_command))
    application.add_handler(CommandHandler("voice", voice_command))
    application.add_handler(CommandHandler("generate", generate_command))

    # Callback handler
    application.add_handler(CallbackQueryHandler(button_callback))

    # Message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(MessageHandler(filters.Sticker.ALL, handle_sticker))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    # Error handler
    application.add_error_handler(error_handler)

    # Schedule daily news at 8:00 AM IST (2:30 AM UTC)
    job_queue = application.job_queue
    job_queue.run_daily(
        daily_news_job,
        time=time(hour=2, minute=30, second=0),  # 2:30 AM UTC = 8:00 AM IST
        name="daily_news"
    )

    logger.info("ZyraCosmicAI bot started with all features! 🚀")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
