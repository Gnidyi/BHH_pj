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
user_chat_files = {}
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
    user_chat_files[user_id] = create_chat_file()
    emit('bot_response', {'response': "Herzlich Willkommen beim BUGLAND Supportchatbot!"})
    time.sleep(0.75)
    emit('bot_response', {'response': "Bist du ein Privatkunde oder ein Geschäftskunde? (Privat/Gewerbe)"})

@socketio.on('message')
def handle_message(data):
    user_message = data.get('message')
    user_id = request.sid
    ticket_responses = []

    if not user_message:
        emit('bot_response', {'response': 'No message received!'})
        return

    chat_file_path = user_chat_files.get(user_id)

    if not chat_file_path:
        chat_file_path = create_chat_file()
        user_chat_files[user_id] = chat_file_path

    write_ticket(chat_file_path, f"User: {user_message}")

    # Check the user's current state - brauchen wir um inputs zu erhalten
    current_state = user_states.get(user_id, None)

    if current_state == STATE_WAITING_FOR_CUSTOMER_TYPE:
        # Process customer type (Privat/Gewerbe)
        if user_message.lower() not in ['privat', 'gewerbe', 'exit']:
            response = "Ungültige Eingabe! Bitte gib 'Privat' oder 'Gewerbe' ein."
            emit('bot_response', {'response': response})
            write_ticket(chat_file_path, f"Bot: {response}")
            return

        if user_message.lower() == 'privat':
            response = "Vielen Dank!"
            emit('bot_response', {'response': response})
            write_ticket(chat_file_path, f"Bot: {response}")

            user_states[user_id] = STATE_WAITING_FOR_DEVICE_CHOICE
            response = "Bitte wähle dein Gerät:"
            emit('bot_response', {'response': response})
            write_ticket(chat_file_path, f"Bot: {response}")

            response = "1. CleanBug\n2. WindowFly\n3. GardenBeetle"
            emit('bot_response', {'response': response})
            write_ticket(chat_file_path, f"Bot: {response}")
            return

        elif user_message.lower() == 'gewerbe':
            response = "Vielen Dank für deine Eingabe! Du hast als Geschäftskunde einen persönlichen Ansprechpartner."
            emit('bot_response', {'response': response})
            write_ticket(chat_file_path, f"Bot: {response}")

            user_states[user_id] = STATE_WAITING_FOR_CHATBOT_USE
            response = "Möchtest du dennoch den Chatbot verwenden? (Ja/Nein)"
            emit('bot_response', {'response': response})
            write_ticket(chat_file_path, f"Bot: {response}")
            return

        elif user_message.lower() == 'exit':
            response = "Vielen Dank für die Nutzung unseres Chats!"
            emit('bot_response', {'response': response})
            write_ticket(chat_file_path, f"Bot: {response}")
            user_states[user_id] = None
            return


    elif current_state == STATE_WAITING_FOR_DEVICE_CHOICE:

        if user_message not in ['1', '2', '3', 'exit']:
            response = "Ungültige Eingabe! Bitte gib eine gültige Geräte-Nummer ein."

            emit('bot_response', {'response': response})

            write_ticket(chat_file_path, f"Bot: {response}")

            return

        if user_message == '1':
            response = "Du hast 'CleanBug' gewählt."
        elif user_message == '2':
            response = "Du hast 'WindowFly' gewählt."
        elif user_message == '3':
            response = "Du hast 'GardenBeetle' gewählt."

        emit('bot_response', {'response': response})
        write_ticket(chat_file_path, f"Bot: {response}")

        user_states[user_id] = STATE_WAITING_FOR_PROBLEM_CHOICE
        response = "Was ist das Problem mit deinem Gerät?"
        emit('bot_response', {'response': response})
        write_ticket(chat_file_path, f"Bot: {response}")

        response = "1. Konfiguration\n2. Defekt\n3. Fehlermeldung\n4. Fehlverhalten des Roboters\n5. Sonstiges"
        emit('bot_response', {'response': response})
        write_ticket(chat_file_path, f"Bot: {response}")
        return

    elif current_state == STATE_WAITING_FOR_PROBLEM_CHOICE:
        if user_message not in ['1', '2', '3', '4', '5', 'exit']:
            response = "Ungültige Eingabe! Bitte gib eine gültige Problem-Nummer ein."
            ticket_responses.append(f"Bot: {response}")
            emit('bot_response', {'response': response})
            write_ticket(chat_file_path, '\n'.join(ticket_responses))  # Store ticket responses
            return

        if user_message == '1' or user_message.lower() == "konfiguration":
            response = openai_pr("Mein Roboter hat ein Konfigurationsproblem. Was soll ich nun machen?")
            ticket_responses.append(f"Bot: {response}")
            emit('bot_response', {'response': response})
        elif user_message == '2' or user_message.lower() == "defekt":
            response = openai_pr("Ich glaub mein Roboter ist defekt. Was soll ich nun machen?")
            ticket_responses.append(f"Bot: {response}")
            emit('bot_response', {'response': response})
        elif user_message == '3' or user_message.lower() == "fehlermeldung":
            response = openai_pr("Ich habe einen Roboter und er zeigt eine Fehlermeldung an. Was soll ich nun machen?")
            ticket_responses.append(f"Bot: {response}")
            emit('bot_response', {'response': response})
        elif user_message == '4' or user_message.lower() == "fehlverhalten des roboters":
            response = openai_pr("Der Roboter funktioniert nicht so wie er soll. Was soll ich nun machen?")
            ticket_responses.append(f"Bot: {response}")
            emit('bot_response', {'response': response})
        elif user_message == '5' or user_message.lower() == "sonstiges":
            response = "Du hast 'Sonstiges' gewählt. Bitte schildere dein Problem:"
            ticket_responses.append(f"Bot: {response}")
            emit('bot_response', {'response': response})
            user_states[user_id] = STATE_WAITING_FOR_PROBLEM_DESCRIPTION  # Proceed to problem description
            write_ticket(chat_file_path, '\n'.join(ticket_responses))  # Store ticket responses
            return
        elif user_message.lower() == "exit":
            response = "Chat beendet. Vielen Dank für die Nutzung unseres Chats!"
            ticket_responses.append(f"Bot: {response}")
            emit('bot_response', {'response': response})
            user_states[user_id] = None  # Reset state and end the chat
            write_ticket(chat_file_path, '\n'.join(ticket_responses))  # Store ticket responses
            return

        response = "Alternativ kontaktiere den Support unter folgender Telefonnummer oder E-Mail."
        ticket_responses.append(f"Bot: {response}")
        emit('bot_response', {'response': response})
        response = "Telefonnummer: 0123456789\nE-Mail: supp.bt@bugland.de"
        ticket_responses.append(f"Bot: {response}")
        emit('bot_response', {'response': response})
        time.sleep(5)

        response = "Brauchen Sie noch hilfe? (Ja/Nein)"
        ticket_responses.append(f"Bot: {response}")
        emit('bot_response', {'response': response})
        user_states[user_id] = "waiting_for_restart_choice"
        write_ticket(chat_file_path, '\n'.join(ticket_responses))  # Store ticket responses
        return

    elif current_state == "waiting_for_restart_choice":
        if user_message.lower() == "ja":
            user_states[user_id] = STATE_WAITING_FOR_DEVICE_CHOICE
            response = "Bitte wähle dein Gerät:\n1. CleanBug\n2. WindowFly\n3. GardenBeetle"
            ticket_responses.append(f"Bot: {response}")
            emit('bot_response', {'response': response})
        elif user_message.lower() == "nein":
            response = "Vielen Dank für die Nutzung unseres Chats!"
            ticket_responses.append(f"Bot: {response}")
            emit('bot_response', {'response': response})
            user_states[user_id] = None
        else:
            response = "Ungültige Eingabe! Bitte gib 'Gerät' oder 'Exit' ein."
            ticket_responses.append(f"Bot: {response}")
            emit('bot_response', {'response': response})

        write_ticket(chat_file_path, '\n'.join(ticket_responses))  # Store ticket responses
        return

    elif current_state == STATE_WAITING_FOR_PROBLEM_DESCRIPTION:
        problem_description = user_message
        response = openai_pr(problem_description)
        ticket_responses.append(f"Bot: {response}")
        emit('bot_response', {'response': response})

        # Nach weiteren Problemen fragen
        time.sleep(2)
        response = "Brauchen Sie noch weitere Hilfe? (Ja/Nein)"
        ticket_responses.append(f"Bot: {response}")
        emit('bot_response', {'response': response})
        user_states[user_id] = "waiting_for_restart_choice"
        write_ticket(chat_file_path, '\n'.join(ticket_responses))  # Store ticket responses
        return

    elif current_state == STATE_WAITING_FOR_CHATBOT_USE:
        if user_message.lower() == 'ja':
            user_states[user_id] = STATE_WAITING_FOR_DEVICE_CHOICE
            response = "Bitte wähle dein Gerät:\n1. CleanBug\n2. WindowFly\n3. GardenBeetle"
            ticket_responses.append(f"Bot: {response}")
            emit('bot_response', {'response': response})
        elif user_message.lower() == 'nein':
            response = "Vielen Dank für die Nutzung unseres Chats!"
            ticket_responses.append(f"Bot: {response}")
            emit('bot_response', {'response': response})
            response = "Alternativ kontaktiere den Support unter folgender Telefonnummer oder E-Mail:"
            ticket_responses.append(f"Bot: {response}")
            emit('bot_response', {'response': response})
            response = "Telefonnummer: 0123456789\nE-Mail: supp.bt@bugland.de"
            ticket_responses.append(f"Bot: {response}")
            emit('bot_response', {'response': response})
            user_states[user_id] = None  # End the chat
        else:
            response = "Ungültige Eingabe! Bitte gib 'Ja' oder 'Nein' ein."
            ticket_responses.append(f"Bot: {response}")
            emit('bot_response', {'response': response})

        write_ticket(chat_file_path, '\n'.join(ticket_responses))  # Store ticket responses
        return
    else:
        # Wenn kein spezifischer Zustand, nach allgemeinem Input fragen
        response = "Ich habe dich nicht verstanden. Bitte versuche es noch einmal."
        ticket_responses.append(f"Bot: {response}")
        emit('bot_response', {'response': response})
        write_ticket(chat_file_path, '\n'.join(ticket_responses))  # Store ticket responses

# Handling chat disconnection
@socketio.on('disconnect')
def disconnect():
    user_id = request.sid
    if user_id in user_states:
        del user_states[user_id]
    emit('bot_response', {'response': "Chat beendet. Vielen Dank für die Nutzung unseres Chats!"})


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
