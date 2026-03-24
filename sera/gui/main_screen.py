import os
import random
import datetime
import tempfile

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
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
from kivy.graphics import Color, Rectangle
from kivy.core.audio import SoundLoader

from ..config.settings import AppSettings
from ..audio.recorder import AudioRecorder
from ..audio.processor import AudioProcessor


# ─── Colors ───────────────────────────────────────────────────────────────────
BG      = (0.12, 0.12, 0.14, 1)
SURFACE = (0.17, 0.17, 0.20, 1)
ACCENT  = (0.30, 0.80, 0.64, 1)
RED     = (0.91, 0.30, 0.24, 1)
ORANGE  = (0.95, 0.61, 0.07, 1)
TEXT    = (1, 1, 1, 1)
SUBTEXT = (0.58, 0.65, 0.65, 1)


def _btn(text, color=ACCENT, **kw):
    return Button(
        text=text,
        background_normal='',
        background_color=color,
        color=TEXT,
        bold=True,
        size_hint_y=None,
        height=48,
        **kw
    )


class SeraMainScreen(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation='vertical', **kw)
        try:
            self.settings = AppSettings()
        except Exception:
            self.settings = None

        try:
            sr = self.settings.sample_rate if self.settings else 44100
            ch = self.settings.channels if self.settings else 1
            self.recorder = AudioRecorder(sr, ch)
        except Exception:
            self.recorder = None

        self._start_time = None
        self._last_rms = 0.0
        self._timer_event = None
        self._audio_result = None
        self._director_images = []
        self._current_img_idx = 0
        self._director_event = None
        self._bgm_sound = None
        self._bgm_path = None
        self._current_play_sound = None

        try:
            self._build_ui()
        except Exception as e:
            self.clear_widgets()
            err = Label(text=f'خطأ في الواجهة:\n{e}', color=RED,
                        font_size=14, halign='center')
            self.add_widget(err)
            return

        self._refresh_btn_states()

    # ──────────────────────────────── UI BUILD ────────────────────────────────

    def _build_ui(self):
        with self.canvas.before:
            Color(*BG)
            self._bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        self.add_widget(self._build_header())

        self._tabs = TabbedPanel(
            do_default_tab=False,
            tab_width=150,
            tab_height=44,
        )

        rec_tab = TabbedPanelItem(text='RECORDER')
        rec_tab.add_widget(self._build_recorder_tab())

        dir_tab = TabbedPanelItem(text='DIRECTOR')
        dir_tab.add_widget(self._build_director_tab())

        self._tabs.add_widget(rec_tab)
        self._tabs.add_widget(dir_tab)

        # Switch to recorder tab after layout
        Clock.schedule_once(lambda dt: self._switch_to_tab(rec_tab), 0.1)

        self.add_widget(self._tabs)

    def _switch_to_tab(self, tab):
        try:
            self._tabs.switch_to(tab)
        except Exception:
            pass

    def _update_bg(self, *_):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size

    def _build_header(self):
        box = BoxLayout(size_hint_y=None, height=52, padding=[16, 8])
        with box.canvas.before:
            Color(*SURFACE)
            rect = Rectangle(pos=box.pos, size=box.size)
        box.bind(pos=lambda *_: setattr(rect, 'pos', box.pos),
                 size=lambda *_: setattr(rect, 'size', box.size))
        lbl = Label(text='SERA Voice Twin', color=ACCENT,
                    font_size=20, bold=True, halign='left')
        lbl.bind(size=lambda *_: setattr(lbl, 'text_size', lbl.size))
        box.add_widget(lbl)
        return box

    # ─────────────────────────── RECORDER TAB ────────────────────────────────

    def _build_recorder_tab(self):
        root = ScrollView()
        layout = BoxLayout(orientation='vertical', padding=16, spacing=10,
                           size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))

        self._status_lbl = Label(text='جاهز للتسجيل', color=SUBTEXT,
                                 font_size=13, size_hint_y=None, height=28)
        layout.add_widget(self._status_lbl)

        self._timer_lbl = Label(text='00:00:00', color=TEXT,
                                font_size=40, bold=True,
                                size_hint_y=None, height=58)
        layout.add_widget(self._timer_lbl)

        meter_row = GridLayout(cols=5, spacing=4, size_hint_y=None, height=16)
        self._meters = []
        for _ in range(5):
            pb = ProgressBar(max=100, value=0)
            self._meters.append(pb)
            meter_row.add_widget(pb)
        layout.add_widget(meter_row)

        self._level_lbl = Label(text='المستوى: 0%', color=SUBTEXT,
                                font_size=12, size_hint_y=None, height=24)
        layout.add_widget(self._level_lbl)

        # Recording buttons 2x2
        rec_grid = GridLayout(cols=2, spacing=8, size_hint_y=None, height=112)
        self._btn_start  = _btn('تسجيل',      color=RED)
        self._btn_pause  = _btn('إيقاف مؤقت', color=ORANGE)
        self._btn_resume = _btn('استئناف',     color=ACCENT)
        self._btn_stop   = _btn('حفظ/إيقاف',  color=(0.4, 0.4, 0.4, 1))
        for b in [self._btn_start, self._btn_pause,
                  self._btn_resume, self._btn_stop]:
            rec_grid.add_widget(b)
        self._btn_start.bind(on_release=lambda _: self.start_recording())
        self._btn_pause.bind(on_release=lambda _: self.pause_recording())
        self._btn_resume.bind(on_release=lambda _: self.resume_recording())
        self._btn_stop.bind(on_release=lambda _: self.stop_and_save())
        layout.add_widget(rec_grid)

        layout.add_widget(Label(text='معاينة التشغيل', color=SUBTEXT,
                                font_size=12, size_hint_y=None, height=22))

        play_grid = GridLayout(cols=3, spacing=8, size_hint_y=None, height=52)
        self._btn_play        = _btn('تشغيل',          color=ACCENT)
        self._btn_play_pause  = _btn('إيقاف',          color=ORANGE)
        self._btn_play_resume = _btn('استئناف التشغيل', color=ACCENT)
        for b in [self._btn_play, self._btn_play_pause, self._btn_play_resume]:
            play_grid.add_widget(b)
        self._btn_play.bind(on_release=lambda _: self.start_play())
        self._btn_play_pause.bind(on_release=lambda _: self.pause_play())
        self._btn_play_resume.bind(on_release=lambda _: self.resume_play())
        layout.add_widget(play_grid)

        self._btn_settings = _btn('الإعدادات', color=SURFACE)
        self._btn_settings.color = ACCENT
        self._btn_settings.bind(on_release=lambda _: self.open_settings())
        layout.add_widget(self._btn_settings)

        root.add_widget(layout)
        return root

    # ─────────────────────────── DIRECTOR TAB ────────────────────────────────

    def _build_director_tab(self):
        root = ScrollView()
        layout = BoxLayout(orientation='vertical', padding=16, spacing=10,
                           size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))

        img_box = BoxLayout(size_hint_y=None, height=200)
        with img_box.canvas.before:
            Color(0, 0, 0, 1)
            r = Rectangle(pos=img_box.pos, size=img_box.size)
        img_box.bind(pos=lambda *_: setattr(r, 'pos', img_box.pos),
                     size=lambda *_: setattr(r, 'size', img_box.size))
        self._director_img = KivyImage(allow_stretch=True, keep_ratio=True)
        img_box.add_widget(self._director_img)
        layout.add_widget(img_box)

        self._overlay_lbl = Label(text='', color=TEXT, font_size=15, bold=True,
                                  size_hint_y=None, height=26)
        layout.add_widget(self._overlay_lbl)

        self._btn_imgs = _btn('اختر صوراً...', color=SURFACE)
        self._btn_imgs.color = ACCENT
        self._img_count_lbl = Label(text='لا توجد صور.', color=SUBTEXT,
                                    font_size=12, size_hint_y=None, height=22)
        self._btn_imgs.bind(on_release=self._on_select_images)
        layout.add_widget(self._btn_imgs)
        layout.add_widget(self._img_count_lbl)

        self._btn_bgm = _btn('اختر موسيقى خلفية...', color=SURFACE)
        self._btn_bgm.color = ACCENT
        self._music_lbl = Label(text='لا توجد موسيقى.', color=SUBTEXT,
                                font_size=12, size_hint_y=None, height=22)
        self._btn_bgm.bind(on_release=self._on_select_music)
        layout.add_widget(self._btn_bgm)
        layout.add_widget(self._music_lbl)

        txt_row = BoxLayout(size_hint_y=None, height=42, spacing=8)
        txt_row.add_widget(Label(text='نص:', color=TEXT,
                                 font_size=13, size_hint_x=None, width=60))
        self._overlay_input = TextInput(multiline=False,
                                        hint_text='نص على الشاشة...')
        self._overlay_input.bind(text=self._on_overlay_text)
        txt_row.add_widget(self._overlay_input)
        layout.add_widget(txt_row)

        spd_row = BoxLayout(size_hint_y=None, height=42, spacing=8)
        spd_row.add_widget(Label(text='سرعة التبديل (ث):', color=TEXT,
                                 font_size=12, size_hint_x=None, width=130))
        sw_val = self.settings.director_switch_time if self.settings else 5
        self._switch_slider = Slider(min=1, max=60, value=sw_val, step=1)
        self._switch_lbl = Label(text=str(sw_val), color=ACCENT,
                                 font_size=13, size_hint_x=None, width=30)
        self._switch_slider.bind(value=self._on_speed_changed)
        spd_row.add_widget(self._switch_slider)
        spd_row.add_widget(self._switch_lbl)
        layout.add_widget(spd_row)

        self._btn_toggle_dir = _btn('تشغيل المعاينة', color=ACCENT)
        self._btn_toggle_dir.bind(on_release=self._on_toggle_director)
        layout.add_widget(self._btn_toggle_dir)

        root.add_widget(layout)
        return root

    # ─────────────────────────── RECORDING LOGIC ─────────────────────────────

    def start_recording(self):
        if not self.recorder or self.recorder.is_recording:
            return
        self._audio_result = None
        try:
            sr = self.settings.sample_rate if self.settings else 44100
            ch = self.settings.channels if self.settings else 1
            self.recorder = AudioRecorder(sr, ch)
            self.recorder.start(self._audio_callback)
            self._start_time = datetime.datetime.now()
            if self._timer_event:
                self._timer_event.cancel()
            self._timer_event = Clock.schedule_interval(self._on_timer, 0.1)
            self._set_status('● تسجيل جارٍ', RED)
            self._start_director_if_needed()
            self._refresh_btn_states()
        except Exception as e:
            self._show_error(f'خطأ في بدء التسجيل:\n{e}')

    def _audio_callback(self, indata, frames, time, status):
        try:
            import numpy as np
            if len(indata) > 0:
                rms = float(np.sqrt(np.mean(indata.astype(np.float32) ** 2)))
                self._last_rms = rms
        except Exception:
            pass

    def pause_recording(self):
        if self.recorder:
            self.recorder.pause()
        self._set_status('⏸ متوقف مؤقتاً', ORANGE)
        self._refresh_btn_states()

    def resume_recording(self):
        if self.recorder:
            self.recorder.resume()
        self._set_status('● تسجيل جارٍ', RED)
        self._refresh_btn_states()

    def stop_and_save(self):
        if self._timer_event:
            self._timer_event.cancel()
            self._timer_event = None
        self._stop_director()
        try:
            result = self.recorder.stop() if self.recorder else None
            self._audio_result = result
            if result is None:
                self._set_status('لا يوجد تسجيل', SUBTEXT)
            else:
                save_path = self.settings.recordings_dir if self.settings else '/sdcard/SERA'
                filename = AudioProcessor.save_recording(
                    result,
                    self.settings.sample_rate if self.settings else 44100,
                    save_path,
                    remove_silence=self.settings.remove_silence if self.settings else False,
                    silence_threshold=self.settings.silence_threshold if self.settings else -40,
                    adaptive_silence=self.settings.adaptive_silence if self.settings else True
                )
                if filename:
                    self._set_status(f'✅ تم الحفظ: {filename}', ACCENT)
                else:
                    self._set_status('لا يوجد تسجيل', SUBTEXT)
        except Exception as e:
            self._set_status(f'خطأ في الحفظ: {e}', RED)
        self._timer_lbl.text = '00:00:00'
        self._refresh_btn_states()

    def _on_timer(self, dt):
        try:
            if self.recorder and self.recorder.is_recording and not self.recorder.is_paused:
                if self._start_time:
                    delta = datetime.datetime.now() - self._start_time
                    self._timer_lbl.text = str(delta).split('.')[0]
            rms = self._last_rms
            percent = min(100, int((rms / 8000) * 100))
            self._level_lbl.text = f'المستوى: {percent}%'
            for m in self._meters:
                v = min(100, max(0, percent + random.randint(-10, 10)))
                m.value = v
        except Exception:
            pass

    # ─────────────────────────── PLAYBACK ────────────────────────────────────

    def start_play(self):
        if self._audio_result is None:
            return
        try:
            kind, data = self._audio_result
            path = None
            if kind == 'frames' and data:
                import numpy as np
                audio = np.concatenate(data, axis=0)
                fd, path = tempfile.mkstemp(suffix='.wav')
                os.close(fd)
                sr = self.settings.sample_rate if self.settings else 44100
                AudioProcessor.write_wav(path, sr, audio)
            elif kind == 'file' and data:
                path = data
            if path:
                self._play_file(path)
        except Exception as e:
            self._show_error(f'خطأ في التشغيل:\n{e}')

    def _play_file(self, path):
        try:
            if self._current_play_sound:
                self._current_play_sound.stop()
            sound = SoundLoader.load(path)
            if sound:
                vol = self.settings.rec_volume if self.settings else 1.0
                sound.volume = vol
                sound.play()
                self._current_play_sound = sound
        except Exception as e:
            self._show_error(f'خطأ: {e}')

    def pause_play(self):
        try:
            if self._current_play_sound:
                self._current_play_sound.stop()
        except Exception:
            pass

    def resume_play(self):
        try:
            if self._current_play_sound:
                self._current_play_sound.play()
        except Exception:
            pass

    # ─────────────────────────── DIRECTOR ────────────────────────────────────

    def _on_select_images(self, *_):
        if platform == 'android':
            self._load_android_images()
            self._show_info('ضع الصور في المجلد:\n/sdcard/SERA/images/')
        else:
            self._show_desktop_image_picker()

    def _show_desktop_image_picker(self):
        try:
            from kivy.uix.filechooser import FileChooserListView
            content = BoxLayout(orientation='vertical')
            fc = FileChooserListView(filters=['*.jpg', '*.jpeg', '*.png'],
                                     multiselect=True)
            btn_row = BoxLayout(size_hint_y=None, height=44, spacing=8)
            ok_btn = _btn('موافق', color=ACCENT)
            cancel_btn = _btn('إلغاء', color=(0.4, 0.4, 0.4, 1))
            btn_row.add_widget(ok_btn)
            btn_row.add_widget(cancel_btn)
            content.add_widget(fc)
            content.add_widget(btn_row)
            popup = Popup(title='اختر صوراً', content=content,
                          size_hint=(0.95, 0.9))

            def on_ok(_):
                if fc.selection:
                    self._director_images = list(fc.selection)
                    self._img_count_lbl.text = f'{len(fc.selection)} صورة محملة.'
                popup.dismiss()

            ok_btn.bind(on_release=on_ok)
            cancel_btn.bind(on_release=popup.dismiss)
            popup.open()
        except Exception as e:
            self._show_error(str(e))

    def _load_android_images(self):
        import glob
        found = []
        for ext in ['*.jpg', '*.jpeg', '*.png']:
            found.extend(glob.glob(f'/sdcard/SERA/images/{ext}'))
        if found:
            self._director_images = found
            self._img_count_lbl.text = f'{len(found)} صورة محملة.'
        else:
            self._img_count_lbl.text = 'لا توجد صور في /sdcard/SERA/images/'

    def _on_select_music(self, *_):
        if platform == 'android':
            self._load_android_music()
            self._show_info('ضع الموسيقى في:\n/sdcard/SERA/bgm.mp3')
        else:
            self._show_desktop_music_picker()

    def _show_desktop_music_picker(self):
        try:
            from kivy.uix.filechooser import FileChooserListView
            content = BoxLayout(orientation='vertical')
            fc = FileChooserListView(filters=['*.wav', '*.mp3'])
            btn_row = BoxLayout(size_hint_y=None, height=44, spacing=8)
            ok_btn = _btn('موافق', color=ACCENT)
            cancel_btn = _btn('إلغاء', color=(0.4, 0.4, 0.4, 1))
            btn_row.add_widget(ok_btn)
            btn_row.add_widget(cancel_btn)
            content.add_widget(fc)
            content.add_widget(btn_row)
            popup = Popup(title='اختر موسيقى', content=content,
                          size_hint=(0.95, 0.9))

            def on_ok(_):
                if fc.selection:
                    self._bgm_path = fc.selection[0]
                    self._music_lbl.text = os.path.basename(fc.selection[0])
                popup.dismiss()

            ok_btn.bind(on_release=on_ok)
            cancel_btn.bind(on_release=popup.dismiss)
            popup.open()
        except Exception as e:
            self._show_error(str(e))

    def _load_android_music(self):
        for name in ['bgm.mp3', 'bgm.wav']:
            path = f'/sdcard/SERA/{name}'
            if os.path.exists(path):
                self._bgm_path = path
                self._music_lbl.text = name
                return

    def _on_overlay_text(self, instance, value):
        self._overlay_lbl.text = value
        if self.settings:
            self.settings.director_text = value

    def _on_speed_changed(self, instance, value):
        v = int(value)
        self._switch_lbl.text = str(v)
        if self.settings:
            self.settings.director_switch_time = v

    def _start_director_if_needed(self):
        if self._director_images:
            self._current_img_idx = random.randint(0, len(self._director_images) - 1)
            self._show_director_image()
            if self._director_event:
                self._director_event.cancel()
            sw = self.settings.director_switch_time if self.settings else 5
            self._director_event = Clock.schedule_interval(
                self._on_director_switch, sw)
        if self._bgm_path:
            try:
                sound = SoundLoader.load(self._bgm_path)
                if sound:
                    vol = self.settings.bgm_volume if self.settings else 0.5
                    sound.volume = vol
                    sound.loop = True
                    sound.play()
                    self._bgm_sound = sound
            except Exception:
                pass

    def _stop_director(self):
        if self._director_event:
            self._director_event.cancel()
            self._director_event = None
        if self._bgm_sound:
            try:
                self._bgm_sound.stop()
            except Exception:
                pass
            self._bgm_sound = None

    def _on_director_switch(self, dt):
        if self._director_images:
            self._current_img_idx = random.randint(0, len(self._director_images) - 1)
            self._show_director_image()

    def _show_director_image(self):
        if self._director_images:
            path = self._director_images[self._current_img_idx]
            if os.path.exists(path):
                try:
                    self._director_img.source = path
                    self._director_img.reload()
                except Exception:
                    pass

    def _on_toggle_director(self, *_):
        if self._director_event or self._bgm_sound:
            self._stop_director()
            self._btn_toggle_dir.text = 'تشغيل المعاينة'
        else:
            self._start_director_if_needed()
            self._btn_toggle_dir.text = 'إيقاف المعاينة'

    # ─────────────────────────── SETTINGS ────────────────────────────────────

    def open_settings(self):
        try:
            from .settings_screen import SettingsPopup
            popup = SettingsPopup(self.settings, on_save=self._on_settings_saved)
            popup.open()
        except Exception as e:
            self._show_error(str(e))

    def _on_settings_saved(self):
        try:
            sr = self.settings.sample_rate if self.settings else 44100
            ch = self.settings.channels if self.settings else 1
            self.recorder = AudioRecorder(sr, ch)
        except Exception:
            pass

    # ─────────────────────────── HELPERS ─────────────────────────────────────

    def _set_status(self, text, color):
        try:
            self._status_lbl.text = text
            self._status_lbl.color = color
        except Exception:
            pass

    def _refresh_btn_states(self):
        try:
            rec = self.recorder.is_recording if self.recorder else False
            paused = self.recorder.is_paused if self.recorder else False
            has_audio = self._audio_result is not None
            self._btn_start.disabled = rec
            self._btn_pause.disabled = not (rec and not paused)
            self._btn_resume.disabled = not (rec and paused)
            self._btn_stop.disabled = not rec
            self._btn_play.disabled = not has_audio
            self._btn_play_pause.disabled = not has_audio
            self._btn_play_resume.disabled = not has_audio
            self._btn_settings.disabled = rec
        except Exception:
            pass

    def _show_error(self, msg):
        try:
            popup = Popup(title='خطأ',
                          content=Label(text=str(msg), color=RED,
                                        text_size=(280, None), halign='center'),
                          size_hint=(0.85, 0.35))
            popup.open()
        except Exception:
            pass

    def _show_info(self, msg):
        try:
            popup = Popup(title='معلومة',
                          content=Label(text=msg, color=TEXT,
                                        text_size=(280, None), halign='center'),
                          size_hint=(0.85, 0.35))
            popup.open()
        except Exception:
            pass
