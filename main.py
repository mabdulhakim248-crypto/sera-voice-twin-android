import os
os.environ.setdefault('KIVY_NO_CONSOLELOG', '0')

from kivy.app import App
from kivy.core.window import Window
from kivy.utils import platform

if platform != 'android':
    Window.size = (400, 700)

from sera.gui.main_screen import SeraMainScreen


class SeraApp(App):
    def build(self):
        self.title = 'SERA Voice Twin'
        return SeraMainScreen()


if __name__ == '__main__':
    SeraApp().run()
