from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from datetime import datetime

app = Flask(__name__)
socketio = SocketIO(app)

users = {}  # {sid: {'username': str, 'last_seen': datetime}}
messages = {}  # {(user1, user2): [{'username': str, 'message': str, 'timestamp': str, 'unread': bool, 'delivered': bool}]}

@app.route('/')
def chat():
    return render_template('chat.html')

@socketio.on('connect')
def handle_connect():
    sid = request.sid
    users[sid] = {'username': None, 'last_seen': datetime.now()}

@socketio.on('register_username')
def handle_register_username(data):
    sid = request.sid
    username = data['username']
    if username in [u['username'] for u in users.values() if u['username']]:
        emit('error', 'Username already taken', to=sid)
        return
    users[sid]['username'] = username
    users[sid]['last_seen'] = datetime.now()
    emit('user_list', [{'username': u['username'], 'last_seen': u['last_seen'].isoformat()} for u in users.values() if u['username']], broadcast=True)

@socketio.on('send_private_message')
def handle_send_private_message(data):
    sender_sid = request.sid
    sender_username = users[sender_sid].get('username')
    recipient_username = data['recipient']
    message_content = data['message']
    if not sender_username:
        emit('error', 'You must register a username first', to=sender_sid)
        return
    recipient_sid = next((sid for sid, info in users.items() if info['username'] == recipient_username), None)
    if not recipient_sid:
        emit('error', 'Recipient not found', to=sender_sid)
        return
    
    timestamp = datetime.now().isoformat()
    message = {
        'username': sender_username,
        'message': message_content,
        'timestamp': timestamp,
        'unread': (sender_sid != recipient_sid),  # Chỉ unread nếu không phải người gửi
        'delivered': False
    }
    key = tuple(sorted([sender_username, recipient_username]))
    if key not in messages:
        messages[key] = []
    messages[key].append(message)  # Thêm vào cuối danh sách
    emit('new_message', message, to=sender_sid)
    if recipient_sid:
        message['delivered'] = True
        emit('new_message', message, to=recipient_sid)
        users[recipient_sid]['last_seen'] = datetime.now()
    emit('user_list', [{'username': u['username'], 'last_seen': u['last_seen'].isoformat()} for u in users.values() if u['username']], broadcast=True)

@socketio.on('get_history')
def handle_get_history(data):
    sid = request.sid
    username = users[sid].get('username')
    other_username = data['other_user']
    if not username:
        emit('error', 'You must register a username first', to=sid)
        return
    key = tuple(sorted([username, other_username]))
    history = messages.get(key, [])
    emit('history', history, to=sid)

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    if sid in users:
        del users[sid]
        emit('user_list', [{'username': u['username'], 'last_seen': u['last_seen'].isoformat()} for u in users.values() if u['username']], broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True)