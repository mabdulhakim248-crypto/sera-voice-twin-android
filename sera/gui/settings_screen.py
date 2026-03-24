from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.slider import Slider
from kivy.uix.switch import Switch
from kivy.uix.spinner import Spinner
from kivy.graphics import Color, Rectangle

BG      = (0.12, 0.12, 0.14, 1)
SURFACE = (0.17, 0.17, 0.20, 1)
ACCENT  = (0.30, 0.80, 0.64, 1)
TEXT    = (1, 1, 1, 1)
SUBTEXT = (0.58, 0.65, 0.65, 1)
RED     = (0.91, 0.30, 0.24, 1)


def _lbl(text, color=TEXT, size=13):
    return Label(text=text, color=color, font_size=size,
                 size_hint_y=None, height=28, halign='left')


def _btn(text, color=ACCENT):
    b = Button(text=text, background_normal='', background_color=color,
               color=TEXT, bold=True, size_hint_y=None, height=44)
    return b


class SettingsPopup(Popup):
    def __init__(self, settings, on_save=None, **kw):
        self.app_settings = settings
        self._on_save = on_save

        content = self._build_content()
        super().__init__(
            title='SERA Settings',
            content=content,
            size_hint=(0.95, 0.92),
            background_color=BG,
            **kw
        )

    def _build_content(self):
        root = ScrollView()
        layout = BoxLayout(orientation='vertical', padding=12, spacing=10,
                           size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))

        s = self.app_settings

        # Sample Rate
        layout.add_widget(_lbl('Sample Rate (Hz):', color=SUBTEXT))
        self._sr_spinner = Spinner(
            text=str(s.sample_rate),
            values=['44100', '48000', '22050', '16000'],
            size_hint_y=None, height=40
        )
        layout.add_widget(self._sr_spinner)

        # Channels
        layout.add_widget(_lbl('Channels:', color=SUBTEXT))
        self._ch_spinner = Spinner(
            text='Stereo' if s.channels == 2 else 'Mono',
            values=['Mono', 'Stereo'],
            size_hint_y=None, height=40
        )
        layout.add_widget(self._ch_spinner)

        # Silence Removal
        sil_row = BoxLayout(size_hint_y=None, height=40, spacing=8)
        sil_row.add_widget(_lbl('Silence Removal:', color=SUBTEXT))
        self._silence_sw = Switch(active=s.remove_silence,
                                  size_hint_x=None, width=80)
        sil_row.add_widget(self._silence_sw)
        layout.add_widget(sil_row)

        # Adaptive
        ada_row = BoxLayout(size_hint_y=None, height=40, spacing=8)
        ada_row.add_widget(_lbl('Adaptive Threshold:', color=SUBTEXT))
        self._adaptive_sw = Switch(active=s.adaptive_silence,
                                   size_hint_x=None, width=80)
        ada_row.add_widget(self._adaptive_sw)
        layout.add_widget(ada_row)

        # Silence threshold slider
        self._thresh_lbl = _lbl(f'Silence Threshold: {int(s.silence_threshold)} dB',
                                color=SUBTEXT)
        layout.add_widget(self._thresh_lbl)
        self._thresh_slider = Slider(min=-80, max=-10,
                                     value=s.silence_threshold, step=1)
        self._thresh_slider.bind(value=self._on_thresh)
        layout.add_widget(self._thresh_slider)

        # BGM Volume
        self._bgm_lbl = _lbl(f'BGM Volume: {int(s.bgm_volume * 100)}%',
                             color=SUBTEXT)
        layout.add_widget(self._bgm_lbl)
        self._bgm_slider = Slider(min=0, max=100,
                                  value=s.bgm_volume * 100, step=1)
        self._bgm_slider.bind(value=self._on_bgm_vol)
        layout.add_widget(self._bgm_slider)

        # Recording Volume
        self._rec_lbl = _lbl(f'Playback Volume: {int(s.rec_volume * 100)}%',
                             color=SUBTEXT)
        layout.add_widget(self._rec_lbl)
        self._rec_slider = Slider(min=0, max=100,
                                  value=s.rec_volume * 100, step=1)
        self._rec_slider.bind(value=self._on_rec_vol)
        layout.add_widget(self._rec_slider)

        # Buttons
        btn_row = BoxLayout(size_hint_y=None, height=48, spacing=8)
        ok_btn = _btn('Save', color=ACCENT)
        cancel_btn = _btn('Cancel', color=(0.35, 0.35, 0.35, 1))
        ok_btn.bind(on_release=self._on_ok)
        cancel_btn.bind(on_release=self.dismiss)
        btn_row.add_widget(ok_btn)
        btn_row.add_widget(cancel_btn)
        layout.add_widget(btn_row)

        root.add_widget(layout)
        return root

    def _on_thresh(self, instance, value):
        self._thresh_lbl.text = f'Silence Threshold: {int(value)} dB'

    def _on_bgm_vol(self, instance, value):
        self._bgm_lbl.text = f'BGM Volume: {int(value)}%'

    def _on_rec_vol(self, instance, value):
        self._rec_lbl.text = f'Playback Volume: {int(value)}%'

    def _on_ok(self, *_):
        s = self.app_settings
        s.sample_rate = int(self._sr_spinner.text)
        s.channels = 2 if self._ch_spinner.text == 'Stereo' else 1
        s.remove_silence = self._silence_sw.active
        s.adaptive_silence = self._adaptive_sw.active
        s.silence_threshold = float(self._thresh_slider.value)
        s.bgm_volume = self._bgm_slider.value / 100.0
        s.rec_volume = self._rec_slider.value / 100.0
        s.save()
        if self._on_save:
            self._on_save()
        self.dismiss()
