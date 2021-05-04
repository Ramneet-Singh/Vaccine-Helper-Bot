import logging

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update, ParseMode
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext,
    Defaults,
)

from service import getVaccineAvailability

import json
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
USER_CONFIGS_PATH = os.getenv("USER_CONFIGS_PATH")

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

CHOOSE, PIN, STATE, DISTRICT, AGE, MODE = range(6)

stateDict = json.load(open("state.json", "r"))
districtDict = json.load(open("district.json", "r"))

usersDict = {}


def getStateCode(stateName: str) -> int:
    found = False
    code = 0
    for stateField in stateDict:
        if stateField["state_name"].upper() == stateName.upper():
            found, code = True, stateField['state_id']
    if not found:
        raise Exception("Couldn't find state!")
    return code


def getDistrictCode(stateCode: int, districtName: str) -> int:
    found, code = False, 0
    if str(stateCode) not in districtDict.keys():
        raise Exception("State Code Not Found!")

    for districtField in districtDict[str(stateCode)]:
        if districtField['district_name'].upper() == districtName.upper():
            found, code = True, districtField['district_id']
    if not found:
        raise Exception("Couldn't find district!")
    return code


def start(update: Update, _: CallbackContext) -> int:
    reply_keyboard = [["1"], ["2"]]

    update.message.reply_text(
        'Hi! My name is Vaccine Bot.'
        'Send /cancel to stop talking to me.\n\n'
        'Choose how you would like to search for available slots:\n'
        '1. Using State and District Name (Recommended Method)\n'
        '2. Using Pincode\n'
        'Enter 1 or 2 only',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True),
    )

    return CHOOSE


