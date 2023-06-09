# Import telebot and schedule
import telebot
from telebot.async_telebot import AsyncTeleBot
from telebot import types

#Async states - replacing next step handlers
from telebot.asyncio_storage import StateMemoryStorage
from telebot.asyncio_handler_backends import State, StatesGroup
from telebot import asyncio_filters

# Python libs
import logging
import asyncio
import aioschedule
import time
import datetime

#Files - users_db, config
import config
import users_config
from default_exercises import daily_default, full_body_default

logging.basicConfig(filename='bot.log', level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

bot = AsyncTeleBot(token=config.TOKEN, state_storage=StateMemoryStorage())
users_tmp = users_config.users

class UserStates(StatesGroup):
    ask_schedule = State()
    data_gathered = State()
    
@bot.message_handler(commands=['start'])
async def start(message):
    # Send the initial greeting message
    msg = f'<i>Ага, вот ты и попался!</i>'
    await bot.send_message(message.chat.id, msg, parse_mode='html')
    user_id = message.chat.id

    # Define a dictionary to store user data
    user_data = {'user_id': '', 'gender': '', 'schedule': [], 'personal_program': []}
    user_data['user_id'] = user_id
    # Send a question asking for gender with buttons
    markup1 = telebot.types.InlineKeyboardMarkup()
    g1 = telebot.types.InlineKeyboardButton('М', callback_data = 'male')
    g2 = telebot.types.InlineKeyboardButton('Ж', callback_data = 'female')
   
    markup1.add(g1, g2)
    await bot.send_message(message.chat.id, 'Говори быстро, ты кто?!', reply_markup=markup1)
    await bot.set_state(message.from_user.id, UserStates.ask_schedule, message.chat.id)

@bot.callback_query_handler(func=lambda call: True)
async def process_gender_step(call):
    # Process the answer for gender question
    gender = call.data
    user_data = {'user_id': call.message.chat.id, 'gender': gender, 'schedule': []}
    await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='Говори быстро, ты кто?!')
    # Send a question asking for days of the week with comma-separated values
    await bot.send_message(call.message.chat.id, 'Записал')
    id_list = [i['user_id'] for i in users_tmp]
    if user_data['user_id'] not in id_list:
        users_tmp.append(user_data)
    await bot.send_message(call.message.chat.id, 'В какие дни пойдёшь в зал?! Напиши через запятую!')

