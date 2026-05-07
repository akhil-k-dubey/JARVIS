from __future__ import annotations

from datetime import datetime
from typing import Optional
import argparse
import sys

from assistant import Jarvis
from brain import Brain
from commands import is_shutdown_command, is_wake_command
from voice import VoiceIO


def run(
    default_voice_mode: bool = True,
    debug_voice: bool = False,
    stt_backend: str = "google",
    whisper_model_size: str = "base.en",
    stt_language: str = "en-IN",
    tts_backend: str = "powershell",
    llm_backend: str = "ollama",
    llm_model: str = "auto",
    llm_base_url: str = "http://127.0.0.1:11434",
    llm_timeout: float = 20.0,
    llm_enabled: bool = True,
) -> None:
    brain = Brain(
        enabled=llm_enabled and llm_backend == "ollama",
        base_url=llm_base_url,
        model=llm_model,
        timeout_s=llm_timeout,
        debug=debug_voice,
    )
    agent = Jarvis(name="jarvis", brain=brain)
    voice = VoiceIO(
        debug=debug_voice,
        stt_backend=stt_backend,
        whisper_model_size=whisper_model_size,
        stt_language=stt_language,
        tts_backend=tts_backend,
    )
    voice.voice_mode = default_voice_mode

    # Announce online line immediately, then stay in standby for wake phrase flow.
    online_message = f"{agent.name.title()} online. Systems restored at {datetime.now().strftime('%I:%M %p')}."
    print(online_message)
    voice.speak(online_message)
    standby_message = agent.standby()
    print(standby_message)
    voice.speak(standby_message)
    print("Type 'help' to see commands. Use 'voice on' / 'voice off' to control voice mode.")

    # One-line voice readiness / fallback status.
    if voice.voice_mode and voice.mic_enabled and voice.tts_enabled:
        status_line = (
            f"Voice: READY "
            f"(backend={voice.mic_backend}, TTS={voice.tts_effective_backend})"
        )
    elif voice.voice_mode and (voice.mic_enabled or voice.tts_enabled):
        status_line = (
            "Voice: PARTIAL "
            f"(backend={voice.mic_backend}, "
            f"TTS={voice.tts_effective_backend if voice.tts_enabled else 'off'})"
        )
    elif voice.voice_mode:
        status_line = "Voice: FALLBACK (text-only; mic/TTS unavailable)"
    else:
        status_line = "Voice: DISABLED (text-only mode)"
    print(status_line)
    if debug_voice:
        print("[voice-debug] Debug mode enabled.")

    while agent.awake:
        user_input: Optional[str] = None

        if voice.voice_mode and voice.mic_enabled:
            spoken = voice.listen()
            if spoken:
                print(f"You (voice) > {spoken}")
                user_input = spoken

        if not user_input and (not voice.voice_mode or not voice.mic_enabled):
            try:
                user_input = input("You > ")
            except (EOFError, KeyboardInterrupt):
                print("\nPowering down. Until next time.")
                break
        if not user_input:
            continue

        normalized = user_input.strip().lower()
        if is_shutdown_command(normalized):
            response = "Powering down. Until next time."
            agent.awake = False
            print(f"{agent.name.title()} > {response}")
            voice.speak(response)
            break

        if not agent.activated:
            if is_wake_command(normalized, agent.name):
                response = agent.wake()
                print(f"{agent.name.title()} > {response}")
                voice.speak(response)
            else:
                response = (
                    f"In standby. Type 'wake up {agent.name}' to activate."
                )
                print(f"{agent.name.title()} > {response}")
                voice.speak(response)
            continue

        if is_wake_command(normalized, agent.name):
            response = "I am already online and listening."
            print(f"{agent.name.title()} > {response}")
            voice.speak(response)
            continue

        response = agent.handle(user_input)

        if normalized == "voice on":
            voice.voice_mode = True
        elif normalized == "voice off":
            voice.voice_mode = False

        print(f"{agent.name.title()} > {response}")
        voice.speak(response)

        if not agent.awake:
            break


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Jarvis assistant.")
    parser.add_argument(
        "--voice",
        dest="voice",
        action="store_true",
        help="Start Jarvis in voice mode (default).",
    )
    parser.add_argument(
        "--no-voice",
        dest="voice",
        action="store_false",
        help="Start Jarvis in text-only mode.",
    )
    parser.add_argument(
        "--debug-voice",
        action="store_true",
        help="Print microphone/TTS diagnostics while running.",
    )
    parser.add_argument(
        "--stt-backend",
        choices=["google", "whisper"],
        default="google",
        help="Speech-to-text backend. Use 'whisper' for local GPU/CPU transcription.",
    )
    parser.add_argument(
        "--whisper-model",
        default="base.en",
        help="Whisper model size for faster-whisper (tiny.en, base.en, small.en, etc).",
    )
    parser.add_argument(
        "--stt-language",
        default="en-IN",
        help="Google STT language locale (for example: en-IN, hi-IN, en-US).",
    )
    parser.add_argument(
        "--tts-backend",
        choices=["auto", "pyttsx3", "powershell", "none"],
        default="powershell",
        help=(
            "Text-to-speech backend. Default is 'powershell' for Windows reliability."
        ),
    )
    parser.add_argument(
        "--llm-backend",
        choices=["ollama", "none"],
        default="ollama",
        help="LLM backend for open-ended replies.",
    )
    parser.add_argument(
        "--llm-model",
        default="auto",
        help="Ollama model name. Use 'auto' to pick best installed model.",
    )
    parser.add_argument(
        "--llm-base-url",
        default="http://127.0.0.1:11434",
        help="Ollama server URL.",
    )
    parser.add_argument(
        "--llm-timeout",
        type=float,
        default=20.0,
        help="Timeout in seconds for LLM requests.",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Disable LLM brain and use rule-based responses only.",
    )
    parser.set_defaults(voice=True)

    args = parser.parse_args(sys.argv[1:])
    run(
        default_voice_mode=args.voice,
        debug_voice=args.debug_voice,
        stt_backend=args.stt_backend,
        whisper_model_size=args.whisper_model,
        stt_language=args.stt_language,
        tts_backend=args.tts_backend,
        llm_backend=args.llm_backend,
        llm_model=args.llm_model,
        llm_base_url=args.llm_base_url,
        llm_timeout=args.llm_timeout,
        llm_enabled=not args.no_llm,
    )