def choose(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user
    usePIN = True if (update.message.text == "2") else False
    logger.info("Choice made by %s: %s", user.first_name,
                ("PIN Code" if usePIN else "State & District"))

    context.user_data["usePIN"] = usePIN
    if usePIN:
        update.message.reply_text(
            "Please enter PIN Code", reply_markup=ReplyKeyboardRemove(),
        )
        return PIN
    else:
        update.message.reply_text(
            "Please enter your State",
            reply_markup=ReplyKeyboardRemove(),
        )
        return STATE


def state(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user
    stateName = update.message.text
    logger.info("State of %s: %s", user.first_name, stateName)

    if stateName.upper() not in [stateField["state_name"].upper() for stateField in stateDict]:
        update.message.reply_text('Please enter the full name of the state')
        return STATE

    assert(context.user_data['usePIN'] == False)
    context.user_data['stateCode'] = getStateCode(stateName)

    update.message.reply_text(
        'Please enter your District',
    )

    return DISTRICT


def district(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user
    districtName = update.message.text
    logger.info("District of %s: %s", user.first_name, districtName)

    assert(context.user_data["usePIN"] == False)
    try:
        stateCode = context.user_data["stateCode"]
        context.user_data["districtCode"] = getDistrictCode(
            stateCode, districtName)
    except Exception as e:
        update.message.reply_text("Transaction Failed: " + str(e.args[0]))
        return ConversationHandler.END

    reply_keyboard = [["1"], ["2"]]
    update.message.reply_text(
        'Please select the age group to search for:\n'
        '1. 18+ years old\n'
        '2. 45+ years old\n'
        'Enter 1 or 2 only',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True)
    )

    return AGE


def pin(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user
    pincode = update.message.text
    logger.info("PIN Code of %s: %s", user.first_name, pincode)

    if not (pincode.isdecimal() and len(pincode) == 6):
        update.message.reply_text("Please enter a valid PIN Code")
        return PIN

    context.user_data['PIN'] = pincode

    reply_keyboard = [["1"], ["2"]]
    update.message.reply_text(
        'Please select the age group to search for:\n'
        '1. 18+ years old\n'
        '2. 45+ years old\n'
        'Enter 1 or 2 only',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True)
    )

    return AGE


def age(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user
    is18Plus = True if update.message.text == "1" else False
    logger.info("Age Group of %s: %s", user.first_name,
                "18+" if is18Plus else "45+")

    context.user_data['is18Plus'] = is18Plus

    reply_keyboard = [["1"], ["2"]]
    update.message.reply_text(
        'Choose the mode:\n'
        '1. Subscribe for receiving regular updates\n'
        '2. Check only once for slots available now\n'
        'Enter 1 or 2 only',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True)
    )

    return MODE


def mode(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user
    oneTime = True if update.message.text == "2" else False
    logger.info("Mode of %s: %s", user.first_name,
                "One-Time"if oneTime else "Subscribe")

    context.user_data["oneTime"] = oneTime
    context.user_data["chatId"] = update.message.chat.id

    if not oneTime:
        fileName = USER_CONFIGS_PATH+str(update.message.chat.id)+"-config.json"
        userFile = open(fileName, "w")
        json.dump(context.user_data, userFile)

        update.message.reply_text(
            "Your request has been sent. Thank you!", reply_markup=ReplyKeyboardRemove())
    else:
        args = [context.user_data["chatId"],
                context.user_data["usePIN"], context.user_data["is18Plus"]]
        if context.user_data["usePIN"]:
            args.append(context.user_data["PIN"])
        else:
            args.append(context.user_data["stateCode"])
            args.append(context.user_data["districtCode"])
        context.job_queue.run_once(
            fetchCurrentAvailableSlots, when=15, context=args)
        update.message.reply_text(
            "Thank you! Fetching available slots", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def cancel(update: Update, _: CallbackContext) -> int:
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text(
        'Bye! Stay safe!', reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


def sessionMsgTemplate(session, index):
    response = f'\n<b>Center {index}: {session["name"]}</b>\n'
    response += f'<b>Fee Type</b>: {  "Free" if session["fee_type"]=="Free" else ("Paid <b>(Rs. " + session["fee"] + ")</b>")}\n'
    response += f'<b>Age Group</b>: {str(session["min_age_limit"]) + "+"}\n'
    response += f'<b>Vaccine</b>: {session["vaccine"]}\n'
    response += f'<b>Date</b>: {session["date"]}\n'
    response += f'<b>Available Capacity</b>: {session["available_capacity"]}\n'
    response += f'<b>Slots:</b>\n'
    for slot in session["slots"]:
        response += f'\t{slot}\n'
    return response


def fetchCurrentAvailableSlots(context):
    chat_id = context.job.context[0]
    usePIN = context.job.context[1]
    is18Plus = context.job.context[2]
    if usePIN:
        pincode = context.job.context[3]
        availableSessions = getVaccineAvailability(pincode, True, is18Plus)
    else:
        stateCode = context.job.context[3]
        districtCode = context.job.context[4]
        availableSessions = getVaccineAvailability(
            districtCode, False, is18Plus)

    if len(availableSessions) > 0:
        context.bot.send_message(
            chat_id=chat_id, text="Here are available slots in the next 2 days:")
        idx = 1
        for session in availableSessions:
            context.bot.send_message(
                chat_id=chat_id, text=sessionMsgTemplate(session, idx))
            idx = idx + 1
    else:
        context.bot.send_message(
            chat_id=chat_id, parse_mode="HTML", text="There are no available slots in the next 2 days.\nPlease check back later or subscribe for updates")


def checkForAvailableSlots(context: CallbackContext):
    directory = os.fsencode(USER_CONFIGS_PATH)

    for file in os.listdir(directory):
        filename = os.fsdecode(file)
        userConfig = json.load(
            open(os.path.join(USER_CONFIGS_PATH, filename), "r"))
        if userConfig["usePIN"]:
            availableSessions = getVaccineAvailability(
                userConfig["PIN"], True, userConfig["is18Plus"])
        else:
            availableSessions = getVaccineAvailability(
                userConfig["districtCode"], False, userConfig["is18Plus"])

        if len(availableSessions) > 0:
            context.bot.send_message(
                chat_id=userConfig["chatId"], text="Hi! Here are the available vaccine slots for the next 2 days:")
            idx = 1
            for session in availableSessions:
                context.bot.send_message(
                    chat_id=userConfig["chatId"], text=sessionMsgTemplate(session, idx))
                idx = idx + 1
        else:
            context.bot.send_message(
                chat_id=userConfig["chatId"], text="Hi! There are no available vaccine slots for the next 2 days.")


def sendToEachUser(update: Update, context: CallbackContext) -> None:
    bot = context.bot
    for user in usersDict:
        bot.send_message(
            chat_id=user,
            text=f'Hi User with State Code {usersDict[user]["stateCode"]} and District Code {usersDict[user]["districtCode"]}'
        )


def main() -> None:
    # Create the Updater and pass it your bot's token.
    updater = Updater(TELEGRAM_TOKEN, defaults=Defaults(
        parse_mode=ParseMode.HTML))

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Add conversation handler with the states STATE and DISTRICT
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSE: [MessageHandler(Filters.text(["1", "2"]), choose)],
            STATE: [MessageHandler(Filters.text & ~Filters.command, state)],
            DISTRICT: [MessageHandler(Filters.text & ~Filters.command, district)],
            PIN: [MessageHandler(Filters.text & ~Filters.command, pin)],
            AGE: [MessageHandler(Filters.text(["1", "2"]), age)],
            MODE: [MessageHandler(Filters.text(["1", "2"]), mode)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dispatcher.add_handler(conv_handler)

    dispatcher.add_handler(CommandHandler("send", sendToEachUser))
    # Start the Bot
    updater.start_polling()

    updater.job_queue.run_repeating(
        checkForAvailableSlots, interval=300, first=15)

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