@bot.message_handler(state=UserStates.ask_schedule)
async def process_schedule_step(message):
    # async with bot.retrieve_data(message.from_user.id, message.chat.id) as user_data:
    usr_schedule = message.text
    user_id = message.chat.id
    days = ['понедельник', "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
    
    # Check if the schedule is provided in a comma-separated format
    if ',' not in usr_schedule and usr_schedule.lower() not in days:
        await bot.send_message(user_id, 'Шутки шутить вздумал? А ну-ка соберись и введи дни нормально!')
        await bot.set_state(user_id, UserStates.ask_schedule, message.chat.id)
        return 
    
    # Check if there is only one day in schedule
    elif ',' not in usr_schedule and usr_schedule.lower() in days:
        await bot.send_message(message.chat.id, 'Всего один день? Слабовато. Но, надеюсь, со временем ты исправишься! Я прослежу, чтобы не сачковал тут...')
        def_schedule = 0
        for d in days: 
            if usr_schedule.lower() == d:
                def_schedule = days.index(d)
        for i in users_tmp:
            if i['user_id'] == message.chat.id:
                i['schedule'] = def_schedule
        await bot.set_state(message.from_user.id, UserStates.data_gathered, message.chat.id)
        return
    
    # Update the user data dictionary with the schedule if user provides bot with multiple days
    
    usr_schedule = [i.strip() for i in usr_schedule.split(',')]
    for i in usr_schedule:
        if i.lower() not in days:
            await bot.send_message(message.chat.id, 'Шутки шутить вздумал? А ну-ка соберись и введи дни нормально!')
            await bot.set_state(user_id, UserStates.ask_schedule, message.chat.id)
            return
    def_schedule = []
    for i in days:
        for d in usr_schedule:
            if d.lower() == i:
                def_schedule.append(days.index(i))
    for i in users_tmp:
        if i['user_id'] == message.chat.id: 
            i['schedule'] = def_schedule

    markup2 = types.ReplyKeyboardMarkup(resize_keyboard=True)
    b1 = telebot.types.KeyboardButton("Программа")
    markup2.add(b1)
    await bot.send_message(message.chat.id, 'Отлично, запомнил!', reply_markup=markup2)
    update_list_of_users(users_tmp)
    await bot.set_state(message.from_user.id, UserStates.data_gathered, message.chat.id)
    
@bot.message_handler(commands=['change_schedule'])
async def change_schedule(message):
    await bot.set_state(message.from_user.id, UserStates.ask_schedule)
    await bot.send_message(message.chat.id, 'Поменять решил? Ну ладно, перечисляй. Записываю!')
        
@bot.message_handler(commands=['help'], state=UserStates.data_gathered)
async def handle_help(message):
    bot_commands = [x for l in config.COMMANDS for x in l]
    await bot.send_message(message.chat.id, f'Чем тебе помочь? Напиши так, чтобы я мог разобрать! \n Список команд: {bot_commands} \n Чтобы напомнить программу напиши: "Программа"! ')
    
@bot.message_handler(content_types=['text'], state=UserStates.data_gathered)
async def handle_text(message):
    if message.text not in config.CHAT_WORD_COMMANDS:
        await bot.send_message(message.chat.id, 'Не могу разобрать что ты там бормочешь, иди лучше сделай растяжку и спину выпрями, а то сидишь как собака сутулая')
    elif message.text == "Программа":
        for usr in users_tmp:
            usr_vals = [i for i in usr.values()]
            user_id, gender, user_schedule = usr_vals[0], usr_vals[1], usr_vals[2]
            exercises = []
            if user_id == message.chat.id:
                if datetime.datetime.now().weekday() not in user_schedule:
                    for ex in daily_default:
                        if ex['gender'] == gender:
                            tmp_ex = ex['exercises']
                            am = ex['amount']
                            exercises.append(f'{tmp_ex[0]}, {am[0]} раз')
                            exercises.append(f'{tmp_ex[1]}, {am[1]}')
                            msg = f'{exercises[0]},\n {exercises[1]}'
                            await bot.send_message(message.chat.id, msg)
                elif datetime.datetime.now().weekday() in user_schedule:
                    for ex in full_body_default:
                        if ex['gender'] == gender:
                            exercises = ex['exercises'] 
                            msg = "\n".join(exercises)
                            await bot.send_message(message.chat.id, msg)                     

def upate_users_tmp(users):
    for usr in users:
        if 'personal_program' not in usr:
            usr.update({'personal_program': []})

def update_list_of_users(users_tmp):
    users_tmp = upate_users_tmp(users=users_tmp)
    with open('users_config.py', 'w') as f:
        f.write(f'users = {users_tmp}')
    users = users_config.users
    return users

def get_daily(users):
    daily = []
    for user in users: 
        if datetime.datetime.now().weekday() not in user['schedule']:
            daily.append((user['user_id'], user['gender']))
    return daily

async def send_morning_notification(users):
    daily = get_daily(users=users)
    gym = [usr['user_id'] for usr in users if datetime.datetime.now().weekday() in usr['schedule']]
    for usr in daily:
        msg = 'Доброе утро! В зал ты сегодня, конечно, не идёшь, но не забудь немного подвигаться. Я прослежу!😉'
        await bot.send_message(chat_id=usr[0], text=msg)
    for uid in gym:
        msg = 'Доброе утро! Надеюсь, ты не забыл собрать сумку в качалку!😉'
        await bot.send_message(chat_id=uid, text=msg)

async def send_walk(users):
    daily = get_daily(users=users)
    for usr in daily:
        msg = 'Пойдёшь домой - выйди на пару остановок раньше и пройдись пешком, хоть воздухом подышишь!'
        await bot.send_message(chat_id=usr[0], text=msg)
    
async def send_daily(users):
    daily = get_daily(users=users)
    msg_f = 'Маловато двигаешься! Ну-ка присядь-ка 20 раз!'
    msg_m = "Ты там к стулу не прирос? А ну-ка упал отжался 25 раз!"
    msg_p = 'Неплохой день, но будет грустно если ты не сделаешь минуту планки пока он ещё не закончился! Вперёд!'
    if time.strftime("%H", time.localtime()) == '11' or  time.strftime("%H", time.localtime()) == '18':
        for usr in daily:
            if usr[1] == 'female':
                await bot.send_message(chat_id=usr[0], text=msg_f)
            elif usr[1] == 'male':
                await bot.send_message(chat_id=usr[0], text=msg_m)
    elif time.strftime("%H:%M", time.localtime()) == '20:00':
        for usr in daily:
            await bot.send_message(chat_id=usr[0], text=msg_p)

users = update_list_of_users(users_tmp) 

# async def run_test(users):
#     for usr in users:
#         usr_id = usr['user_id']
#         await bot.send_message(chat_id=usr_id, text='testing, attention please')

async def scheduler():
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)

bot.add_custom_filter(asyncio_filters.StateFilter(bot))
bot.add_custom_filter(asyncio_filters.IsDigitFilter())

aioschedule.every().day.at('05:30').do(send_morning_notification, users)
aioschedule.every().day.at('11:00').do(send_daily, users)
aioschedule.every().day.at('15:30').do(send_walk, users)
aioschedule.every().day.at('18:00').do(send_daily, users)
aioschedule.every().day.at('20:00').do(send_daily, users)
aioschedule.every().hour.do(update_list_of_users, users_tmp)

async def main():
    await asyncio.gather(bot.infinity_polling(), scheduler())

if __name__ == '__main__':
    asyncio.run(main())

    