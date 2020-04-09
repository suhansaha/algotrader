from flask import Flask, render_template
from flask_socketio import SocketIO
import eventlet
eventlet.monkey_patch()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'vnkdjnfjknfl1232#'
socketio = SocketIO(app, async_mode='eventlet', message_queue='redis://redis:6379/0')  
#socketio = SocketIO(app)  

@app.route('/')
def sessions():
    return render_template('session.html')

def messageReceived(methods=['GET', 'POST']):
    print('message was received!!!')

@socketio.on('my event')
def handle_my_custom_event(json, methods=['GET', 'POST']):
    print('received my event: ' + str(json))
    #socketio.emit('my response', json, namespace='/', callback=messageReceived)
    socketio.emit('my response', json)

if __name__ == '__main__':
    socketio.run(app, debug=True)