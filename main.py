import os
os.environ.setdefault('KIVY_NO_CONSOLELOG', '0')

from kivy.app import App
from kivy.core.window import Window
from kivy.utils import platform

if platform != 'android':
    Window.size = (400, 700)

# Request Android permissions before anything else
if platform == 'android':
    try:
        from android.permissions import request_permissions, Permission
        request_permissions([
            Permission.RECORD_AUDIO,
            Permission.READ_EXTERNAL_STORAGE,
            Permission.WRITE_EXTERNAL_STORAGE,
        ])
    except Exception:
        pass

from sera.gui.main_screen import SeraMainScreen


class SeraApp(App):
    def build(self):
        self.title = 'SERA Voice Twin'
        try:
            return SeraMainScreen()
        except Exception as e:
            from kivy.uix.label import Label
            return Label(
                text=f'خطأ في التشغيل:\n{e}',
                color=(1, 0.3, 0.3, 1),
                font_size=16,
                halign='center'
            )


if __name__ == '__main__':
    SeraApp().run()
