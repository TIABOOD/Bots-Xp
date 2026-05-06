import asyncio
import json
import os
from datetime import datetime, timedelta
from highrise import BaseBot, User
from highrise.models import User as HighriseUser, Position
import random

class XPBot(BaseBot):
    def __init__(self):
        super().__init__()
        self.load_config()
        self.load_xp_data()
        self.load_questions()
        self.user_join_time = {}  # تتبع وقت دخول المستخدم
        self.user_message_count = {}  # عداد الرسائل
        self.last_question_time = {}  # آخر وقت سؤال لكل مستخدم
        
    def load_config(self):
        """تحميل الإعدادات من config.json"""
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                self.config = json.load(f)
                self.bot_token = self.config.get('bot_token')
                self.room_id = self.config.get('room_id')
                self.owner_username = self.config.get('owner_username')
        except FileNotFoundError:
            print("❌ Error: config.json not found!")
            exit(1)
    
    def load_xp_data(self):
        """تحميل بيانات XP من JSON"""
        if os.path.exists('xp_data.json'):
            with open('xp_data.json', 'r', encoding='utf-8') as f:
                self.xp_data = json.load(f)
        else:
            self.xp_data = {}
    
    def save_xp_data(self):
        """حفظ بيانات XP في JSON"""
        with open('xp_data.json', 'w', encoding='utf-8') as f:
            json.dump(self.xp_data, f, ensure_ascii=False, indent=2)
    
    def load_questions(self):
        """تحميل الأسئلة من questions.json"""
        try:
            with open('questions.json', 'r', encoding='utf-8') as f:
                self.questions = json.load(f)
        except FileNotFoundError:
            print("⚠️ Warning: questions.json not found!")
            self.questions = []
    
    async def on_start(self):
        """عند بدء البوت"""
        print(f"✅ Bot started!")
        print(f"🏠 Room ID: {self.room_id}")
        print(f"👑 Owner: {self.owner_username}")
        print(f"📊 XP Data loaded: {len(self.xp_data)} users")
        print(f"❓ Questions loaded: {len(self.questions)}")
    
    async def on_user_join(self, user: HighriseUser, position: Position):
        """عند دخول مستخدم الروم"""
        username = user.username
        self.user_join_time[username] = datetime.now()
        self.user_message_count[username] = 0
        self.last_question_time[username] = datetime.now()
        
        # تهيئة بيانات المستخدم
        if username not in self.xp_data:
            self.xp_data[username] = {
                'xp': 0,
                'level': 1,
                'join_date': datetime.now().isoformat()
            }
            self.save_xp_data()
        
        await self.chat(f"👋 مرحباً {username}! أهلاً وسهلاً في الروم.")
        print(f"✅ {username} joined the room")
        
        # بدء نظام الوقت (كل ساعة = 10 XP)
        asyncio.create_task(self.time_system(username))
    
    async def on_user_left(self, user: HighriseUser):
        """عند مغادرة مستخدم الروم"""
        username = user.username
        if username in self.user_join_time:
            del self.user_join_time[username]
        if username in self.user_message_count:
            del self.user_message_count[username]
        print(f"❌ {username} left the room")
    
    async def on_chat(self, user: HighriseUser, message: str):
        """عند إرسال رسالة"""
        username = user.username
        
        # نظام الرسائل (كل 50 رسالة = 5 XP)
        if username not in self.user_message_count:
            self.user_message_count[username] = 0
        
        self.user_message_count[username] += 1
        
        if self.user_message_count[username] % 50 == 0:
            await self.add_xp(username, 5, "💬 نظام الرسائل (50 رسالة)")
        
        # التحقق من الأوامر
        if message.startswith('/'):
            await self.handle_command(user, message)
        
        # نظام الأسئلة - الإجابة على سؤال
        if hasattr(self, 'current_question') and self.current_question:
            correct_answer = self.current_question['answer']
            if message.strip().upper() == correct_answer.upper():
                await self.add_xp(username, 5, "❓ نظام الأسئلة (إجابة صحيحة)")
                self.current_question = None
                await self.chat(f"✅ إجابة صحيحة يا {username}! +5 XP")
    
    async def time_system(self, username: str):
        """نظام الوقت: كل ساعة = 10 XP"""
        while username in self.user_join_time:
            await asyncio.sleep(3600)  # انتظر ساعة واحدة
            if username in self.user_join_time:
                await self.add_xp(username, 10, "⏰ نظام الوقت (ساعة واحدة)")
    
    async def question_system(self):
        """نظام الأسئلة: سؤال كل 10 دقائق"""
        while True:
            await asyncio.sleep(600)  # كل 10 دقائق
            
            if len(self.questions) > 0:
                self.current_question = random.choice(self.questions)
                question_text = self.current_question['question']
                options = self.current_question['options']
                
                options_text = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(options)])
                await self.chat(f"❓ سؤال: {question_text}\n{options_text}\n(أجب بالخيار الصحيح: A, B, C, أو D)")
    
    async def add_xp(self, username: str, xp_amount: int, source: str):
        """إضافة XP للمستخدم"""
        if username not in self.xp_data:
            self.xp_data[username] = {
                'xp': 0,
                'level': 1,
                'join_date': datetime.now().isoformat()
            }
        
        self.xp_data[username]['xp'] += xp_amount
        self.xp_data[username]['level'] = self.xp_data[username]['xp'] // 100 + 1
        self.save_xp_data()
        
        print(f"✅ {username} +{xp_amount} XP from {source} (Total: {self.xp_data[username]['xp']})")
    
    async def handle_command(self, user: HighriseUser, message: str):
        """التعامل مع الأوامر"""
        username = user.username
        command = message.split()[0].lower()
        
        if command == '/xp':
            await self.cmd_xp(user)
        elif command == '/leaderboard':
            await self.cmd_leaderboard()
        elif command == '/question':
            await self.cmd_question()
        elif command == '/help':
            await self.cmd_help()
        elif command == '/reset' and username == self.owner_username:
            await self.cmd_reset(user, message)
        elif command == '/resetall' and username == self.owner_username:
            await self.cmd_resetall()
        else:
            await self.chat(f"❌ أمر غير معروف: {command}")
    
    async def cmd_xp(self, user: HighriseUser):
        """أمر عرض XP"""
        username = user.username
        if username in self.xp_data:
            data = self.xp_data[username]
            await self.chat(
                f"📊 {username}:\n"
                f"XP: {data['xp']}\n"
                f"Level: {data['level']}"
            )
        else:
            await self.chat(f"❌ لا توجد بيانات لك يا {username}")
    
    async def cmd_leaderboard(self):
        """أمر عرض أفضل اللاعبين"""
        sorted_users = sorted(
            self.xp_data.items(),
            key=lambda x: x[1]['xp'],
            reverse=True
        )[:10]
        
        leaderboard = "🏆 **Leaderboard Top 10:**\n"
        for i, (username, data) in enumerate(sorted_users, 1):
            leaderboard += f"{i}. {username} - {data['xp']} XP (Level {data['level']})\n"
        
        await self.chat(leaderboard)
    
    async def cmd_question(self):
        """أمر طلب سؤال"""
        if len(self.questions) > 0:
            self.current_question = random.choice(self.questions)
            question_text = self.current_question['question']
            options = self.current_question['options']
            
            options_text = "\n".join([f"{chr(65+i)}. {opt}" for i, opt in enumerate(options)])
            await self.chat(f"❓ {question_text}\n{options_text}")
        else:
            await self.chat("❌ لا توجد أسئلة متاحة!")
    
    async def cmd_help(self):
        """أمر المساعدة"""
        help_text = (
            "📖 **الأوامر المتاحة:**\n"
            "/xp - عرض XP الخاص بك\n"
            "/leaderboard - أفضل 10 لاعبين\n"
            "/question - اطلب سؤال\n"
            "/help - هذه الرسالة\n\n"
            "⏰ **نظام الوقت:** كل ساعة = 10 XP\n"
            "❓ **نظام الأسئلة:** كل 10 دقائق سؤال = 5 XP\n"
            "💬 **نظام الرسائل:** كل 50 رسالة = 5 XP"
        )
        await self.chat(help_text)
    
    async def cmd_reset(self, user: HighriseUser, message: str):
        """أمر تصفير XP (للمالك فقط)"""
        parts = message.split()
        if len(parts) < 2:
            await self.chat("❌ الاستخدام: /reset @username")
            return
        
        target_user = parts[1].replace('@', '')
        if target_user in self.xp_data:
            self.xp_data[target_user] = {
                'xp': 0,
                'level': 1,
                'join_date': datetime.now().isoformat()
            }
            self.save_xp_data()
            await self.chat(f"✅ تم تصفير XP للمستخدم {target_user}")
        else:
            await self.chat(f"❌ لم يتم العثور على المستخدم {target_user}")
    
    async def cmd_resetall(self):
        """أمر تصفير جميع البيانات (للمالك فقط)"""
        self.xp_data = {}
        self.save_xp_data()
        await self.chat("⚠️ تم تصفير جميع بيانات XP!")

if __name__ == "__main__":
    bot = XPBot()
    bot.run()
