import numpy as np
import datetime
from pathlib import Path


class AudioProcessor:
    @staticmethod
    def calculate_adaptive_threshold(audio: np.ndarray, sample_rate: int) -> float:
        if len(audio) < sample_rate * 0.5:
            return -45.0

        if audio.dtype == np.int16:
            norm_audio = audio.astype(np.float32) / 32768.0
        else:
            norm_audio = audio.astype(np.float32)

        chunk_size = int(sample_rate * 0.1)
        num_chunks = len(norm_audio) // chunk_size
        noise_floors = []
        for i in range(min(num_chunks, 10)):
            chunk = norm_audio[i * chunk_size:(i + 1) * chunk_size]
            noise_floors.append(np.sqrt(np.mean(chunk ** 2)))

        noise_rms = min(noise_floors) if noise_floors else 0.001
        noise_db = 20 * np.log10(noise_rms + 1e-9)
        peak_rms = np.max(np.abs(norm_audio))
        peak_db = 20 * np.log10(peak_rms + 1e-9)
        threshold_db = max(noise_db + 8, peak_db - 28)
        return max(-55, min(-28, threshold_db))

    @staticmethod
    def remove_silence(audio: np.ndarray, sample_rate: int, threshold_db: float = -40) -> np.ndarray:
        threshold = 10 ** (threshold_db / 20)
        max_val = 32768 if audio.dtype == np.int16 else 1.0

        abs_audio = np.abs(audio) / max_val
        if len(abs_audio.shape) > 1:
            abs_audio = np.max(abs_audio, axis=1)

        chunk_size = int(sample_rate * 0.1)
        num_chunks = len(audio) // chunk_size
        if num_chunks == 0:
            return audio

        voice_chunks = np.zeros(num_chunks, dtype=bool)
        for i in range(num_chunks):
            chunk = abs_audio[i * chunk_size:(i + 1) * chunk_size]
            rms = np.sqrt(np.mean(chunk ** 2))
            if rms > threshold:
                voice_chunks[i] = True

        if not np.any(voice_chunks):
            return audio

        padded_chunks = np.zeros(num_chunks, dtype=bool)
        padding = 1
        for i in range(num_chunks):
            if voice_chunks[i]:
                start = max(0, i - padding)
                end = min(num_chunks, i + padding + 1)
                padded_chunks[start:end] = True

        keep_mask = np.ones(len(audio), dtype=bool)
        for i in range(num_chunks):
            if not padded_chunks[i]:
                keep_mask[i * chunk_size:(i + 1) * chunk_size] = False

        return audio[keep_mask]

    @staticmethod
    def save_recording(result, sample_rate: int, save_path,
                       remove_silence=False, silence_threshold=-40,
                       adaptive_silence=True):
        from scipy.io import wavfile
        import shutil

        if result is None:
            return None

        kind, data = result

        if kind == 'file':
            if not data or not Path(data).exists():
                return None
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'recording_{timestamp}.wav'
            dest = Path(save_path) / filename
            shutil.copy2(data, dest)
            return filename

        elif kind == 'frames':
            if not data:
                return None
            audio = np.concatenate(data, axis=0)
            original_length = len(audio)

            if remove_silence:
                target_threshold = silence_threshold
                if adaptive_silence:
                    target_threshold = AudioProcessor.calculate_adaptive_threshold(audio, sample_rate)
                audio = AudioProcessor.remove_silence(audio, sample_rate, threshold_db=target_threshold)

            if len(audio) < sample_rate * 0.1 and original_length > sample_rate * 1:
                audio = np.concatenate(data, axis=0)

            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'recording_{timestamp}.wav'
            file_path = Path(save_path) / filename
            wavfile.write(str(file_path), sample_rate, audio.astype(np.int16))
            return filename

        return None

    @staticmethod
    def load_wav_as_numpy(path):
        from scipy.io import wavfile
        try:
            fs, data = wavfile.read(str(path))
            return fs, data
        except Exception:
            return None, None
