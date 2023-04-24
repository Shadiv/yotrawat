from telebot.asyncio_handler_backends import State, StatesGroup

TOKEN='token'
COMMANDS = ['start']
CHAT_WORD_COMMANDS = ['Программа']
# days = {"понедельник": 0,
#         "вторник": 1,
#         "среда": 2,
#         "четверг": 3,
#         "пятница": 4,
#         "суббота": 5,
#         "воскресенье": 6}

class UserStates(StatesGroup):
    user_id = State()
    gender = State()
    schedule = State()

# set_state -> sets a new state
# delete_state -> delets state if exists
# get_state -> returns state if exists

