from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
import json
from datetime import datetime, timezone
import smtplib
from email.message import EmailMessage
import os

# Dictionary to store user-specific configuration data
user_configs = {}

# Directory to save user-specific config files
CONFIG_DIR = "user_configs"
if not os.path.exists(CONFIG_DIR):
    os.makedirs(CONFIG_DIR)

# Load configuration for a specific user
def load_user_config(user_id):
    config_file = os.path.join(CONFIG_DIR, f"{user_id}_config.json")
    if os.path.exists(config_file):
        try:
            with open(config_file, "r") as file:
                return json.load(file)
        except Exception as e:
            print(f"Error loading user config file: {e}")
    return None

# Save configuration for a specific user
def save_user_config(user_id, config_data):
    config_file = os.path.join(CONFIG_DIR, f"{user_id}_config.json")
    try:
        with open(config_file, "w") as file:
            json.dump(config_data, file)
    except Exception as e:
        print(f"Error saving user config file: {e}")

# Send email function
async def send_email(sender, receiver, subject, body):
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender["email"], sender["password"])
            msg = EmailMessage()
            msg["From"] = sender["email"]
            msg["To"] = receiver
            msg["Subject"] = subject
            msg.set_content(body)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Automatic Sending", callback_data="automatic")],
        [InlineKeyboardButton("Manual Sending", callback_data="manual")],
        [InlineKeyboardButton("Send Emails in Range", callback_data="range")],
        [InlineKeyboardButton("Inverse Sending", callback_data="inverse")],
        [InlineKeyboardButton("Add config.json file", callback_data="add_config")],
        [InlineKeyboardButton("Exit", callback_data="exit")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Welcome to the Email Bot! Please choose an option:", reply_markup=reply_markup)

# Handle menu options
async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    option = query.data

    user_id = update.effective_user.id
    user_config = load_user_config(user_id)

    if option == "automatic":
        if not user_config:
            await query.edit_message_text("No config file found. Please upload a config.json file first.")
            return
        await query.edit_message_text("Automatic Sending selected. Enter phone numbers separated by commas.")
        context.user_data["mode"] = "automatic"
    elif option == "manual":
        if not user_config:
            await query.edit_message_text("No config file found. Please upload a config.json file first.")
            return
        await query.edit_message_text("Manual Sending selected. Choose a sender.")
        for idx, sender in enumerate(user_config["senders"], 1):
            await query.message.reply_text(f"{idx}. {sender['email']}")
        context.user_data["mode"] = "manual"
    elif option == "range":
        if not user_config:
            await query.edit_message_text("No config file found. Please upload a config.json file first.")
            return
        await query.edit_message_text("Send Emails in Range selected. Enter range in 'start,end' format.")
        context.user_data["mode"] = "range"
    elif option == "inverse":
        if not user_config:
            await query.edit_message_text("No config file found. Please upload a config.json file first.")
            return
        await query.edit_message_text("Inverse Sending selected. Enter phone numbers separated by commas.")
        context.user_data["mode"] = "inverse"
    elif option == "add_config":
        await query.edit_message_text("Please upload your config.json file.")
        context.user_data["mode"] = "add_config"
    elif option == "exit":
        await query.edit_message_text("Exiting the bot. Thank you!")
    else:
        await query.edit_message_text("Invalid option selected.")

# Handle user inputs
async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get("mode")
    text = update.message.text
    user_id = update.effective_user.id
    user_config = load_user_config(user_id)

    if mode == "automatic" and user_config:
        phone_numbers = text.split(",")
        for phone in phone_numbers:
            sender = user_config["senders"][0]  # Pick the first sender
            subject = user_config["subject"].format(phone.strip())
            body = user_config["body"]
            success = await send_email(sender, user_config["receiver"], subject, body)
            if success:
                await update.message.reply_text(f"Email sent to {phone.strip()} successfully!")
            else:
                await update.message.reply_text(f"Failed to send email to {phone.strip()}.")
    elif mode == "manual" and user_config:
        try:
            sender_index = int(text) - 1
            sender = user_config["senders"][sender_index]
            await update.message.reply_text(f"Selected {sender['email']}. Enter phone number.")
            context.user_data["sender"] = sender
        except:
            await update.message.reply_text("Invalid selection. Please try again.")
    elif mode == "range" and user_config:
        try:
            start, end = map(int, text.split(","))
            senders = user_config["senders"][start - 1:end]
            await update.message.reply_text(f"Selected senders from {start} to {end}. Enter phone numbers.")
            context.user_data["senders"] = senders
        except:
            await update.message.reply_text("Invalid range. Please try again.")
    elif mode == "inverse" and user_config:
        phone_numbers = text.split(",")
        senders = list(reversed(user_config["senders"]))
        for phone, sender in zip(phone_numbers, senders):
            subject = user_config["subject"].format(phone.strip())
            body = user_config["body"]
            success = await send_email(sender, user_config["receiver"], subject, body)
            if success:
                await update.message.reply_text(f"Email sent to {phone.strip()} successfully!")
            else:
                await update.message.reply_text(f"Failed to send email to {phone.strip()}.")

# Handle document uploads
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    document = update.message.document

    if document.file_name == "config.json":
        file_path = os.path.join(CONFIG_DIR, f"{user_id}_config.json")
        await document.get_file().download(file_path)
        await update.message.reply_text("Config file uploaded and saved successfully.")
    else:
        await update.message.reply_text("Please upload a valid config.json file.")

# Main function to start the bot
def main():
    bot_token = "6242926336:AAH_jMAHQjMq5TJwif3wbbKcHRvLa_GrnkY"
    application = ApplicationBuilder().token(bot_token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_menu))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    application.run_polling()

if __name__ == "__main__":
    main()
