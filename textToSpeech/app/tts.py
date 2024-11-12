from langdetect import detect
from abc import ABC, abstractmethod
import requests
import time
import subprocess
from typing import Optional, Callable
import redis
import hashlib
from functools import wraps


class Cache():
    def __init__(self, redis_url: str, max_size_mb: int = 100):
        self.redis = redis.Redis.from_url(redis_url)
        self.enabled = True

        self.max_size_bytes = max_size_mb * 1024 * 1024

    def generate_key(self, text: str, language: str, voice: str, speed: float):
        """Generates MD5 hash to be used as key in redis"""
        # Removing language because langdetect is ass
        key_string = f"{text}-{voice}-{speed}"
        return hashlib.sha256(key_string.encode()).hexdigest()

    def get(self, key: str):
        value = self.redis.get(key)
        if value:
            # Add to access order
            self.redis.zadd("cache_access_order", {key: time.time()})
        return value

    def set(self, key: str, value: bytes):
        self.redis.set(key, value)
        # zadd to keep track of access order
        self.redis.zadd("cache_access_order", {key: time.time()})

    def __get_cache_size(self):
        return self.redis.info("memory")["used_memory"]

    def __cleanup_cache(self):
        cache_size = self.__get_cache_size()
        while cache_size > self.max_size_bytes:
            # Get the oldest item
            oldest_item = self.redis.zrange("cache_access_order", 0, 0)[0]
            if isinstance(oldest_item, bytes):
                print("Removing old items from cache")
                self.redis.delete(oldest_item)
                self.redis.zrem("cache_access_order", oldest_item)
            else:
                print(f"Oldest item is not a bytes object: {
                      oldest_item}. Something is wrong!")

            cache_size = self.__get_cache_size()

    def cache_info(self):
        memory = self.redis.info("memory")
        length = self.redis.zcard("cache_access_order")
        return {
            "memory": memory,
            "length": length
        }


def cached_tts(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(self, text: str) -> bytes:
        if not hasattr(self, 'cache') or not self.cache:
            # If no cache is set, just return the result of the function
            return func(self, text)

        cache_key = self.cache.generate_key(
            text, self.language, self.voice, self.speed)

        cached_audio = self.cache.get(cache_key)
        if cached_audio:
            print(f"Cache hit for {cache_key}")
            return cached_audio

        # Generate TTS if not cached
        audio = func(self, text)
        self.cache.set(cache_key, audio)
        return audio

    return wrapper


class TTS(ABC):
    def __init__(self, cache: Optional[Cache] = None):
        self.cache = cache

    def __detect_language(self, text: str):
        """Detect the language of the text, returns string like 'en' or 'nb' """
        try:
            return detect(text)
        except:
            return "en"

    @abstractmethod
    def _generate_tts(self, text: str):
        pass

    @cached_tts
    def tts(self, text: str) -> bytes:
        if self.language == "autodetect":
            print("Autodetecting language")
            self.language = self.__detect_language(text)
            print(f"Detected language: {self.language}")

            # TODO fix this
            if self.language == "nb":
                self.voice = "Aksel"
            else:
                self.voice = "Harry"

        return self._generate_tts(text)


class Narakeet(TTS):
    def __init__(self, api_key: str, voice: str = "Aksel", language: str = "autodetect", speed: float = 1.0, cache: Optional[Cache] = None):

        if not api_key:
            raise ValueError("API key is required")
        self.api_key = api_key
        self.voice = voice
        self.language = language
        self.speed = speed
        self.cache = cache

    def _generate_tts(self, text: str) -> bytes:
        url = f'https://api.narakeet.com/text-to-speech/mp3?voice={
            self.voice}&voice-speed={self.speed}&language={self.language}'

        options = {
            'headers': {
                'Accept': 'application/octet-stream',
                'Content-Type': 'text/plain',
                'x-api-key': self.api_key,
            },
            'data': text.encode('utf8')
        }
        start_time = time.time()
        response = requests.post(url, **options)
        if response.status_code != 200:
            print(f"Failed to generate TTS: {options}")
            print(f"URL: {url}")
            raise ValueError(f"Failed to geernate TTs: {
                             response.status_code} {response.text}")
        end_time = time.time()
        print(f"TTS generated in {end_time - start_time} seconds")
        return response.content


class Espeak(TTS):
    def __init__(self, language: str = "en", speed: float = 1.0, cache: Optional[Cache] = None):
        default_speed = 175

        self.language = language
        self.speed = speed * default_speed
        self.cache = cache
        self.voice = "default"

    def _generate_tts(self, text: str) -> bytes:
        espeak_result = subprocess.run(
            ['espeak-ng', '-v', self.language, '-s',
                str(self.speed), '--stdout', text],
            capture_output=True,
            check=True
        )

        return espeak_result.stdout
