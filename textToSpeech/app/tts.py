from langdetect import detect
from abc import ABC, abstractmethod
from logging_config import logger
import requests
import time
import subprocess
from typing import Optional, Callable
import redis
import hashlib
import openai
from functools import wraps


class Cache():
    def __init__(self, redis_url: str, max_size_mb: int = 100):
        self.redis = redis.Redis.from_url(redis_url)
        self.enabled = True

        self.max_size_bytes = max_size_mb * 1024 * 1024

    def generate_key(self, text: str, language: str, voice: str, speed: float, model: str):
        """Generates MD5 hash to be used as key in redis"""
        # Removing language because langdetect is ass
        key_string = f"{text}-{voice}-{speed}-{model}"
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
                logger.info(f"Removing old items from cache: {oldest_item}")
                self.redis.delete(oldest_item)
                self.redis.zrem("cache_access_order", oldest_item)
            else:
                logger.error(f"Oldest item is not a bytes object: {
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
            text, self.language, self.voice, self.speed, self.model)

        cached_audio = self.cache.get(cache_key)
        if cached_audio:
            logger.info(f"Cache hit for {cache_key}")
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
            logger.info("Autodetecting language")
            self.language = self.__detect_language(text)
            logger.info(f"Detected language: {self.language}")

            # TODO fix this
            if self.language == "nb":
                self.voice = "Aksel"
            else:
                self.voice = "Harry"

        return self._generate_tts(text)


class Narakeet(TTS):
    def __init__(self, api_key: str, voice: str = "Matt", language: str = "autodetect", speed: float = 1.0, cache: Optional[Cache] = None):

        logger.debug("Initializing Narakeet")

        if not api_key:
            raise ValueError("API key is required")
        self.api_key = api_key
        self.language = language
        self.speed = speed
        self.cache = cache
        self.model = "narakeet"
        self.supported_voices = ["Matt","Linda","Betty","Jessica","Ben","Melissa","Chris","Shannon","Mike","Bill","Sarah","Jeff","Maggie","Lisa","Mary","Karen","Tom","Jack","Joanna","Dustin","Tony","Kelly","Wanda","Rodney","Britney","Steve","Jennifer","Julia","Rhonda","Martin","John","Will","Morgan","Eddie","Jodie","Debbie","Nancy","Kim","Lucy","Beverly","Amber","Ashley","Mark","Connie","Sandra","Holly","Harrison","Jackie","Kirk","Mia","Chuck","Ronald","Brad","Paul","Julie","Ivy","Bridget","Tracy","Walter","Eric","Amanda","Tina","Chad","Gary","Raymond","Cindy","Jackson","Roger","Cora","Tyrell","Wyatt","Earl","Forrest","Jeb","Latoya","Dolly","Savannah","Georgia","Travis","Colt","Jerome","Kendrick","Jada","Sal","Tyrone","Curtis","Shaniqua","Duane","Eva","Pablo","Howard","Quentin","Larry","Deshawn","Raul","Denzel","Carl","Jade","Suzie"]

        if voice not in self.supported_voices:
            self.voice = "Matt"
        else:
            self.voice = voice

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
            logger.error(f"Failed to generate TTS: {options}")
            logger.error(f"URL: {url}")
            raise ValueError(f"Failed to geernate TTs: {
                             response.status_code} {response.text}")
        end_time = time.time()
        logger.info(f"TTS generated in {round(end_time - start_time, 2)} seconds")
        return response.content


class Espeak(TTS):
    def __init__(self, language: str = "en", speed: float = 1.0, cache: Optional[Cache] = None):
        logger.debug("Initializing Espeak")
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


class OpenAI(TTS):
    def __init__(self, api_key: str, voice: str = "alloy", language: str = "en", model: str = "tts-1", speed: float = 1.0, cache: Optional[Cache] = None):
        logger.debug("Initializing OpenAI")
        self.api_key = api_key
        self.language = language
        self.speed = speed
        self.cache = cache
        self.voice = voice
        self.openai = openai.OpenAI(api_key=self.api_key)
        supported_voices = [
            "alloy",
            "ash",
            "ballad",
            "coral",
            "echo",
            "fable",
            "onyx",
            "nova",
            "sage",
            "shimmer"]

        if voice not in supported_voices:
            self.voice = "alloy"
        else:
            self.voice = voice

        supported_models = ["gpt-4o-mini-tts", "tts-1", "tts-1-hd"]
        if model not in supported_models:
            self.model = "tts-1"
        else:
            self.model = model

    def _generate_tts(self, text: str) -> bytes:
        logger.trace(f"Generating TTS for {text} with model {self.model} and voice {self.voice}")
        start_time = time.time()
        response = self.openai.audio.speech.create(
            model=self.model,
            voice=self.voice,
            input=text,
            speed=self.speed
        )
        end_time = time.time()
        logger.debug(f"TTS generated in {round(end_time - start_time, 2)} seconds")
        return response.content


