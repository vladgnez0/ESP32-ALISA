import socket
from secret import MagmaCipher

# Глобальный ключ, чтобы при желании можно было использовать его из других модулей
key: bytes = b""


def key_server(host: str = "0.0.0.0", port: int = 54321) -> None:
    """
    Простой синхронный сервер, который один раз принимает подключение,
    генерирует ключ для MagmaCipher и отправляет его клиенту.
    """
    global key

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, port))
        s.listen(1)
        print(f"Сервер ключей слушает на {host}:{port} ...")

        conn = None
        try:
            conn, addr = s.accept()
            print(f"Клиент подключился: {addr}")

            # Генерируем ключ и сохраняем его в глобальной переменной
            key = MagmaCipher.generate_key()

            # Отправляем ключ целиком как байты
            conn.sendall(key)
            print(f"Отправлен ключ: {key.hex()}")

        except Exception as e:
            print(f"Ошибка в key_server: {e}")

        finally:
            if conn:
                conn.close()


if __name__ == "__main__":
    key_server()
