import bot_app
import users_config
import schedule
import time

users_tmp = users_config.users
users = bot_app.update_list_of_users(bot_app.users_tmp)
schedule.every().day.at('05:30').do(bot_app.send_morning_notification, users)
schedule.every().day.at('11:00').do(bot_app.send_daily, users)
schedule.every().day.at('17:00').do(bot_app.send_daily, users)
schedule.every().day.at('20:15').do(bot_app.send_daily, users)
schedule.every().hour.do(bot_app.update_list_of_users, users_tmp)

while True:
    schedule.run_pending()
    time.sleep(1)