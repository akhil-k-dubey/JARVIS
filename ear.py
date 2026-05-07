from __future__ import annotations

from typing import Optional
import os
import tempfile
import wave

try:
    import speech_recognition as sr  # pyright: ignore[reportMissingImports]
except ImportError:
    sr = None

try:
    import sounddevice as sd  # pyright: ignore[reportMissingImports]
except ImportError:
    sd = None

try:
    import numpy as np  # pyright: ignore[reportMissingImports]
except ImportError:
    np = None

try:
    from faster_whisper import WhisperModel  # pyright: ignore[reportMissingImports]
except ImportError:
    WhisperModel = None


def setup_mic(recognizer: Optional["sr.Recognizer"], debug) -> tuple[Optional["sr.Recognizer"], bool, str]:
    if sr is None:
        debug("SpeechRecognition not installed.")
        return None, False, "none"
    try:
        recognizer = sr.Recognizer()
        try:
            with sr.Microphone():
                pass
            debug("Mic backend: speech_recognition_mic.")
            return recognizer, True, "speech_recognition_mic"
        except Exception:
            debug("SpeechRecognition mic probe failed, trying sounddevice.")

        if sd is None or np is None:
            debug("sounddevice/numpy unavailable, mic disabled.")
            return None, False, "none"

        debug("Mic backend: sounddevice_record.")
        return recognizer, True, "sounddevice_record"
    except Exception:
        debug("Mic setup failed completely.")
        return None, False, "none"


def setup_stt_backend(
    stt_backend: str,
    whisper_model_size: str,
    whisper_device: str,
    whisper_compute_type: str,
    debug,
) -> tuple[str, Optional[object]]:
    if stt_backend != "whisper":
        debug("STT backend: google")
        return "google", None

    if WhisperModel is None:
        debug("faster-whisper not installed. Falling back to google.")
        return "google", None

    try:
        model = WhisperModel(
            whisper_model_size,
            device=whisper_device,
            compute_type=whisper_compute_type,
        )
        debug(
            f"STT backend: whisper ({whisper_model_size}, "
            f"device={whisper_device}, compute={whisper_compute_type})"
        )
        return "whisper", model
    except Exception as exc:
        debug(f"Whisper init failed, fallback to google: {exc}")
        return "google", None


def transcribe_audio_data(
    recognizer: Optional["sr.Recognizer"],
    audio_data: "sr.AudioData",
    stt_backend: str,
    whisper_model: Optional[object],
    stt_language: str,
    debug,
) -> Optional[str]:
    if stt_backend == "whisper" and whisper_model is not None:
        try:
            fd, wav_path = tempfile.mkstemp(suffix=".wav")
            os.close(fd)
            try:
                with wave.open(wav_path, "wb") as wav_file:
                    wav_file.setnchannels(1)
                    wav_file.setsampwidth(audio_data.sample_width)
                    wav_file.setframerate(audio_data.sample_rate)
                    wav_file.writeframes(audio_data.get_raw_data())

                segments, _ = whisper_model.transcribe(wav_path, language="en")
                transcript = " ".join(segment.text.strip() for segment in segments).strip()
                if transcript:
                    debug(f"STT transcript (whisper): {transcript}")
                    return transcript
                debug("STT transcript (whisper): <empty>")
                return None
            finally:
                try:
                    os.unlink(wav_path)
                except OSError:
                    pass
        except Exception as exc:
            debug(f"STT whisper failed: {exc}")
            return None

    if recognizer is None:
        return None

    try:
        transcript = recognizer.recognize_google(audio_data, language=stt_language)
        debug(f"STT transcript (google): {transcript}")
        return transcript
    except Exception as exc:
        debug(f"STT google failed: {type(exc).__name__}: {exc}")
        return None

