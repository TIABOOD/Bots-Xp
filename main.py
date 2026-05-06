import asyncio
import json
import os
from datetime import datetime
from highrise import BaseBot, User, SessionMetadata
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
        self.current_question = None
        self.current_question_user = None
        
    def load_config(self):
        """تحميل الإعدادات من config.json"""
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                self.config = json.load(f)
                self.bot_token = self.config.get('bot_token')
                self.room_id = self.config.get('room_id')
                self.owner_username = self.config.get('owner_username')
                print(f"✅ Config loaded")
                print(f"🏠 Room ID: {self.room_id}")
                print(f"👑 Owner: {self.owner_username}")
        except FileNotFoundError:
            print("❌ Error: config.json not found!")
            exit(1)
    
    def load_xp_data(self):
        """تحميل بيانات XP من JSON"""
        if os.path.exists('xp_data.json'):
            with open('xp_data.json', 'r', encoding='utf-8') as f:
                self.xp_data = json.load(f)
                print(f"✅ XP data loaded: {len(self.xp_data)} users")
        else:
            self.xp_data = {}
            print("✅ New XP data created")
    
    def save_xp_data(self):
        """حفظ بيانات XP في JSON"""
        with open('xp_data.json', 'w', encoding='utf-8') as f:
            json.dump(self.xp_data, f, ensure_ascii=False, indent=2)
    
    def load_questions(self):
        """تحميل الأسئلة من questions.json"""
        try:
            with open('questions.json', 'r', encoding='utf-8') as f:
                self.questions = json.load(f)
                print(f"✅ Questions loaded: {len(self.questions)} questions")
        except FileNotFoundError:
            print("⚠️ Warning: questions.json not found!")
            self.questions = []
    
    async def on_start(self, session_metadata: SessionMetadata):
        """عند بدء البوت"""
        print(f"\n🤖 === BOT STARTED ===")
        print(f"📊 Version: {session_metadata.sdk_version if hasattr(session_metadata, 'sdk_version') else 'v25.1'}")
        print(f"✅ Bot is ready!\n")
        
        # بدء نظام الأسئلة
        asyncio.create_task(self.question_loop())
    
    async def on_user_join(self, user: User):
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
        
        try:
            await self.chat(f"👋 مرحباً {username}! أهلاً وسهلاً في الروم. 🎮")
        except:
            pass
        
        print(f"✅ {username} joined the room")
        
        # بدء نظام الوقت
        asyncio.create_task(self.time_system(username))
    
    async def on_user_leave(self, user: User):
        """عند مغادرة مستخدم الروم"""
        username = user.username
        if username in self.user_join_time:
            del self.user_join_time[username]
        if username in self.user_message_count:
            del self.user_message_count[username]
        print(f"❌ {username} left the room")
    
    async def on_chat(self, user: User, message: str):
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
        if self.current_question and self.current_question_user == username:
            correct_answer = self.current_question['answer']
            if message.strip().upper() == correct_answer.upper():
                await self.add_xp(username, 5, "❓ نظام الأسئلة (إجابة صحيحة)")
                try:
                    await self.chat(f"✅ إجابة صحيحة يا {username}! +5 XP 🎉")
                except:
                    pass
                self.current_question = None
                self.current_question_user = None
    
    async def time_system(self, username: str):
        """نظام الوقت: كل ساعة = 10 XP"""
        while username in self.user_join_time:
            await asyncio.sleep(3600)  # انتظر ساعة واحدة
            if username in self.user_join_time:
                await self.add_xp(username, 10, "⏰ نظام الوقت (ساعة واحدة)")
    
    async def question_loop(self):
        """حلقة الأسئلة: سؤال كل 10 دقائق"""
        await asyncio.sleep(5)  # انتظر قليلاً
        while True:
            await asyncio.sleep(600)  # كل 10 دقائق
            
            if len(self.questions) > 0 and len(self.user_join_time) > 0:
                # اختر مستخدم عشوائي من المتصلين
                users = list(self.user_join_time.keys())
                if users:
                    self.current_question_user = random.choice(users)
                    self.current_question = random.choice(self.questions)
                    question_text = self.current_question['question']
                    options = self.current_question['options']
                    
                    options_text = "\n".join([f"{chr(65+i)}. {opt}" for i, opt in enumerate(options)])
                    try:
                        await self.chat(f"❓ سؤال جديد:\n{question_text}\n{options_text}\n(أجب بالخيار الصحيح: A, B, C, أو D)")
                    except:
                        pass
    
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
    
    async def handle_command(self, user: User, message: str):
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
            try:
                await self.chat(f"❌ أمر غير معروف: {command}")
            except:
                pass
    
    async def cmd_xp(self, user: User):
        """أمر عرض XP"""
        username = user.username
        if username in self.xp_data:
            data = self.xp_data[username]
            try:
                await self.chat(
                    f"📊 {username}:\n"
                    f"💰 XP: {data['xp']}\n"
                    f"🎖️ Level: {data['level']}"
                )
            except:
                pass
        else:
            try:
                await self.chat(f"❌ لا توجد بيانات لك يا {username}")
            except:
                pass
    
    async def cmd_leaderboard(self):
        """أمر عرض أفضل اللاعبين"""
        if not self.xp_data:
            try:
                await self.chat("❌ لا توجد بيانات حالياً")
            except:
                pass
            return
        
        sorted_users = sorted(
            self.xp_data.items(),
            key=lambda x: x[1]['xp'],
            reverse=True
        )[:10]
        
        leaderboard = "🏆 **Leaderboard Top 10:**\n"
        for i, (username, data) in enumerate(sorted_users, 1):
            leaderboard += f"{i}. {username} - {data['xp']} XP (Level {data['level']})\n"
        
        try:
            await self.chat(leaderboard)
        except:
            pass
    
    async def cmd_question(self):
        """أمر طلب سؤال"""
        if len(self.questions) > 0:
            self.current_question = random.choice(self.questions)
            question_text = self.current_question['question']
            options = self.current_question['options']
            
            options_text = "\n".join([f"{chr(65+i)}. {opt}" for i, opt in enumerate(options)])
            try:
                await self.chat(f"❓ {question_text}\n{options_text}")
            except:
                pass
        else:
            try:
                await self.chat("❌ لا توجد أسئلة متاحة!")
            except:
                pass
    
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
        try:
            await self.chat(help_text)
        except:
            pass
    
    async def cmd_reset(self, user: User, message: str):
        """أمر تصفير XP (للمالك فقط)"""
        parts = message.split()
        if len(parts) < 2:
            try:
                await self.chat("❌ الاستخدام: /reset @username")
            except:
                pass
            return
        
        target_user = parts[1].replace('@', '')
        if target_user in self.xp_data:
            self.xp_data[target_user] = {
                'xp': 0,
                'level': 1,
                'join_date': datetime.now().isoformat()
            }
            self.save_xp_data()
            try:
                await self.chat(f"✅ تم تصفير XP للمستخدم {target_user}")
            except:
                pass
        else:
            try:
                await self.chat(f"❌ لم يتم العثور على المستخدم {target_user}")
            except:
                pass
    
    async def cmd_resetall(self):
        """أمر تصفير جميع البيانات (للمالك فقط)"""
        self.xp_data = {}
        self.save_xp_data()
        try:
            await self.chat("⚠️ تم تصفير جميع بيانات XP!")
        except:
            pass

async def main():
    """الدالة الرئيسية"""
    bot = XPBot()
    
    try:
        # تشغيل البوت
        await bot.run(
            token=bot.bot_token,
            room_id=bot.room_id
        )
    except KeyboardInterrupt:
        print("\n\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")

if __name__ == "__main__":
    import sys
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        sys.exit(0)
