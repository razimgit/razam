import os
import pyaudio
import numpy as np
import wave
from tkinter import TclError


RECORD_SECONDS = 5
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 22050

def record_draw_save(fig, ax, save_dir):
    '''Records sound from microphone, draws waveform, and saves what\'s been recorded.
    Returns True if everything worked'''
    p = pyaudio.PyAudio()

    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )

    ax.axis('off')
    ax.set_ylim(-5000, 5000)
    x = np.arange(0, CHUNK)
    line, = ax.plot(x, np.zeros(CHUNK), '-', lw=2, c='k')
    frames = []

    for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
        try:
            data = stream.read(CHUNK)
            frames.append(data)
            data_int = np.fromstring(data, dtype=np.int16)
            line.set_ydata(data_int)
            fig.canvas.draw()
            fig.canvas.flush_events()
        except TclError:
            return None

    stream.stop_stream()
    stream.close()
    p.terminate()

    sample_filename = None
    if frames:
        sample_filename = os.path.join(save_dir, 'sample.wav')
        wf = wave.open(sample_filename, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
    
    return sample_filename