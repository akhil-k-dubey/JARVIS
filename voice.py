from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import os
import subprocess
import time

from ear import np, sd, sr, setup_mic, setup_stt_backend, transcribe_audio_data

try:
    import pyttsx3  # pyright: ignore[reportMissingImports]
except ImportError:
    pyttsx3 = None


@dataclass
class VoiceIO:
    """Handles microphone input and text-to-speech output."""

    voice_mode: bool = True
    tts_enabled: bool = False
    mic_enabled: bool = False
    recognizer: Optional["sr.Recognizer"] = None
    tts_engine: Optional[object] = None
    tts_backend: str = "auto"  # "auto" | "pyttsx3" | "powershell" | "none"
    tts_effective_backend: str = "none"
    mic_backend: str = "none"  # "speech_recognition_mic" | "sounddevice_record" | "none"
    stt_backend: str = "google"  # "google" | "whisper"
    whisper_model_size: str = "base.en"
    whisper_device: str = "auto"
    whisper_compute_type: str = "auto"
    stt_language: str = "en-IN"
    mic_phrase_seconds: int = 5
    min_input_rms: float = 220.0
    post_tts_cooldown_s: float = 1.0
    debug: bool = False
    whisper_model: Optional[object] = None
    selected_voice_name: str = "default"
    _last_tts_time: float = 0.0

    def __post_init__(self) -> None:
        self._setup_tts()
        self._setup_mic()
        self._setup_stt_backend()

    def _debug(self, message: str) -> None:
        if self.debug:
            print(f"[voice-debug] {message}")

    def _setup_tts(self) -> None:
        requested_backend = self.tts_backend.lower().strip()
        if requested_backend == "none":
            self.tts_enabled = False
            self.tts_engine = None
            self.tts_effective_backend = "none"
            self._debug("TTS disabled by configuration.")
            return

        def init_powershell() -> bool:
            if os.name != "nt":
                return False
            self.tts_engine = None
            self.tts_enabled = True
            self.tts_effective_backend = "powershell"
            self.selected_voice_name = "windows default"
            self._debug("TTS initialized with PowerShell backend.")
            return True

        def init_pyttsx3() -> bool:
            if pyttsx3 is None:
                self._debug("pyttsx3 not installed.")
                return False
            try:
                if os.name == "nt":
                    self.tts_engine = pyttsx3.init(driverName="sapi5")
                else:
                    self.tts_engine = pyttsx3.init()
                self._configure_jarvis_voice()
                self.tts_enabled = True
                self.tts_effective_backend = "pyttsx3"
                self._debug(
                    f"TTS initialized successfully. Voice={self.selected_voice_name}"
                )
                return True
            except Exception as exc:
                self._debug(f"pyttsx3 init failed: {exc}")
                return False

        if requested_backend == "pyttsx3":
            order = ["pyttsx3"]
        elif requested_backend == "powershell":
            order = ["powershell"]
        else:
            order = ["pyttsx3", "powershell"] if os.name == "nt" else ["pyttsx3"]

        for backend in order:
            if backend == "pyttsx3" and init_pyttsx3():
                return
            if backend == "powershell" and init_powershell():
                return

        self.tts_engine = None
        self.tts_enabled = False
        self.tts_effective_backend = "none"
        self._debug("TTS initialization failed for all requested backends.")

    def _configure_jarvis_voice(self) -> None:
        if self.tts_engine is None:
            return
        try:
            voices = self.tts_engine.getProperty("voices") or []
        except Exception:
            voices = []

        preferred_tokens = ("david", "mark", "zira", "english")
        selected_voice_id: Optional[str] = None

        for voice in voices:
            name = str(getattr(voice, "name", "")).lower()
            voice_id = str(getattr(voice, "id", ""))
            if any(token in name for token in preferred_tokens):
                selected_voice_id = voice_id
                self.selected_voice_name = str(getattr(voice, "name", "default"))
                break

        if selected_voice_id is None and voices:
            first_voice = voices[0]
            selected_voice_id = str(getattr(first_voice, "id", ""))
            self.selected_voice_name = str(getattr(first_voice, "name", "default"))

        if selected_voice_id:
            self.tts_engine.setProperty("voice", selected_voice_id)
        self.tts_engine.setProperty("rate", 175)
        self.tts_engine.setProperty("volume", 1.0)

    def _speak_with_powershell(self, text: str) -> None:
        escaped = text.replace("'", "''")
        script = (
            "Add-Type -AssemblyName System.Speech; "
            "$speak = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$speak.Speak('{escaped}');"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            check=True,
            capture_output=True,
            text=True,
        )

    def _setup_mic(self) -> None:
        self.recognizer, self.mic_enabled, self.mic_backend = setup_mic(
            self.recognizer, self._debug
        )

    def _setup_stt_backend(self) -> None:
        self.stt_backend, self.whisper_model = setup_stt_backend(
            self.stt_backend,
            self.whisper_model_size,
            self.whisper_device,
            self.whisper_compute_type,
            self._debug,
        )

    def speak(self, text: str) -> None:
        if not self.voice_mode:
            return

        def backend_ready() -> bool:
            if not self.tts_enabled:
                return False
            if self.tts_effective_backend == "pyttsx3":
                return self.tts_engine is not None
            if self.tts_effective_backend == "powershell":
                return True
            return False

        if not backend_ready():
            self._debug("TTS not ready, attempting reinitialize.")
            self._setup_tts()
            if not backend_ready():
                self._debug("TTS reinitialize failed; skipping speech.")
                return

        try:
            if self.tts_effective_backend == "powershell":
                self._speak_with_powershell(text)
            else:
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
            self._last_tts_time = time.monotonic()
            self._debug(f"TTS spoke ({self.tts_effective_backend}): {text}")
        except Exception as exc:
            self._debug(f"TTS primary backend failed: {type(exc).__name__}: {exc}")
            try:
                if self.tts_effective_backend == "powershell" and pyttsx3 is not None:
                    self._debug("Trying runtime fallback to pyttsx3.")
                    self.tts_engine = pyttsx3.init()
                    self._configure_jarvis_voice()
                    self.tts_effective_backend = "pyttsx3"
                    self.tts_enabled = True
                    self.tts_engine.say(text)
                    self.tts_engine.runAndWait()
                    self._last_tts_time = time.monotonic()
                    self._debug(f"TTS spoke ({self.tts_effective_backend}): {text}")
                    return
                if self.tts_effective_backend == "pyttsx3" and os.name == "nt":
                    self._debug("Trying runtime fallback to PowerShell.")
                    self.tts_effective_backend = "powershell"
                    self.tts_engine = None
                    self.tts_enabled = True
                    self._speak_with_powershell(text)
                    self._last_tts_time = time.monotonic()
                    self._debug(f"TTS spoke ({self.tts_effective_backend}): {text}")
                    return
            except Exception as fallback_exc:
                self._debug(
                    f"TTS fallback failed: {type(fallback_exc).__name__}: {fallback_exc}"
                )

            self.tts_enabled = False
            self._debug("TTS disabled after primary+fallback failure.")

    def listen(self) -> Optional[str]:
        if (
            not self.voice_mode
            or not self.mic_enabled
            or self.recognizer is None
            or sr is None
        ):
            return None
        if time.monotonic() - self._last_tts_time < self.post_tts_cooldown_s:
            return None

        if self.mic_backend == "speech_recognition_mic":
            try:
                with sr.Microphone() as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.4)
                    audio = self.recognizer.listen(
                        source, timeout=3, phrase_time_limit=4
                    )
                return transcribe_audio_data(
                    self.recognizer,
                    audio,
                    self.stt_backend,
                    self.whisper_model,
                    self.stt_language,
                    self._debug,
                )
            except Exception as exc:
                self._debug(f"STT (sr mic) failed: {exc}")
                return None

        if self.mic_backend == "sounddevice_record":
            try:
                sample_rate = 16000
                phrase_seconds = self.mic_phrase_seconds
                frames = int(sample_rate * phrase_seconds)
                audio = sd.rec(frames, samplerate=sample_rate, channels=1, dtype=np.int16)
                sd.wait()
                pcm16 = audio.reshape(-1)
                rms = float(np.sqrt(np.mean(np.square(pcm16.astype(np.float32)))))
                if rms < self.min_input_rms:
                    self._debug(f"STT skipped: low input level (rms={rms:.1f})")
                    return None
                audio_data = sr.AudioData(
                    pcm16.tobytes(), sample_rate=sample_rate, sample_width=2
                )
                return transcribe_audio_data(
                    self.recognizer,
                    audio_data,
                    self.stt_backend,
                    self.whisper_model,
                    self.stt_language,
                    self._debug,
                )
            except Exception as exc:
                self._debug(f"STT (sounddevice) failed: {exc}")
                return None

        return None

