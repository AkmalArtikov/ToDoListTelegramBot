from telegram import Updater
import telegram
import pickle
from datetime import timedelta


DAYS = ("Today", "Tomorrow", "One Week Later", "Someday")


class WaitingTypes:
    def __init__(self):
        pass

    DATE = 1
    NUMBER = 2
    NOTHING = 3


class Task(object):
    def __init__(self, title):
        self.title = title

    def get_title(self):
        return self.title


class User(object):
    def __init__(self):
        self.tasks = {}
        self.waiting_type = WaitingTypes.NOTHING
        self.temp_task = ""

    def wait_for(self):
        return self.waiting_type

    def set_wait_type(self, waiting_type):
        self.waiting_type = waiting_type

    def set_temp_title(self, title):
        self.temp_task = Task(title)
        self.waiting_type = WaitingTypes.DATE

    def add_task(self, date):
        date_key = date
        if date != DAYS[3]:
            date_key = "{:%d, %b %Y}".format(date)

        if date_key in self.tasks:
            self.tasks[date_key].append(self.temp_task)
        else:
            self.tasks[date_key] = [self.temp_task]

        self.waiting_type = WaitingTypes.NOTHING

    def delete_task(self, number):
        deleted_task = ""
        task_counter = 0

        for date in self.tasks:
            if date != DAYS[3]:
                deleted_task = self.delete_task_in_date(task_counter, date, number)
                if deleted_task != "":
                    return deleted_task
                else:
                    task_counter += len(self.tasks[date])

        if DAYS[3] in self.tasks:
            deleted_task = self.delete_task_in_date(task_counter, DAYS[3], number)
            if deleted_task != "":
                return deleted_task

        return deleted_task

    def delete_task_in_date(self, task_counter, date, number):
        counter = task_counter
        for i in range(len(self.tasks[date])):
            counter += 1
            if counter == number:
                task = self.tasks[date][i]
                del self.tasks[date][i]
                if len(self.tasks[date]) == 0:
                    self.tasks.pop(date, None)
                return task.get_title() + " at " + date
        return ""

    def get_tasks(self):
        return self.tasks


