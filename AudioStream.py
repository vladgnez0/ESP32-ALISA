import aiofiles

MP3_FILE_PATH = "1.mp3"


async def generate_audio_stream():
    """
    Асинхронно читает MP3-файл небольшими кусками и отдаёт их как поток.

    Файл 1.mp3 должен быть создан заранее (например, с помощью TextToSpeech.text_to_mp3).
    """
    async with aiofiles.open(MP3_FILE_PATH, "rb") as f:
        while True:
            chunk = await f.read(1024)
            if not chunk:
                break
            yield chunk
