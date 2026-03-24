import os
import random
import datetime

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.slider import Slider
from kivy.uix.switch import Switch
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.uix.image import Image as KivyImage
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.clock import Clock
from kivy.utils import platform
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.core.audio import SoundLoader

from ..config.settings import AppSettings
from ..audio.recorder import AudioRecorder
from ..audio.processor import AudioProcessor


# ─── Colors ───────────────────────────────────────────────────────────────────
BG       = (0.12, 0.12, 0.14, 1)
SURFACE  = (0.17, 0.17, 0.20, 1)
ACCENT   = (0.30, 0.80, 0.64, 1)
RED      = (0.91, 0.30, 0.24, 1)
ORANGE   = (0.95, 0.61, 0.07, 1)
TEXT     = (1, 1, 1, 1)
SUBTEXT  = (0.58, 0.65, 0.65, 1)


def _btn(text, color=ACCENT, **kw):
    b = Button(
        text=text,
        background_normal='',
        background_color=color,
        color=TEXT,
        bold=True,
        size_hint_y=None,
        height=48,
        **kw
    )
    return b


def _label(text, color=TEXT, size=14, bold=False, **kw):
    return Label(text=text, color=color, font_size=size, bold=bold,
                 size_hint_y=None, height=32, **kw)


class SeraMainScreen(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation='vertical', **kw)
        self.settings = AppSettings()
        self.recorder = AudioRecorder(self.settings.sample_rate, self.settings.channels)

        self._start_time = None
        self._last_rms = 0.0
        self._timer_event = None
        self._audio_result = None

        self._director_images = []
        self._current_img_idx = 0
        self._director_event = None
        self._bgm_sound = None

        self._build_ui()
        self._refresh_btn_states()

    # ──────────────────────────── UI BUILD ────────────────────────────────────

    def _build_ui(self):
        with self.canvas.before:
            Color(*BG)
            self._bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        header = self._build_header()
        self.add_widget(header)

        self._tabs = TabbedPanel(do_default_tab=False, tab_width=160,
                                 tab_height=40, background_color=SURFACE)

        rec_tab = TabbedPanelItem(text='RECORDER')
        rec_tab.add_widget(self._build_recorder_tab())
        self._tabs.add_widget(rec_tab)

        dir_tab = TabbedPanelItem(text='DIRECTOR')
        dir_tab.add_widget(self._build_director_tab())
        self._tabs.add_widget(dir_tab)

        self._tabs.default_tab = rec_tab
        self.add_widget(self._tabs)

    def _update_bg(self, *_):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size

    def _build_header(self):
        box = BoxLayout(size_hint_y=None, height=56, padding=[16, 8])
        with box.canvas.before:
            Color(*SURFACE)
            self._hdr_rect = Rectangle(pos=box.pos, size=box.size)
        box.bind(pos=lambda *_: setattr(self._hdr_rect, 'pos', box.pos),
                 size=lambda *_: setattr(self._hdr_rect, 'size', box.size))
        lbl = Label(text='SERA Voice Twin', color=ACCENT,
                    font_size=20, bold=True, halign='left')
        lbl.bind(size=lambda *_: setattr(lbl, 'text_size', lbl.size))
        box.add_widget(lbl)
        return box

    # ──────────────────────── RECORDER TAB ───────────────────────────────────

    def _build_recorder_tab(self):
        root = ScrollView()
        layout = BoxLayout(orientation='vertical', padding=16, spacing=12,
                           size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))

        # Status
        self._status_lbl = Label(text='Ready to record', color=SUBTEXT,
                                 font_size=13, size_hint_y=None, height=28)
        layout.add_widget(self._status_lbl)

        # Timer
        self._timer_lbl = Label(text='00:00:00', color=TEXT,
                                font_size=42, bold=True,
                                size_hint_y=None, height=60)
        layout.add_widget(self._timer_lbl)

        # Level meter (5 bars)
        meter_row = GridLayout(cols=5, spacing=4, size_hint_y=None, height=16)
        self._meters = []
        for _ in range(5):
            pb = ProgressBar(max=100, value=0)
            self._meters.append(pb)
            meter_row.add_widget(pb)
        layout.add_widget(meter_row)

        self._level_lbl = Label(text='PEAK RMS: 0%', color=SUBTEXT,
                                font_size=12, size_hint_y=None, height=24)
        layout.add_widget(self._level_lbl)

        # Recording buttons
        rec_grid = GridLayout(cols=2, spacing=8, size_hint_y=None, height=112)
        self._btn_start  = _btn('Record',  color=RED)
        self._btn_pause  = _btn('Pause',   color=ORANGE)
        self._btn_resume = _btn('Resume',  color=ACCENT)
        self._btn_stop   = _btn('Stop/Save', color=(0.4, 0.4, 0.4, 1))
        for b in [self._btn_start, self._btn_pause, self._btn_resume, self._btn_stop]:
            rec_grid.add_widget(b)
        self._btn_start.bind(on_release=lambda _: self.start_recording())
        self._btn_pause.bind(on_release=lambda _: self.pause_recording())
        self._btn_resume.bind(on_release=lambda _: self.resume_recording())
        self._btn_stop.bind(on_release=lambda _: self.stop_and_save())
        layout.add_widget(rec_grid)

        # Playback buttons
        play_lbl = Label(text='Preview Playback', color=SUBTEXT,
                         font_size=12, size_hint_y=None, height=24)
        layout.add_widget(play_lbl)
        play_grid = GridLayout(cols=3, spacing=8, size_hint_y=None, height=52)
        self._btn_play        = _btn('Play',   color=ACCENT)
        self._btn_play_pause  = _btn('Pause',  color=ORANGE)
        self._btn_play_resume = _btn('Resume', color=ACCENT)
        for b in [self._btn_play, self._btn_play_pause, self._btn_play_resume]:
            play_grid.add_widget(b)
        self._btn_play.bind(on_release=lambda _: self.start_play())
        self._btn_play_pause.bind(on_release=lambda _: self.pause_play())
        self._btn_play_resume.bind(on_release=lambda _: self.resume_play())
        layout.add_widget(play_grid)

        # Settings button
        self._btn_settings = _btn('Settings', color=SURFACE,
                                  size_hint_y=None, height=44)
        self._btn_settings.color = ACCENT
        self._btn_settings.bind(on_release=lambda _: self.open_settings())
        layout.add_widget(self._btn_settings)

        root.add_widget(layout)
        return root

    # ──────────────────────── DIRECTOR TAB ───────────────────────────────────

    def _build_director_tab(self):
        root = ScrollView()
        layout = BoxLayout(orientation='vertical', padding=16, spacing=12,
                           size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))

        # Image display
        img_box = BoxLayout(size_hint_y=None, height=220)
        with img_box.canvas.before:
            Color(0, 0, 0, 1)
            self._img_bg = Rectangle(pos=img_box.pos, size=img_box.size)
        img_box.bind(pos=lambda *_: setattr(self._img_bg, 'pos', img_box.pos),
                     size=lambda *_: setattr(self._img_bg, 'size', img_box.size))
        self._director_img = KivyImage(allow_stretch=True, keep_ratio=True)
        img_box.add_widget(self._director_img)
        layout.add_widget(img_box)

        # Overlay text label on image (simulated)
        self._overlay_lbl = Label(text='', color=TEXT, font_size=16, bold=True,
                                  size_hint_y=None, height=28)
        layout.add_widget(self._overlay_lbl)

        # Select images button
        self._btn_imgs = _btn('Select Images...', color=SURFACE)
        self._btn_imgs.color = ACCENT
        self._img_count_lbl = Label(text='No images loaded.', color=SUBTEXT,
                                    font_size=12, size_hint_y=None, height=24)
        self._btn_imgs.bind(on_release=self._on_select_images)
        layout.add_widget(self._btn_imgs)
        layout.add_widget(self._img_count_lbl)

        # Select music button
        self._btn_bgm = _btn('Select Background Music...', color=SURFACE)
        self._btn_bgm.color = ACCENT
        self._music_lbl = Label(text='No music loaded.', color=SUBTEXT,
                                font_size=12, size_hint_y=None, height=24)
        self._btn_bgm.bind(on_release=self._on_select_music)
        layout.add_widget(self._btn_bgm)
        layout.add_widget(self._music_lbl)

        # Text overlay input
        txt_row = BoxLayout(size_hint_y=None, height=40, spacing=8)
        txt_row.add_widget(Label(text='Overlay Text:', color=TEXT,
                                 font_size=13, size_hint_x=None, width=110))
        self._overlay_input = TextInput(multiline=False, hint_text='Enter overlay text...')
        self._overlay_input.bind(text=self._on_overlay_text)
        txt_row.add_widget(self._overlay_input)
        layout.add_widget(txt_row)

        # Position spinner
        pos_row = BoxLayout(size_hint_y=None, height=40, spacing=8)
        pos_row.add_widget(Label(text='Position:', color=TEXT,
                                 font_size=13, size_hint_x=None, width=80))
        self._pos_spinner = Spinner(
            text='Bottom Center',
            values=['Top Left', 'Top Center', 'Top Right',
                    'Center Left', 'Center', 'Center Right',
                    'Bottom Left', 'Bottom Center', 'Bottom Right'],
            size_hint_x=1, height=40
        )
        self._pos_spinner.bind(text=self._on_pos_changed)
        pos_row.add_widget(self._pos_spinner)
        layout.add_widget(pos_row)

        # Switch duration
        spd_row = BoxLayout(size_hint_y=None, height=40, spacing=8)
        spd_row.add_widget(Label(text='Switch (s):', color=TEXT,
                                 font_size=13, size_hint_x=None, width=90))
        self._switch_slider = Slider(min=1, max=60,
                                     value=self.settings.director_switch_time,
                                     step=1)
        self._switch_lbl = Label(text=str(self.settings.director_switch_time),
                                 color=ACCENT, font_size=13,
                                 size_hint_x=None, width=30)
        self._switch_slider.bind(value=self._on_speed_changed)
        spd_row.add_widget(self._switch_slider)
        spd_row.add_widget(self._switch_lbl)
        layout.add_widget(spd_row)

        # Toggle button
        self._btn_toggle_dir = _btn('Start Live Preview', color=ACCENT)
        self._btn_toggle_dir.bind(on_release=self._on_toggle_director)
        layout.add_widget(self._btn_toggle_dir)

        root.add_widget(layout)
        return root

    # ──────────────────────── RECORDING LOGIC ────────────────────────────────

    def start_recording(self):
        if self.recorder.is_recording:
            return
        self._audio_result = None
        try:
            self.recorder = AudioRecorder(self.settings.sample_rate, self.settings.channels)
            self.recorder.start(self._audio_callback)
            self._start_time = datetime.datetime.now()
            if self._timer_event:
                self._timer_event.cancel()
            self._timer_event = Clock.schedule_interval(self._on_timer, 0.1)
            self._set_status('RECORDING [ACTIVE]', RED)
            self._start_director_if_needed()
            self._refresh_btn_states()
        except Exception as e:
            self._show_error(str(e))

    def _audio_callback(self, indata, frames, time, status):
        import numpy as np
        if len(indata) > 0:
            rms = float(np.sqrt(np.mean(indata.astype(np.float32) ** 2)))
        else:
            rms = 0.0
        self._last_rms = rms

    def pause_recording(self):
        self.recorder.pause()
        self._set_status('AUDIO ENGINE [SUSPENDED]', ORANGE)
        self._refresh_btn_states()

    def resume_recording(self):
        self.recorder.resume()
        self._set_status('RECORDING [ACTIVE]', RED)
        self._refresh_btn_states()

    def stop_and_save(self):
        if self._timer_event:
            self._timer_event.cancel()
            self._timer_event = None
        self._stop_director()
        result = self.recorder.stop()
        self._audio_result = result

        if result is None:
            self._set_status('Ready', SUBTEXT)
            self._timer_lbl.text = '00:00:00'
            self._refresh_btn_states()
            return

        try:
            filename = AudioProcessor.save_recording(
                result,
                self.settings.sample_rate,
                self.settings.recordings_dir,
                remove_silence=self.settings.remove_silence,
                silence_threshold=self.settings.silence_threshold,
                adaptive_silence=self.settings.adaptive_silence
            )
            if filename:
                self._set_status(f'Saved: {filename}', ACCENT)
            else:
                self._set_status('Nothing recorded.', SUBTEXT)
        except Exception as e:
            self._set_status(f'Error saving: {e}', RED)

        self._timer_lbl.text = '00:00:00'
        self._refresh_btn_states()

    def _on_timer(self, dt):
        if self._start_time and self.recorder.is_recording and not self.recorder.is_paused:
            delta = datetime.datetime.now() - self._start_time
            self._timer_lbl.text = str(delta).split('.')[0]

        rms = self._last_rms
        percent = min(100, int((rms / 8000) * 100))
        self._level_lbl.text = f'PEAK RMS: {percent}%'
        for m in self._meters:
            v = min(100, max(0, percent + random.randint(-10, 10)))
            m.value = v

    # ──────────────────────── PLAYBACK LOGIC ─────────────────────────────────

    def start_play(self):
        if self._audio_result is None:
            return
        kind, data = self._audio_result
        if kind == 'frames' and data:
            import numpy as np
            from scipy.io import wavfile
            import tempfile
            audio = np.concatenate(data, axis=0)
            fd, path = tempfile.mkstemp(suffix='.wav')
            os.close(fd)
            wavfile.write(path, self.settings.sample_rate, audio.astype(np.int16))
            self._play_file(path)
        elif kind == 'file' and data:
            self._play_file(data)

    def _play_file(self, path):
        if self._bgm_sound:
            self._bgm_sound.stop()
        sound = SoundLoader.load(path)
        if sound:
            sound.volume = self.settings.rec_volume
            sound.play()
            self._current_play_sound = sound

    def pause_play(self):
        if hasattr(self, '_current_play_sound') and self._current_play_sound:
            try:
                self._current_play_sound.stop()
            except Exception:
                pass

    def resume_play(self):
        if hasattr(self, '_current_play_sound') and self._current_play_sound:
            try:
                self._current_play_sound.play()
            except Exception:
                pass

    # ──────────────────────── DIRECTOR LOGIC ─────────────────────────────────

    def _on_select_images(self, *_):
        if platform == 'android':
            self._show_info('On Android, place images in /sdcard/SERA/images/ folder and they will be loaded automatically.')
            self._load_android_images()
        else:
            self._show_desktop_image_picker()

    def _show_desktop_image_picker(self):
        from kivy.uix.filechooser import FileChooserListView
        content = BoxLayout(orientation='vertical')
        fc = FileChooserListView(filters=['*.jpg', '*.jpeg', '*.png'],
                                 multiselect=True)
        btn_row = BoxLayout(size_hint_y=None, height=44, spacing=8)
        ok_btn = _btn('OK', color=ACCENT)
        cancel_btn = _btn('Cancel', color=(0.4, 0.4, 0.4, 1))
        btn_row.add_widget(ok_btn)
        btn_row.add_widget(cancel_btn)
        content.add_widget(fc)
        content.add_widget(btn_row)

        popup = Popup(title='Select Images', content=content,
                      size_hint=(0.95, 0.9))

        def on_ok(_):
            paths = fc.selection
            if paths:
                self._director_images = list(paths)
                self._img_count_lbl.text = f'{len(paths)} images loaded.'
            popup.dismiss()

        ok_btn.bind(on_release=on_ok)
        cancel_btn.bind(on_release=popup.dismiss)
        popup.open()

    def _load_android_images(self):
        import glob
        patterns = [
            '/sdcard/SERA/images/*.jpg',
            '/sdcard/SERA/images/*.jpeg',
            '/sdcard/SERA/images/*.png',
        ]
        found = []
        for p in patterns:
            found.extend(glob.glob(p))
        if found:
            self._director_images = found
            self._img_count_lbl.text = f'{len(found)} images loaded.'
        else:
            self._img_count_lbl.text = 'No images found in /sdcard/SERA/images/'

    def _on_select_music(self, *_):
        if platform == 'android':
            self._show_info('Place music file at /sdcard/SERA/bgm.wav or bgm.mp3')
            self._load_android_music()
        else:
            self._show_desktop_music_picker()

    def _show_desktop_music_picker(self):
        from kivy.uix.filechooser import FileChooserListView
        content = BoxLayout(orientation='vertical')
        fc = FileChooserListView(filters=['*.wav', '*.mp3'])
        btn_row = BoxLayout(size_hint_y=None, height=44, spacing=8)
        ok_btn = _btn('OK', color=ACCENT)
        cancel_btn = _btn('Cancel', color=(0.4, 0.4, 0.4, 1))
        btn_row.add_widget(ok_btn)
        btn_row.add_widget(cancel_btn)
        content.add_widget(fc)
        content.add_widget(btn_row)

        popup = Popup(title='Select Music', content=content,
                      size_hint=(0.95, 0.9))

        def on_ok(_):
            paths = fc.selection
            if paths:
                self._bgm_path = paths[0]
                self._music_lbl.text = os.path.basename(paths[0])
            popup.dismiss()

        ok_btn.bind(on_release=on_ok)
        cancel_btn.bind(on_release=popup.dismiss)
        popup.open()

    def _load_android_music(self):
        for name in ['bgm.wav', 'bgm.mp3']:
            path = f'/sdcard/SERA/{name}'
            if os.path.exists(path):
                self._bgm_path = path
                self._music_lbl.text = name
                return

    def _on_overlay_text(self, instance, value):
        self.settings.director_text = value
        self._overlay_lbl.text = value

    def _on_pos_changed(self, instance, value):
        positions = ['Top Left', 'Top Center', 'Top Right',
                     'Center Left', 'Center', 'Center Right',
                     'Bottom Left', 'Bottom Center', 'Bottom Right']
        if value in positions:
            self.settings.director_text_pos = positions.index(value)

    def _on_speed_changed(self, instance, value):
        v = int(value)
        self._switch_lbl.text = str(v)
        self.settings.director_switch_time = v

    def _start_director_if_needed(self):
        if self._director_images:
            self._current_img_idx = random.randint(0, len(self._director_images) - 1)
            self._show_director_image()
            if self._director_event:
                self._director_event.cancel()
            self._director_event = Clock.schedule_interval(
                self._on_director_switch,
                self.settings.director_switch_time
            )

        if hasattr(self, '_bgm_path') and self._bgm_path:
            sound = SoundLoader.load(self._bgm_path)
            if sound:
                sound.volume = self.settings.bgm_volume
                sound.loop = True
                sound.play()
                self._bgm_sound = sound

    def _stop_director(self):
        if self._director_event:
            self._director_event.cancel()
            self._director_event = None
        if self._bgm_sound:
            self._bgm_sound.stop()
            self._bgm_sound = None

    def _on_director_switch(self, dt):
        if self._director_images:
            self._current_img_idx = random.randint(0, len(self._director_images) - 1)
            self._show_director_image()

    def _show_director_image(self):
        if self._director_images:
            path = self._director_images[self._current_img_idx]
            if os.path.exists(path):
                self._director_img.source = path
                self._director_img.reload()

    def _on_toggle_director(self, *_):
        if self._director_event or self._bgm_sound:
            self._stop_director()
            self._btn_toggle_dir.text = 'Start Live Preview'
        else:
            self._start_director_if_needed()
            self._btn_toggle_dir.text = 'Stop Live Preview'

    # ──────────────────────── SETTINGS ───────────────────────────────────────

    def open_settings(self):
        from .settings_screen import SettingsPopup
        popup = SettingsPopup(self.settings, on_save=self._on_settings_saved)
        popup.open()

    def _on_settings_saved(self):
        self.recorder = AudioRecorder(self.settings.sample_rate, self.settings.channels)

    # ──────────────────────── HELPERS ────────────────────────────────────────

    def _set_status(self, text, color):
        self._status_lbl.text = text
        self._status_lbl.color = color

    def _refresh_btn_states(self):
        rec = self.recorder.is_recording
        paused = self.recorder.is_paused
        has_audio = self._audio_result is not None

        self._btn_start.disabled = rec
        self._btn_pause.disabled = not (rec and not paused)
        self._btn_resume.disabled = not (rec and paused)
        self._btn_stop.disabled = not rec
        self._btn_play.disabled = not has_audio
        self._btn_play_pause.disabled = not has_audio
        self._btn_play_resume.disabled = not has_audio
        self._btn_settings.disabled = rec

    def _show_error(self, msg):
        popup = Popup(title='Error',
                      content=Label(text=msg, color=RED),
                      size_hint=(0.8, 0.3))
        popup.open()

    def _show_info(self, msg):
        popup = Popup(title='Info',
                      content=Label(text=msg, color=TEXT, text_size=(300, None),
                                    halign='center'),
                      size_hint=(0.85, 0.35))
        popup.open()
