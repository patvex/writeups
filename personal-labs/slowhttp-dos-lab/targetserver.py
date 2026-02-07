import socket
import threading
import time

# КОНФИГУРАЦИЯ
HOST = '0.0.0.0'
PORT = 8080
MAX_THREADS = 10  # Специально занижаем лимит, чтобы сервер "лег" быстро
thread_semaphore = threading.Semaphore(MAX_THREADS)

def handle_client(client_socket, addr):
    print(f"[+] Новое соединение от {addr[0]}:{addr[1]}. Активных потоков: {threading.active_count() - 1}/{MAX_THREADS}")
    
    try:
        # Устанавливаем таймаут, но достаточно большой, чтобы R.U.D.Y и Slowloris работали
        client_socket.settimeout(60) 
        
        request_data = b""
        
        # Чтение заголовков (уязвимо для Slowloris)
        while True:
            chunk = client_socket.recv(1024)
            if not chunk:
                break
            request_data += chunk
            
            # Простая проверка конца заголовков
            if b"\r\n\r\n" in request_data:
                break
            
            # Если данные приходят очень медленно (R.U.D.Y / Slowloris),
            # этот поток будет висеть здесь и занимать слот в семафоре.

        # Имитация обработки (для проверки Slow Read)
        response_body = "<html><body><h1>Vulnerable Server is Working</h1><p>Data...</p></body></html>" * 100
        response_headers = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/html\r\n"
            f"Content-Length: {len(response_body)}\r\n"
            "Connection: close\r\n\r\n"
        )
        
        # Отправка данных
        client_socket.sendall(response_headers.encode('utf-8'))
        
        # Отправка тела частями (уязвимо для Slow Read, если клиент читает медленно, буфер заполнится и send заблокируется)
        for i in range(0, len(response_body), 1024):
            client_socket.send(response_body[i:i+1024].encode('utf-8'))
            # time.sleep(0.01) # Можно раскомментировать для имитации нагрузки

    except socket.timeout:
        print(f"[-] Таймаут соединения {addr}")
    except Exception as e:
        print(f"[-] Ошибка с {addr}: {e}")
    finally:
        client_socket.close()
        thread_semaphore.release() # Освобождаем слот
        print(f"[-] Соединение закрыто {addr}. Слот освобожден.")

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(100) # Backlog очереди
    print(f"[*] Сервер слушает на {HOST}:{PORT}")
    print(f"[*] Максимум одновременных соединений: {MAX_THREADS}")

    while True:
        # Пытаемся захватить семафор. Если все слоты заняты (атака), сервер здесь зависнет
        # и перестанет принимать новые соединения (TCP handshake будет проходить, но accept не сработает)
        thread_semaphore.acquire()
        
        client_sock, addr = server.accept()
        client_handler = threading.Thread(target=handle_client, args=(client_sock, addr))
        client_handler.daemon = True
        client_handler.start()

if __name__ == "__main__":
    start_server()