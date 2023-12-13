import time
import eventlet
import socketio
from assistant import Assistant
import gc

sio = socketio.Server(cors_allowed_origins='*')
app = socketio.WSGIApp(sio, static_files={
    '/': {'content_type': 'text/html', 'filename': 'index.html'},
    '/styles.css': {'content_type': 'text/css', 'filename': 'styles.css'}
})

assistant = Assistant()


@sio.event
def connect(sid, environ):
    print('connect ', sid)


@sio.on('confirm-message')
def client_message(sid, data):
    print('User confirms ', data)
    result = assistant.confirm()

    print(f"RESULT FROM CONFIRM {result}")

    while "function_call" in result:
        result = assistant.confirm();

    assistant.unconfirm()
    sio.emit('assistant-message', {'data': result})


@sio.on('client-message')
def client_message(sid, data):
    print('message ', data)
    result = assistant.generate_message(data)

    if result["role"] == "system-confirm":
        sio.emit('system-confirm', {'data': result})
    else:
        sio.emit('assistant-message', {'data': result})


@sio.on('restart-conversation')
def restart(sid):
    print('restarting', )
    assistant = None
    gc.collect()

    time.sleep(5)

    assistant = Assistant()
    sio.emit('system-message', {'data': 'Conversation restarted'})


@sio.event
def disconnect(sid):
    print('disconnect ', sid)


if __name__ == '__main__':
    eventlet.wsgi.server(eventlet.listen(('', 5000)), app)
