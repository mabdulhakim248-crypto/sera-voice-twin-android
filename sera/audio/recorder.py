import os
import tempfile
from kivy.utils import platform


class AudioRecorder:
    def __init__(self, sample_rate: int = 44100, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.is_recording = False
        self.is_paused = False
        self._temp_file = None
        self._audio = None

        if platform == 'android':
            self._backend = 'android'
            self._init_android()
        else:
            self._backend = 'sounddevice'
            self._stream = None
            self._frames = []

    def _init_android(self):
        try:
            from plyer import audio as plyer_audio
            self._plyer_audio = plyer_audio
        except Exception:
            self._plyer_audio = None

    def start(self, callback=None):
        if self.is_recording:
            return False
        self._callback = callback
        self.is_recording = True
        self.is_paused = False

        if self._backend == 'android':
            self._start_android()
        else:
            self._start_sounddevice(callback)
        return True

    def _start_android(self):
        fd, path = tempfile.mkstemp(suffix='.wav')
        os.close(fd)
        self._temp_file = path
        if self._plyer_audio:
            try:
                self._plyer_audio.start(filename=path)
            except Exception as e:
                raise RuntimeError(f'Could not start recording: {e}')

    def _start_sounddevice(self, callback):
        import sounddevice as sd
        self._frames = []

        def _cb(indata, frames, time, status):
            import numpy as np
            if not self.is_paused:
                self._frames.append(indata.copy())
            if callback:
                callback(indata, frames, time, status)

        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype='int16',
            callback=_cb
        )
        self._stream.start()

    def pause(self):
        if self.is_recording:
            self.is_paused = True

    def resume(self):
        if self.is_recording:
            self.is_paused = False

    def stop(self):
        if not self.is_recording:
            return None

        self.is_recording = False
        self.is_paused = False

        if self._backend == 'android':
            return self._stop_android()
        else:
            return self._stop_sounddevice()

    def _stop_android(self):
        if self._plyer_audio:
            try:
                self._plyer_audio.stop()
            except Exception:
                pass
        if self._temp_file and os.path.exists(self._temp_file):
            return ('file', self._temp_file)
        return None

    def _stop_sounddevice(self):
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        frames = self._frames[:]
        self._frames = []
        return ('frames', frames) if frames else None

    def cleanup(self):
        if self._backend == 'android' and self._plyer_audio:
            try:
                self._plyer_audio.stop()
            except Exception:
                pass
        elif self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
