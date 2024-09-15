from postgre_db_handler import DatabaseHandler
import logging
logging.basicConfig(level=logging.INFO)


db_handler = DatabaseHandler(db_name='discord_bot_dev.db')

habits = db_handler.get_habits_in_channel(int(1282069079099707402))
print(len(habits))
print()
user_habits = db_handler.get_user_habits(261152275945226240)
print(len(user_habits))

for i in range(1, 12):
    db_handler.remove_habit_by_id(i)