class Bot(object):
    def __init__(self, refresh_users):
        self.updater = Updater(token="178290745:AAH_Vrkyg5f5C0NkOSUCs7kKaXcv__wUT90")
        self.dispatcher = self.updater.dispatcher

        self.dispatcher.addTelegramCommandHandler('start', self.start)
        self.dispatcher.addTelegramCommandHandler('help', self.help)
        self.dispatcher.addTelegramCommandHandler('add', self.add)
        self.dispatcher.addTelegramCommandHandler('done', self.done)
        self.dispatcher.addTelegramCommandHandler('show', self.show)
        self.dispatcher.addTelegramMessageHandler(self.echo)
        self.dispatcher.addUnknownTelegramCommandHandler(self.unknown)

        self.help_message = "The next commands are available:\n" \
                            + "- type '/start' to resend a greeting message\n" \
                            + "- type '/help' to see the help message with the list of a commands\n" \
                            + "- type '/add title' to add task with given title\n" \
                            + "- type '/done' to mark tasks as done\n" \
                            + "- type '/show' to see the full list of tasks\n"

        if refresh_users:
            self.users = {}
        else:
            try:
                with open("users.pickle", 'rb') as f:
                    self.users = pickle.load(f)
            except IOError:
                self.users = {}

    def start_polling(self):
        self.updater.start_polling()

    def save(self):
        with open("users.pickle", 'wb') as f:
            pickle.dump(self.users, f)

    def start(self, telegram_bot, update):
        chat_id = update.message.chat_id
        reply_markup = telegram.ReplyKeyboardHide()
        text = "ToDo List Bot for easy and effective task management.\n" + self.help_message
        telegram_bot.sendMessage(chat_id=chat_id, text=text, reply_markup=reply_markup)

        if update.message.chat_id not in self.users:
            self.users[chat_id] = User()

        self.refresh_wait_type(self.get_user(chat_id))
        self.save()

    def help(self, telegram_bot, update):
        chat_id = update.message.chat_id
        self.refresh_wait_type(self.get_user(chat_id))
        reply_markup = telegram.ReplyKeyboardHide()
        telegram_bot.sendMessage(chat_id=chat_id, text=self.help_message, reply_markup=reply_markup)

    def show(self, telegram_bot, update):
        chat_id = update.message.chat_id
        self.refresh_wait_type(self.get_user(chat_id))
        user = self.get_user(chat_id)
        tasks = user.get_tasks()

        if len(tasks) == 0:
            reply_markup = telegram.ReplyKeyboardHide()
            telegram_bot.sendMessage(chat_id=chat_id, text="There are no tasks for you!",
                                     reply_markup=reply_markup)
            return

        task_counter = 1
        for date in tasks:
            if date != DAYS[3]:
                task_counter = self.show_task_in_date(tasks, date, chat_id, task_counter, telegram_bot)

        if DAYS[3] in tasks:
            self.show_task_in_date(tasks, DAYS[3], chat_id, task_counter, telegram_bot)

    @staticmethod
    def show_task_in_date(tasks, date, chat_id, task_counter, telegram_bot):
        text = "Tasks for " + date
        for task in tasks[date]:
            text += "\n " + str(task_counter) + ") " + task.get_title()
            task_counter += 1

        reply_markup = telegram.ReplyKeyboardHide()
        telegram_bot.sendMessage(chat_id=chat_id, text=text, reply_markup=reply_markup)
        return task_counter

    def add(self, telegram_bot, update):
        chat_id = update.message.chat_id
        user = self.get_user(chat_id)
        self.refresh_wait_type(user)

        if update.message.text.strip() == "/add":
            reply_markup = telegram.ReplyKeyboardHide()
            telegram_bot.sendMessage(chat_id=chat_id, text="Please, send task in the following format:\n"
                                                           "'/add task_title'", reply_markup=reply_markup)
            return

        text = update.message.text[5:].strip()
        user.set_temp_title(text)
        reply_markup = self.get_date_keyboard()
        telegram_bot.sendMessage(chat_id=chat_id, text="Task with title '" + text + "' will be added to ToDo "
                                                                                    "List!\nPlease, set task date",
                                                                                    reply_markup=reply_markup)
        self.save()

    def done(self, telegram_bot, update):
        chat_id = update.message.chat_id
        user = self.get_user(chat_id)
        self.refresh_wait_type(user)
        reply_markup = telegram.ReplyKeyboardHide()

        if update.message.text.strip() == "/done":
            if len(user.get_tasks()) != 0:
                telegram_bot.sendMessage(chat_id=chat_id, text="Please, enter done tasks' numbers separated by space "
                                                               "in the following format:\n'/done done_task_number"
                                                               " another_task_number'", reply_markup=reply_markup)

            self.show(telegram_bot, update)
            user.set_wait_type(WaitingTypes.NUMBER)
        else:
            numbers = update.message.text[6:].strip().split()

            try:
                for i in range(len(numbers)):
                    numbers[i] = int(numbers[i])
                numbers = list(set(numbers))
            except ValueError:
                telegram_bot.sendMessage(chat_id=chat_id, text="There are no tasks with such numbers",
                                         reply_markup=reply_markup)
                return

            deleted_tasks = []
            for i in range(len(numbers)):
                result = user.delete_task(numbers[i])
                if result != "":
                    deleted_tasks.append(result)
                    for j in range(len(numbers)):
                        if i != j and numbers[j] > numbers[i]:
                            numbers[j] -= 1

            if len(deleted_tasks) != 0:
                text = "Next tasks were deleted:\n"
                for task in deleted_tasks:
                    text += "- " + task + "\n"
            else:
                text = "There are no tasks with such numbers"

            user.set_wait_type(WaitingTypes.NOTHING)
            telegram_bot.sendMessage(chat_id=chat_id, text=text, reply_markup=reply_markup)

        self.save()

    def echo(self, telegram_bot, update):
        chat_id = update.message.chat_id
        user = self.get_user(chat_id)
        text = update.message.text.strip()

        if user.wait_for() == WaitingTypes.DATE:

            if text not in DAYS:
                reply_markup = self.get_date_keyboard()
                telegram_bot.sendMessage(chat_id=update.message.chat_id, text="Please, choose date for the task",
                                         reply_markup=reply_markup)
                return

            delta = timedelta(days=0)
            if text == DAYS[1]:
                delta = timedelta(days=1)
            elif text == DAYS[2]:
                delta = timedelta(days=7)
            date = update.message.date + delta

            if text == DAYS[3]:
                user.add_task(DAYS[3])
            else:
                user.add_task(date)

            reply_markup = telegram.ReplyKeyboardHide()
            if text != DAYS[3]:
                telegram_bot.sendMessage(chat_id=update.message.chat_id, text="Task was successfully added at the"
                                                                              " {:%d, %b %Y}".format(date),
                                                                              reply_markup=reply_markup)
            else:
                telegram_bot.sendMessage(chat_id=update.message.chat_id, text="Task was successfully added at Someday",
                                         reply_markup=reply_markup)

            self.save()
        elif user.wait_for() == WaitingTypes.NUMBER:
            telegram_bot.sendMessage(chat_id=update.message.chat_id, text="Please, enter numbers for done tasks in the"
                                                                          "following format:\n'/done done_task_number"
                                                                          " another_task_number'")
            return
        else:
            telegram_bot.sendMessage(chat_id=update.message.chat_id, text="If you want add task with title '" + text +
                                                                          "' you should send task in the following "
                                                                          "format:\n'/add task_title'")

    def unknown(self, telegram_bot, update):
        chat_id = update.message.chat_id
        self.refresh_wait_type(self.get_user(chat_id))
        reply_markup = telegram.ReplyKeyboardHide()
        text = "Sorry, I didn't understand that command." + self.help_message
        telegram_bot.sendMessage(chat_id=chat_id, text=text, reply_markup=reply_markup)

    def get_user(self, chat_id):
        return self.users[chat_id]

    @staticmethod
    def get_date_keyboard():
        custom_keyboard = [
            [DAYS[0], DAYS[1]],
            [DAYS[2], DAYS[3]]
        ]
        reply_markup = telegram.ReplyKeyboardMarkup(keyboard=custom_keyboard, one_time_keyboard=True)
        return reply_markup

    @staticmethod
    def refresh_wait_type(user):
        if user.wait_for() == WaitingTypes.NUMBER or user.wait_for() == WaitingTypes.DATE:
            user.set_wait_type(WaitingTypes.NOTHING)


if __name__ == '__main__':
    bot = Bot(False)
    bot.start_polling()
