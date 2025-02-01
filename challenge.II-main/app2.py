from flask_socketio import SocketIO, emit
from flask import Flask, render_template, request
import time
import openai
import configparser
from datetime import datetime
import os

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Dictionary to track user states (e.g., awaiting customer type)
user_states = {}
global chat_file_path

#States - klappen wie 'Standby' dingster. Also warten auf input.
STATE_WAITING_FOR_CUSTOMER_TYPE = "waiting_for_customer_type"
STATE_WAITING_FOR_BUSINESS_CHOICE = "waiting_for_business_choice"
STATE_WAITING_FOR_DEVICE_CHOICE = "waiting_for_device_choice"
STATE_WAITING_FOR_PROBLEM_CHOICE = "waiting_for_problem_choice"
STATE_WAITING_FOR_PROBLEM_DESCRIPTION = "waiting_for_problem_description"
STATE_WAITING_FOR_CHATBOT_USE = "waiting_for_chatbot_use"


@app.route('/')
def index():
    return render_template('bugland.html')


# Function to create a new chat file
def create_chat_file():
    now = datetime.now()
    file_name = now.strftime("%d%m%y-%H%M.txt")
    folder = "chats"
    file_path = os.path.join(folder, file_name)

    if not os.path.exists(folder):
        os.makedirs(folder)

    with open(file_path, 'w') as file:
        file.write("Chat started\n")

    return file_path


# Function to write to the chat file
def write_ticket(file_path, text):
    with open(file_path, 'a') as file:
        file.write(text + "\n")

config = configparser.ConfigParser()
config.read('config.ini')
openai.api_key = config['DEFAULT']['API_KEY']


# OpenAI API integration
def ask_openai(question):
    config = configparser.ConfigParser()
    config.read('config.ini')
    openai.api_key = config['DEFAULT']['API_KEY']

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": question}]
    )
    return response.choices[0].message['content']

@socketio.on('start_chat')
def start_chat():
    user_id = request.sid
    user_states[user_id] = STATE_WAITING_FOR_CUSTOMER_TYPE  # Set the state to waiting for customer type
    emit('bot_response', {'response': "Herzlich Willkommen beim BUGLAND Supportchatbot!"})
    time.sleep(0.75)
    emit('bot_response', {'response': "Bist du ein Privatkunde oder ein Geschäftskunde? (Privat/Gewerbe)"})

