from flask import Flask, render_template, redirect, request, url_for, jsonify
from flask_sockets import Sockets
from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler
#from opuslib import Decoder
import wave
import numpy as np

import io
import logging
import json
import struct
import time

app = Flask(__name__, static_folder='static')
sockets = Sockets(app)

#sound_decoder = Decoder(24000, 1)

client_buffer_size = 4096
sample_rate = 44100
save_time_sec = 10


@app.route('/rec', methods=['GET'])
def root():
    return render_template('index.html')

@sockets.route('/audio')
def consume_audio(ws):
    token = request.args.get('token')
    app.logger.info(token + ': new connection')
    if token != 'test_token':
        ws.close()
        return
    
    whole_data = bytearray()
    last_updated = time.time()
    while not ws.closed:
        data = ws.receive()
        if data is None:
            app.logger.info(token + ': no message received...')
            continue
        #data, _ = sound_decoder.decode_float(data, 20)
        data = fpcm32_to_ipcm16(data)
        whole_data.extend(data)
        if time.time() > last_updated + save_time_sec:
            app.logger.info(token + ': saving... ' + str(len(whole_data)))
            # TODO: append instead of rewrite
            save_wav('test.wav', whole_data)
            last_updated = time.time()

    
    app.logger.info(token + ': connection closed, saving... ' + str(len(whole_data)))
    save_wav('test.wav', whole_data)

def save_wav(filename, data):
    with wave.open(filename, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2) # int16
        wav.setframerate(44100)
        wav.writeframesraw(data)
    
def fpcm32_to_ipcm16(data):
    float32_data = decode_floats(data)
    float32_data /= 1.414 # half PI
    float32_data *= 32767 # int16
    return encode_ints16(float32_data.astype(np.int16))

def decode_floats(data):
    return np.array(struct.unpack(str(len(data) // 4) + 'f', data))

def encode_ints16(data):
    return struct.pack(str(len(data)) + 'h', *data)
    

if __name__ == '__main__':
    app.logger.setLevel(logging.DEBUG)
    #app.run()
    server = pywsgi.WSGIServer(('', 5050), app, handler_class=WebSocketHandler)
    app.logger.info('starting server at port 5050')
    server.serve_forever()
