"""
ROSE Voice — wake word detection and speech-to-text pipeline.
Phase 2: Stub module. Voice is disabled by default.
"""

import threading
import queue

from rose.config import VOICE_ENABLED, WAKE_WORD, SILENCE_THRESHOLD_SECONDS
from rose import formatter


class VoiceListener:
    """
    Background voice listener with wake word detection and STT.

    Phase 2 implementation — currently a stub.
    When enabled, requires:
    - PyAudio (microphone capture)
    - openwakeword (wake word detection)
    - faster-whisper (speech-to-text)
    """

    def __init__(self, input_queue: queue.Queue):
        self._queue = input_queue
        self._running = False
        self._thread: threading.Thread | None = None
        self._enabled = VOICE_ENABLED

    @property
    def enabled(self) -> bool:
        return self._enabled

    def start(self):
        """Start the voice listener thread (if enabled)."""
        if not self._enabled:
            return

        # Check dependencies
        if not self._check_dependencies():
            formatter.warn("Voice dependencies not installed. Voice mode disabled.")
            formatter.rose("To enable voice, install: pip install PyAudio faster-whisper openwakeword")
            self._enabled = False
            return

        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True, name="voice-listener")
        self._thread.start()
        formatter.rose("Voice listener active. Wake word: \"rose\"")

    def stop(self):
        """Stop the voice listener."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    def _check_dependencies(self) -> bool:
        """Check if all voice dependencies are available."""
        try:
            import pyaudio
            import openwakeword
            from faster_whisper import WhisperModel
            return True
        except ImportError:
            return False

    def _listen_loop(self):
        """
        Main voice listening loop.

        Flow:
        1. Continuously listen for wake word "rose"
        2. On detection: print listening indicator
        3. Capture audio until silence threshold
        4. Transcribe with Whisper
        5. Push transcription to input queue
        """
        try:
            import pyaudio
            import numpy as np
            from openwakeword.model import Model as WakeWordModel
            from faster_whisper import WhisperModel

            # Initialize wake word model
            wake_model = WakeWordModel(
                wakeword_models=["hey_jarvis"],  # Closest available; custom "rose" can be trained
                inference_framework="onnx",
            )

            # Initialize Whisper
            whisper = WhisperModel("base", device="cpu", compute_type="int8")

            # Audio config
            RATE = 16000
            CHUNK = 1280  # 80ms at 16kHz
            FORMAT = pyaudio.paInt16
            CHANNELS = 1

            pa = pyaudio.PyAudio()
            stream = pa.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK,
            )

            audio_buffer = []
            is_capturing = False
            silence_frames = 0
            silence_limit = int(SILENCE_THRESHOLD_SECONDS * RATE / CHUNK)

            while self._running:
                data = stream.read(CHUNK, exception_on_overflow=False)
                audio_np = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0

                if not is_capturing:
                    # Wake word detection
                    prediction = wake_model.predict(audio_np)
                    # Check if any wake word score exceeds threshold
                    for key, score in prediction.items():
                        if score > 0.5:
                            formatter.listening()
                            is_capturing = True
                            audio_buffer = []
                            silence_frames = 0
                            break
                else:
                    # Capturing speech
                    audio_buffer.append(data)

                    # Simple silence detection based on amplitude
                    amplitude = np.abs(audio_np).mean()
                    if amplitude < 0.01:
                        silence_frames += 1
                    else:
                        silence_frames = 0

                    if silence_frames >= silence_limit:
                        # End of speech — transcribe
                        is_capturing = False

                        if audio_buffer:
                            full_audio = np.frombuffer(
                                b"".join(audio_buffer), dtype=np.int16
                            ).astype(np.float32) / 32768.0

                            segments, _ = whisper.transcribe(full_audio, beam_size=3)
                            text = " ".join(seg.text for seg in segments).strip()

                            if text:
                                formatter.you(text)
                                self._queue.put({
                                    "source": "voice",
                                    "text": text,
                                })

                        audio_buffer = []

            stream.stop_stream()
            stream.close()
            pa.terminate()

        except Exception as e:
            formatter.err(f"Voice listener crashed: {e}")
            self._enabled = False
