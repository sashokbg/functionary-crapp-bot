import time
import eventlet
import socketio
from assistant import Assistant
from datetime import date
import handlers
from json import dumps

sio = socketio.Server(cors_allowed_origins='*')
app = socketio.WSGIApp(sio, static_files={
    '/': {'content_type': 'text/html', 'filename': 'index.html'},
    '/styles.css': {'content_type': 'text/css', 'filename': 'styles.css'}
})

current_user = 'aleksandar@company.com'

projects = handlers.get_projects_for_user(
    '{"email": "'+current_user+'"}')


context = [
    {"role": "system", "content": "Client stdout is HTML capable"},
    {"role": "system", "content": f'Current date is: {date.today()}'},
    {"role": "system", "content": 'Locale is en-GB'},
    {"role": "system", "content": 'Holidays: ["2023-12-25"]'},
    {"role": "system",
     "content": f"Currently connected user is '{current_user}' Firstname Aleksandar Lastname KIRILOV"},
    {"role": "system",
     "content": f"User's assigned project {projects}"},
    {"role": "system", "content": "This program helps user fill in their monthly activity reports. Each activity "
     "report is associated to a project that user has worked on. Activities can be "
     "reported in increments of 25% per day. A single day cannot have more than 100% of "
     "reported time - this includes activities and absences."},
]

assistant = Assistant(context)


@sio.event
def connect(sid, environ):
    print('connect ', sid)
    sio.emit('system-context', assistant.messages)


@sio.on('confirm-message')
def confirm_message(sid, data):
    print('User confirms ', data)
    assistant.confirm()
    result = assistant.generate_message()

    if result["role"] == "system-confirm":
        sio.emit('system-confirm', {'data': result})
    else:
        sio.emit('assistant-message', {'data': result})


@sio.on('client-message')
def client_message(sid, data):
    print('message ', data)
    result = assistant.generate_message(data)

    print('generated result ', result)

    if result["role"] == "system-confirm":
        sio.emit('system-confirm', {'data': result})
    else:
        sio.emit('assistant-message', {'data': result})


@sio.on('restart-conversation')
def restart(sid):
    print('restarting', )
    assistant.init()
    sio.emit('system-message', {'data': {'content': 'Conversation restarted'}})
    sio.emit('system-context', assistant.messages)


@sio.event
def disconnect(sid):
    print('disconnect ', sid)


if __name__ == '__main__':
    eventlet.wsgi.server(eventlet.listen(('', 5000)), app)