@socketio.on('message')
def handle_message(data):
    user_message = data.get('message')
    user_id = request.sid
    chat_file_path = create_chat_file()

    if not user_message:
        emit('bot_response', {'response': 'No message received!'})
        return

    write_ticket(chat_file_path, f"User: {user_message}")

    # Check the user's current state - brauchen wir um inputs zu erhalten
    current_state = user_states.get(user_id, None)

    if current_state == STATE_WAITING_FOR_CUSTOMER_TYPE:
        # Process customer type (Privat/Gewerbe)
        if user_message.lower() not in ['privat', 'gewerbe', 'exit']:
            emit('bot_response', {'response': "Ungültige Eingabe! Bitte gib 'Privat' oder 'Gewerbe' ein."})
            return

        if user_message.lower() == 'privat':
            emit('bot_response', {'response': "Vielen Dank!"})
            user_states[user_id] = STATE_WAITING_FOR_DEVICE_CHOICE  # Proceed to device choice
            emit('bot_response', {'response': "Bitte wähle dein Gerät:"})
            emit('bot_response', {'response': "1. CleanBug\n2. WindowFly\n3. GardenBeetle"})
            return
        elif user_message.lower() == 'gewerbe':
            emit('bot_response', {
                'response': "Vielen Dank für deine Eingabe! Du hast als Geschäftskunde einen persönlichen Ansprechpartner."})
            user_states[user_id] = STATE_WAITING_FOR_CHATBOT_USE
            emit('bot_response', {'response': "Möchtest du dennoch den Chatbot verwenden? (Ja/Nein)"})
            return
        elif user_message.lower() == 'exit':
            emit('bot_response', {'response': "Vielen Dank für die Nutzung unseres Chats!"})
            user_states[user_id] = None
            return

    elif current_state == STATE_WAITING_FOR_DEVICE_CHOICE:
        # Process device choice (CleanBug, WindowFly, GardenBeetle)
        if user_message not in ['1', '2', '3', 'exit']:
            emit('bot_response', {'response': "Ungültige Eingabe! Bitte gib eine gültige Geräte-Nummer ein."})
            return

        if user_message == '1':
            emit('bot_response', {'response': "Du hast 'CleanBug' gewählt."})
        elif user_message == '2':
            emit('bot_response', {'response': "Du hast 'WindowFly' gewählt."})
        elif user_message == '3':
            emit('bot_response', {'response': "Du hast 'GardenBeetle' gewählt."})

        user_states[user_id] = STATE_WAITING_FOR_PROBLEM_CHOICE
        emit('bot_response', {'response': "Was ist das Problem mit deinem Gerät?"})
        emit('bot_response',
             {'response': "1. Konfiguration\n2. Defekt\n3. Fehlermeldung\n4. Fehlverhalten des Roboters\n5. Sonstiges"})
        return

    elif current_state == STATE_WAITING_FOR_PROBLEM_CHOICE:
        # Process problem choice (Konfiguration, Defekt, Fehlermeldung, Fehlverhalten, Sonstiges)
        if user_message not in ['1', '2', '3', '4', '5', 'exit']:
            emit('bot_response', {'response': "Ungültige Eingabe! Bitte gib eine gültige Problem-Nummer ein."})
            return

        # Handle problem based on user's choice
        if user_message == '1' or user_message.lower() == "konfiguration":
            emit('bot_response', { 'response': openai_pr("Mein Roboter hat ein Konfigurationsproblem. Was soll ich nun machen?")})
            print(openai_pr("Mein Roboter hat ein Konfigurationsproblem. Was soll ich nun machen?"))
        elif user_message == '2' or user_message.lower() == "defekt":
            emit('bot_response', { 'response': openai_pr("Ich glaub mein Roboter ist defekt. Was soll ich nun machen?")})
        elif user_message == '3' or user_message.lower() == "fehlermeldung":
            emit('bot_response', { 'response': openai_pr("Ich habe einen Roboter und er zeigt eine Fehlermeldung an. Was soll ich nun machen?")})
        elif user_message == '4' or user_message.lower() == "fehlverhalten des roboters":
            emit('bot_response', { 'response': openai_pr("Der Roboter funktioniert nicht so wie er soll. Was soll ich nun machen?")})
        elif user_message == '5' or user_message.lower() == "sonstiges":
            emit('bot_response', {'response': "Du hast 'Sonstiges' gewählt."})
            emit('bot_response', {'response': "Bitte schildere dein Problem:"})
            user_states[user_id] = STATE_WAITING_FOR_PROBLEM_DESCRIPTION  # Proceed to problem description
            return
        elif user_message.lower() == "exit":
            user_states[user_id] = None  # Reset state and end the chat
            emit('bot_response', {'response': "Chat beendet. Vielen Dank für die Nutzung unseres Chats!"})
            return
        emit('bot_response',
             {'response': "Alternativ kontaktiere den Support unter folgender Telefonnummer oder E-Mail."})
        emit('bot_response', {'response': "Telefonnummer: 0123456789\nE-Mail: supp.bt@bugland.de"})
        time.sleep(5)

        emit('bot_response',
             {'response': "Brauchen Sie noch hilfe? (Ja/Nein)"})
        user_states[user_id] = "waiting_for_restart_choice"
        return

    elif current_state == "waiting_for_restart_choice":
        if user_message.lower() == "ja":
            user_states[user_id] = STATE_WAITING_FOR_DEVICE_CHOICE
            emit('bot_response', {'response': "Bitte wähle dein Gerät:"})
            emit('bot_response', {'response': "1. CleanBug\n2. WindowFly\n3. GardenBeetle"})
        elif user_message.lower() == "nein":
            emit('bot_response', {'response': "Vielen Dank für die Nutzung unseres Chats!"})
            user_states[user_id] = None
        else:
            emit('bot_response', {'response': "Ungültige Eingabe! Bitte gib 'Gerät' oder 'Exit' ein."})

    elif current_state == STATE_WAITING_FOR_PROBLEM_DESCRIPTION:
        problem_description = user_message
        emit('bot_response', {'response': openai_pr(problem_description)})

        # Nach weiteren Problemen fragen
        time.sleep(2)
        emit('bot_response', {'response': "Brauchen Sie noch weitere Hilfe? (Ja/Nein)"})
        user_states[user_id] = "waiting_for_restart_choice"
        return

    elif current_state == STATE_WAITING_FOR_CHATBOT_USE:
        if user_message.lower() == 'ja':
            user_states[user_id] = STATE_WAITING_FOR_DEVICE_CHOICE
            emit('bot_response', {'response': "Bitte wähle dein Gerät:"})
            emit('bot_response', {'response': "1. CleanBug\n2. WindowFly\n3. GardenBeetle"})
        elif user_message.lower() == 'nein':
            emit('bot_response', {'response': "Vielen Dank für die Nutzung unseres Chats!"})
            emit('bot_response',
                 {'response': "Alternativ kontaktiere den Support unter folgender Telefonnummer oder E-Mail:"})
            emit('bot_response', {'response': "Telefonnummer: 0123456789\nE-Mail: supp.bt@bugland.de"})
            user_states[user_id] = None  # End the chat
        else:
            # Handle invalid input for "Ja/Nein"
            emit('bot_response', {'response': "Ungültige Eingabe! Bitte gib 'Ja' oder 'Nein' ein."})

        return
    else:
        # wenn kein specific state, nach general input fragen
        emit('bot_response', {'response': "Ich habe dich nicht verstanden. Bitte versuche es noch einmal."})


# Handling chat disconnection
@socketio.on('disconnect')
def disconnect():
    user_id = request.sid
    if user_id in user_states:
        del user_states[user_id]
    emit('bot_response', {'response': "Chat beendet. Vielen Dank für die Nutzung unseres Chats!"})


# Get problem choices for the chatbot

# Function to call OpenAI API and get response
def openai_pr(inp):
    answer = ask_openai(
        "Ich habe eine Firma namens Bugland und die baut Reinigungsroboter und einen Gartenroboter. "
        "Du sollst so tun als wärst du der Supportchat von dem Unternehmen und Tipps geben. "
        "Sag bitte nicht, dass der Support kontaktiert werden soll oder das du bei weiteren "
        "Fragen helfen kannst. Auch bitte nicht sagen, dass detailierte Informationen "
        "helfen. Also einfach nur die Antwort auf folgende Frage geben und bitte die einzelnen "
        "Punkte mit Gedankenstrichen klar trennen: " + inp
    )
    return answer


# To run the bot
if __name__ == "__main__":
    socketio.run(app, debug=True)
