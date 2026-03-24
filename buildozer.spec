[app]
title = SERA Voice Twin
package.name = seravoicetwin
package.domain = org.sera

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,wav,mp3
source.include_patterns = assets/*,images/*

version = 1.0.0

requirements = python3,kivy==2.3.0,numpy,plyer

orientation = portrait

fullscreen = 0

android.permissions = RECORD_AUDIO,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,INTERNET
android.api = 33
android.minapi = 21
android.ndk = 25b
android.ndk_api = 21
android.private_storage = True
android.accept_sdk_license = True
android.archs = arm64-v8a

android.enable_androidx = True

[buildozer]
log_level = 2
warn_on_root = 1
