import socket
import struct
import pyaudio
import queue
import threading
import time

# Network parameters
RECEIVER_IP = '0.0.0.0'
RECEIVER_PORT = 42069
CHUNK_SIZE = 1024

# Audio parameters
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100

# Initialize PyAudio
p = pyaudio.PyAudio()

# Open a stream using PulseAudio
stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                output=True,
                frames_per_buffer=CHUNK_SIZE,
                output_device_index=6)  # Use the PulseAudio device

# Create a TCP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind((RECEIVER_IP, RECEIVER_PORT))
sock.listen(1)


def receive_all(sock, n):
    data = b''
    while len(data) < n:
        try:
            packet = sock.recv(n - len(data))
            if not packet:
                return None
            data += packet
        except socket.timeout:
            print("Receiving data timed out.")
            return None
        except socket.error as e:
            print(f"Socket error: {e}")
            return None
    return data

def socket_thread(sound_queue):
    while True:
        sock.settimeout(30)
        print("Waiting for connection...")
        try:
            connection, client_address = sock.accept()
            connection.settimeout(5)
            print(f"Connected to {client_address}")
            
            while True:
                try:
                    # Receive the length of the incoming data
                    length_data = receive_all(connection, 4)
                    if length_data is None:
                        print("Connection closed by client")
                        break
                    
                    length = struct.unpack('!I', length_data)[0]
                    audio_data = receive_all(connection, length)
                    
                    if audio_data is None:
                        print("Connection closed by client")
                        break
                    
                    sound_queue.put(audio_data)
                
                except socket.timeout:
                    print("Socket timeout while receiving data")
                    break
                except socket.error as e:
                    print(f"Socket error: {e}")
                    break
        
        except socket.timeout:
            print("Timeout while waiting for connection")
        except socket.error as e:
            print(f"Socket error while accepting connection: {e}")
        
        print("Disconnected. Waiting for new connection...")

sound_queue = queue.Queue()
threading.Thread(target=socket_thread, args=(sound_queue,)).start()


try:
    while True:
        audio_data = sound_queue.get()
        if audio_data is None:
            print("No audio data")
            time.sleep(0.1)
            continue

        print(f"Received {len(audio_data)} bytes of audio data")
        stream.write(audio_data)

except KeyboardInterrupt:
    print("Streaming stopped.")
    sock.close()

finally:
    print("Stopping stream")
    stream.stop_stream()
    stream.close()
    p.terminate()
    sock.close()
