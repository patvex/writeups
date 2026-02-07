import socket
import threading
import time

# КОНФИГУРАЦИЯ
HOST = '0.0.0.0'
PORT = 8080
MAX_THREADS = 100  # Специально занижаем лимит, чтобы сервер "лег" быстро
thread_semaphore = threading.Semaphore(MAX_THREADS)

def handle_client(client_socket, addr):
    start_time = time.time()
    print(f"[+] Новое соединение от {addr[0]}:{addr[1]}. Активных потоков: {threading.active_count() - 1}/{MAX_THREADS}")
    
    try:
        # 1. Устанавливаем общий таймаут на чтение (защита от совсем "мёртвых" соединений)
        client_socket.settimeout(10) 
        
        request_data = b""
        
        while True:
            # 2. Проверяем, не слишком ли долго клиент шлет заголовки
            # Если прошло больше 15 секунд, а заголовков всё нет — кикаем.
            if time.time() - start_time > 15:
                print(f"[-] Slow client detected (Slowloris protection) {addr}")
                break

            try:
                chunk = client_socket.recv(1024)
                if not chunk:
                    break
                request_data += chunk
                
                if b"\r\n\r\n" in request_data:
                    break
            except socket.timeout:
                print(f"[-] Socket timeout while receiving headers {addr}")
                break

        # Если мы вышли из цикла без заголовков — закрываем
        if b"\r\n\r\n" not in request_data:
            return

        # 3. Эмуляция ответа (как у тебя и была)
        response_body = "<html><body><h1>Vibe Server: Safe & Fast</h1></body></html>"
        response_headers = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/html\r\n"
            f"Content-Length: {len(response_body)}\r\n"
            "Connection: close\r\n\r\n"
        )
        
        client_socket.sendall(response_headers.encode('utf-8'))
        client_socket.sendall(response_body.encode('utf-8'))

    except Exception as e:
        print(f"[-] Ошибка с {addr}: {e}")
    finally:
        client_socket.close()
        thread_semaphore.release()
        duration = time.time() - start_time
        print(f"[-] Соединение закрыто {addr}. Слот освобожден. (Длительность: {duration:.2f}s)")

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