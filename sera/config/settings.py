import json
import os
from pathlib import Path
from kivy.utils import platform


def _get_data_dir():
    if platform == 'android':
        from android.storage import app_storage_path
        return Path(app_storage_path())
    return Path.home() / 'Documents' / 'SERA Recordings'


SETTINGS_FILE = None


def _get_settings_file():
    global SETTINGS_FILE
    if SETTINGS_FILE is None:
        if platform == 'android':
            from android.storage import app_storage_path
            SETTINGS_FILE = Path(app_storage_path()) / 'sera_settings.json'
        else:
            SETTINGS_FILE = Path.home() / '.sera_settings.json'
    return SETTINGS_FILE


class AppSettings:
    _defaults = {
        'sample_rate': 44100,
        'channels': 1,
        'remove_silence': False,
        'silence_threshold': -40.0,
        'adaptive_silence': True,
        'director_switch_time': 5,
        'director_text': '',
        'director_text_pos': 7,
        'bgm_volume': 0.5,
        'rec_volume': 1.0,
    }

    def __init__(self):
        self._data = dict(self._defaults)
        self._load()

    def _load(self):
        try:
            f = _get_settings_file()
            if f.exists():
                with open(f, 'r') as fp:
                    saved = json.load(fp)
                self._data.update(saved)
        except Exception:
            pass

    def save(self):
        try:
            f = _get_settings_file()
            f.parent.mkdir(parents=True, exist_ok=True)
            with open(f, 'w') as fp:
                json.dump(self._data, fp)
        except Exception:
            pass

    @property
    def recordings_dir(self):
        d = self._data.get('recordings_dir', None)
        if d is None:
            d = str(_get_data_dir())
            self._data['recordings_dir'] = d
        Path(d).mkdir(parents=True, exist_ok=True)
        return Path(d)

    @recordings_dir.setter
    def recordings_dir(self, value):
        self._data['recordings_dir'] = str(value)
        self.save()

    @property
    def sample_rate(self):
        return self._data['sample_rate']

    @sample_rate.setter
    def sample_rate(self, value):
        self._data['sample_rate'] = int(value)
        self.save()

    @property
    def channels(self):
        return self._data['channels']

    @channels.setter
    def channels(self, value):
        self._data['channels'] = int(value)
        self.save()

    @property
    def remove_silence(self):
        return self._data['remove_silence']

    @remove_silence.setter
    def remove_silence(self, value):
        self._data['remove_silence'] = bool(value)
        self.save()

    @property
    def silence_threshold(self):
        return self._data['silence_threshold']

    @silence_threshold.setter
    def silence_threshold(self, value):
        self._data['silence_threshold'] = float(value)
        self.save()

    @property
    def adaptive_silence(self):
        return self._data['adaptive_silence']

    @adaptive_silence.setter
    def adaptive_silence(self, value):
        self._data['adaptive_silence'] = bool(value)
        self.save()

    @property
    def director_switch_time(self):
        return self._data['director_switch_time']

    @director_switch_time.setter
    def director_switch_time(self, value):
        self._data['director_switch_time'] = int(value)
        self.save()

    @property
    def director_text(self):
        return self._data['director_text']

    @director_text.setter
    def director_text(self, value):
        self._data['director_text'] = str(value)
        self.save()

    @property
    def director_text_pos(self):
        return self._data['director_text_pos']

    @director_text_pos.setter
    def director_text_pos(self, value):
        self._data['director_text_pos'] = int(value)
        self.save()

    @property
    def bgm_volume(self):
        return self._data['bgm_volume']

    @bgm_volume.setter
    def bgm_volume(self, value):
        self._data['bgm_volume'] = float(value)
        self.save()

    @property
    def rec_volume(self):
        return self._data['rec_volume']

    @rec_volume.setter
    def rec_volume(self, value):
        self._data['rec_volume'] = float(value)
        self.save()
