import telebot
from telebot import types
from telebot_calendar import Calendar, CallbackData, ENGLISH_LANGUAGE
import datetime
import sqlite3
from itertools import groupby
from operator import itemgetter

token = input("Pleade input the token of your bot: ")
bot = telebot.TeleBot(token)
calendar = Calendar(language=ENGLISH_LANGUAGE)
calendar_1 = CallbackData('calendar_1', 'action', 'year', 'month', 'day')
now = datetime.datetime.now()

conn = sqlite3.connect('tasks.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        user_id INTEGER,
        task_date TEXT,
        task_name TEXT
    )
''')
conn.commit()
conn.close()

# bot start and button output
@bot.message_handler(commands=['start'])
def start(message):
    keyboard = types.ReplyKeyboardMarkup(True)
    button1 = types.KeyboardButton('✅ Add task')
    button2 = types.KeyboardButton('Show tasks')
    button3 = types.KeyboardButton('Help')
    keyboard.add(button1)
    keyboard.add(button2)
    keyboard.add(button3)
    bot.send_message(message.chat.id, 'Hello, ' + message.from_user.first_name + '!', reply_markup=keyboard)


@bot.message_handler(commands=['help'])
def hepling(message):
    bot.send_message(message.chat.id, '''
⏰ Add reminders so you don't forget important things
''')


@bot.message_handler(content_types=['text'])
def call(message):
    if message.text == '✅ Add task':
        bot.send_message(message.chat.id, 'Which date do you want to add a task to?', reply_markup=calendar.create_calendar(
            name=calendar_1.prefix,
            year=now.year,
            month=now.month)
                         )
    elif message.text == 'Show tasks':
        todos = get_tasks_for_user(message.chat.id)
        if not todos:
            bot.send_message(message.chat.id, 'No tasks')
        else:
            grouped_by_date = {key: list(group) for key, group in groupby(todos, key=itemgetter(0))}
            for date in grouped_by_date:
                tasks_text = '\n'.join(f'- {task[1]}' for task in grouped_by_date[date])
                text = f'Tasks for {date}:\n{tasks_text}'
                keyboard = types.InlineKeyboardMarkup()
                for task in grouped_by_date[date]:
                    button = types.InlineKeyboardButton(text=f'❌ {task[1]}', callback_data=f'delete:{date}:{task[1]}')
                    keyboard.add(button)
                bot.send_message(message.chat.id, text, reply_markup=keyboard)    

    elif message.text == 'Help':
        bot.send_message(message.chat.id, '''
⏰ Add reminders so you don't forget important things
''')
    else:
        bot.send_message(message.chat.id, "🙄 I don't understand... Press 'Add task' in the menu")

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete:'))
def delete_callback(call):
    _, date, task = call.data.split(':')
    delete_task(call.message.chat.id, date, task)
    bot.answer_callback_query(call.id, text=f'Task "{task}" on {date} deleted')

@bot.callback_query_handler(func=lambda call: call.data.startswith(calendar_1.prefix))
def callback_inline(call: types.CallbackQuery):
    name, action, year, month, day = call.data.split(calendar_1.sep)
    date = calendar.calendar_query_handler(bot=bot, call=call, name=name, action=action, year=year, month=month,
                                           day=day)
    if action == 'DAY':
        c_date = date.strftime("%d.%m.%Y")
        bot.send_message(chat_id=call.from_user.id, text=f'You chose {c_date}')
        msg = bot.send_message(chat_id=call.from_user.id, text='What to plan: ')
        bot.register_next_step_handler(msg, lambda message: add_task(message, chat_id=call.from_user.id, c_date=c_date))
    elif action == 'CANCEL':
        bot.send_message(chat_id=call.from_user.id, text='🚫 Cancelled')

def add_task(message, chat_id, c_date):
    conn = sqlite3.connect('tasks.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO tasks (user_id, task_date, task_name) VALUES (?, ?, ?)', (chat_id, c_date, message.text))
    conn.commit()
    conn.close()
    text = f'Task successfully added on {c_date}'
    bot.send_message(chat_id=chat_id, text=text)

def delete_task(chat_id, c_date, task):
    conn = sqlite3.connect('tasks.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM tasks WHERE user_id=? AND task_name=? AND task_date=?', (chat_id, task, c_date))
    conn.commit()
    conn.close()

def get_tasks_for_user(user_id):
    conn = sqlite3.connect('tasks.db')
    cursor = conn.cursor()
    cursor.execute('SELECT task_date, task_name FROM tasks WHERE user_id=?', (user_id,))
    tasks = cursor.fetchall()
    conn.close()
    tasks = sorted(tasks, key=get_date)
    return tasks

def get_date(item):
    dmy = item[0].split('.')
    return int(dmy[2]) * 10000 + int(dmy[1]) * 100 + int(dmy[0])


bot.polling(none_stop=True)