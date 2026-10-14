# Game-developer
# ⚡ Zihad 3D Game Studio

> **Mobile-first 3D Game Development Studio** — Build, preview, and package Babylon.js & Three.js games into real Android APKs — all from your phone using Termux.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0%2B-green)](https://flask.palletsprojects.com)
[![Android](https://img.shields.io/badge/Android-SDK%2035-brightgreen)](https://developer.android.com)
[![Gradle](https://img.shields.io/badge/Gradle-8.10%2B-orange)](https://gradle.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📖 সূচিপত্র (Table of Contents)

- [এটা কী?](#এটা-কী)
- [ফিচার সমূহ](#-ফিচার-সমূহ)
- [স্ক্রিনশট](#-স্ক্রিনশট)
- [প্রয়োজনীয়তা](#-প্রয়োজনীয়তা)
- [ইনস্টলেশন (Termux এ)](#-ইনস্টলেশন-termux-এ)
- [ব্যবহার বিধি](#-ব্যবহার-বিধি)
- [প্রজেক্ট স্ট্রাকচার](#-প্রজেক্ট-স্ট্রাকচার)
- [Keyboard Shortcuts](#-keyboard-shortcuts)
- [Game Templates](#-game-templates)
- [Build System](#-build-system)
- [API Reference](#-api-reference)
- [Troubleshooting](#-troubleshooting)
- [GitHub এ আপলোড](#-github-এ-আপলোড)
- [Contributing](#-contributing)
- [License](#-license)

---

## এটা কী?

**Zihad 3D Game Studio** একটি সম্পূর্ণ **মোবাইল-ভিত্তিক 3D গেম ডেভেলপমেন্ট এনভায়রনমেন্ট** যা Termux এ চলে। এটি Python (Flask) সার্ভার + ব্রাউজার UI + Babylon.js/Three.js গেম ইঞ্জিন + Android SDK/Gradle বিল্ড সিস্টেমকে একসাথে যুক্ত করে।

**এক লাইনে:** ব্রাউজারে গেম বানাও → APK বিল্ড করো → ফোনে ইনস্টল করো।

### 🎯 কাদের জন্য?
- মোবাইল ডেভেলপার যাদের PC নেই
- Termux এ 3D গেম বানাতে চান
- Web-based গেম দ্রুত APK তে রূপান্তর করতে চান
- Babylon.js / Three.js শিখতে চান

---

## ✨ ফিচার সমূহ

### 🎮 গেম ইঞ্জিন
- 🔵 **Babylon.js** — Microsoft এর powerful 3D engine
- 🟢 **Three.js** — WebGL এর সবচেয়ে জনপ্রিয় library
- **Multi-engine project** — একই প্রজেক্টে দুটোই রাখা যায়

### 📝 কোড এডিটর
- **CodeMirror** with syntax highlighting
- **Multi-file tabs** — একসাথে অনেক ফাইল ওপেন
- **Auto-save** (৩ সেকেন্ড debounce)
- **Live reload** — save করলে preview auto refresh
- **Full toolbar** — Save, Reload, Undo, Redo, Copy, Paste, Cut, Clear, Find, Replace, Format, Font±, Go-to-Line

### 📂 ফাইল ম্যানেজার
- **Breadcrumb navigation**
- **Search in project** (grep-like, line numbers)
- **7 ধরনের sort** (name, size, date, type)
- **Rename / Delete** per item
- **File size + date** display
- **ZIP export / import**
- **Multi-file upload** to current folder
- **URL download** (any file from internet)
- **Asset preview** (image thumbnail)

### ⚙️ Build System
- **App Settings Panel** — name, package, version, orientation
- **Custom App Icon** (PNG/JPG upload)
- **Real-time progress bar**
- **Live build log**
- **Confetti animation** on success 🎉
- **APK install** (termux-open)
- **APK download** (browser)

### 🎨 Starter Templates
- 🏃 **Platformer** — jump, gravity, coins
- 🎯 **FPS Shooter** — pointer lock, WASD
- 🏃‍♂️ **Endless Runner** — auto-scroll, obstacles
- 🧊 **GLB Viewer** — orbit camera, lighting

### ⌨️ Productivity
- **Command Palette** (Ctrl+K) — সব action এক জায়গায়
- **Keyboard shortcuts**
- **Recent projects** (localStorage)
- **Dark / Light theme** toggle
- **PWA support** — home screen এ install

### 🔒 Security
- **Path traversal protection**
- **Binary file protection**
- **Safe project isolation**
- **Max file size limits**

---

## 📸 স্ক্রিনশট

> _UI টা mobile-first premium dark theme, glass morphism, gradient buttons সহ।_

| Home | Workspace | Editor |
|---|---|---|
| প্রজেক্ট গ্রিড | ফাইল ব্রাউজার | CodeMirror |

---

## 🔧 প্রয়োজনীয়তা

| সফটওয়্যার | Minimum | Recommended |
|---|---|---|
| **Termux** | F-Droid version | F-Droid latest |
| **Python** | 3.10 | 3.12+ |
| **OpenJDK** | 17 | **21** |
| **Android SDK** | Platform 33 | **Platform 35** |
| **Gradle** | 8.7 | **8.10.2** |
| **Flask** | 3.0 | 3.1+ |
| **Android Version** | 6.0 (API 23) | 13+ |

> ⚠️ **Play Store এর Termux কাজ করবে না।** শুধুমাত্র **F-Droid** থেকে ইনস্টল করা Termux ব্যবহার করো।

---

## 🚀 ইনস্টলেশন (Termux এ)

### ধাপ ১: Termux বেসিক সেটআপ

```bash
pkg update && pkg upgrade -y
pkg install -y python nodejs git nano wget unzip zip termux-tools
termux-setup-storage
```

পারমিশন ডায়ালগে **Allow** চাপো।

### ধাপ ২: Java ইনস্টল

```bash
pkg install -y openjdk-21
java -version
```

### ধাপ ৩: Android SDK ইনস্টল

```bash
mkdir -p $HOME/android-sdk && cd $HOME/android-sdk
wget https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip -O cmdline-tools.zip
unzip cmdline-tools.zip
mkdir -p cmdline-tools/latest
mv cmdline-tools/* cmdline-tools/latest/ 2>/dev/null
```

### ধাপ ৪: Environment Variables

```bash
nano ~/.bashrc
```

শেষে যোগ করো:

```bash
export ANDROID_HOME=$HOME/android-sdk
export ANDROID_SDK_ROOT=$ANDROID_HOME
export PATH=$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$PATH
```

সেভ করে:

```bash
source ~/.bashrc
```

### ধাপ ৫: SDK Platform ইনস্টল

```bash
yes | sdkmanager --licenses
yes | sdkmanager "platform-tools" "platforms;android-35" "build-tools;35.0.0"
```

### ধাপ ৬: Gradle ইনস্টল

```bash
wget -O $ANDROID_HOME/gradle-8.10.2-bin.zip https://services.gradle.org/distributions/gradle-8.10.2-bin.zip
unzip $ANDROID_HOME/gradle-8.10.2-bin.zip -d $ANDROID_HOME/
mv $ANDROID_HOME/gradle-8.10.2/ $ANDROID_HOME/gradle/
rm $ANDROID_HOME/gradle-8.10.2-bin.zip
echo 'export PATH=$PATH:$ANDROID_HOME/gradle/bin' >> ~/.bashrc
source ~/.bashrc
gradle --version
```

### ধাপ ৭: AAPT2 Override (গুরুত্বপূর্ণ!)

ARM device এ Gradle এর default x86_64 aapt2 কাজ করে না।

```bash
pkg install -y aapt2
mkdir -p ~/.gradle
echo 'android.aapt2FromMavenOverride=/data/data/com.termux/files/usr/bin/aapt2' >> ~/.gradle/gradle.properties
```

### ধাপ ৮: Flask ইনস্টল

```bash
pip install flask
```

### ধাপ ৯: প্রজেক্ট ক্লোন

```bash
cd ~
git clone https://github.com/zihadza/Game-developer.git Zihad3DGameStudio
cd Zihad3DGameStudio
```

### ধাপ ১০: ফোল্ডার তৈরি

```bash
mkdir -p /storage/emulated/0/GodotProjects/Games/ZihadGameStudio/Projects
mkdir -p /storage/emulated/0/GodotProjects/Games/ZihadGameStudio/APK-Output
mkdir -p ~/.zihad3d-build
```

### ধাপ ১১: সার্ভার চালাও

```bash
python server.py
```

টার্মিনালে দেখবে:

```
⚡ Zihad 3D Game Studio v3 — http://127.0.0.1:3030
   Projects: /storage/emulated/0/GodotProjects/Games/ZihadGameStudio/Projects
   APK out:  /storage/emulated/0/GodotProjects/Games/ZihadGameStudio/APK-Output
```

ব্রাউজার খুলে যাও: **http://127.0.0.1:3030**

---

## 🎯 ব্যবহার বিধি

### ১. নতুন প্রজেক্ট তৈরি

1. Home এ **Project name** দাও (যেমন `MyGame`)
2. **Engine** সিলেক্ট করো:
   - 🔵 Babylon.js
   - 🟢 Three.js
   - ✅ দুটোই (multi-engine)
3. **🚀 Create** চাপো

### ২. ফাইল এডিট করা

1. বাম sidebar এ ফাইল লিস্ট থেকে ক্লিক করো
2. ডান দিকের **Editor** tab এ কোড আসবে
3. এডিট করো → **Ctrl+S** (auto-save ও আছে)

### ৩. Preview দেখা

1. **👁 Preview** tab ক্লিক করো
2. Live preview চলবে
3. **Live reload** চেক করলে save করলেই auto refresh

### ৪. APK বিল্ড করা

1. **🔨 Build** tab
2. **Build Now** চাপো
3. Progress bar দেখবে
4. সফল হলে 🎉 confetti + home এ ফিরে **📦 APK Packages** এ
5. **Install** → Android installer খুলবে
6. **⬇** → ব্রাউজার দিয়ে download

### ৫. Project Settings

1. Workspace এ **⚙️** আইকনে ক্লিক
2. App name, package, version, orientation দাও
3. Icon (512×512 PNG) upload করো
4. Save

---

## 📁 প্রজেক্ট স্ট্রাকচার

```
/storage/emulated/0/GodotProjects/Games/ZihadGameStudio/
│
├── Projects/                        # তোমার সব গেম
│   ├── MyGame/
│   │   ├── index.html               # মূল HTML (APK এ goes)
│   │   ├── game.js                  # মূল JS
│   │   ├── icon.png                 # App icon (optional)
│   │   ├── studio.json              # Project settings
│   │   ├── README.txt
│   │   ├── models/                  # GLB/GLTF models
│   │   ├── textures/                # Images
│   │   ├── audio/                   # Sound files
│   │   ├── scripts/                 # Extra JS
│   │   ├── scenes/                  # Scene files
│   │   └── engines/                 # Multi-engine variants
│   │       ├── babylon/
│   │       │   ├── index.html
│   │       │   └── game.js
│   │       └── three/
│   │           ├── index.html
│   │           └── game.js
│   └── ...
│
└── APK-Output/                      # Build হওয়া APK
    ├── MyGame-debug.apk
    └── ...

~/Zihad3DGameStudio/                 # Termux home
├── server.py                        # Flask server
├── README.md                        # এই ফাইল
├── templates/                       # (optional)
└── static/                          # (optional)

~/.zihad3d-build/                    # Build temp
└── WebGameWrapper/
    ├── settings.gradle
    ├── build.gradle
    ├── gradle.properties
    ├── local.properties
    └── app/
        ├── build.gradle
        └── src/main/
            ├── AndroidManifest.xml
            ├── java/com/zihad/game/MainActivity.java
            ├── res/mipmap-xxxhdpi/ic_launcher.png
            └── assets/game/         # তোমার গেম এখানে কপি হয়
```

---

## ⌨️ Keyboard Shortcuts

| Shortcut | কাজ |
|---|---|
| `Ctrl + K` | **Command Palette** খোলা |
| `Ctrl + S` | ফাইল সেভ |
| `Ctrl + F` | Editor এ Find |
| `Ctrl + H` | Find & Replace |
| `Ctrl + /` | Toggle comment |
| `Ctrl + Z` | Undo |
| `Ctrl + Y` | Redo |
| `Tab` | 2 spaces indent |
| `Esc` | সব dialog বন্ধ |
| `↑ ↓` | Command palette navigate |
| `Enter` | Command execute |

---

## 🎨 Game Templates

প্রজেক্ট খোলার পর **Ctrl+K** → "Apply Template" দিয়ে এই templates apply করা যায়:

### 🏃 Platformer
- 2.5D side-scroller
- Gravity + jump physics
- Platform generation
- Arrow/WASD keys

### 🎯 FPS Shooter
- First-person controller
- Pointer lock (tap to lock)
- WASD movement
- Three.js PointerLockControls

### 🏃‍♂️ Endless Runner
- Auto-scroll forward
- Random obstacle spawn
- Lane switching (left/right)
- Score counter

### 🧊 GLB Viewer
- Orbit camera
- Directional + hemispheric light
- Model loading (`models/model.glb`)
- Fallback demo cube

---

## 🔨 Build System

### Build Flow

```
Project folder (HTML + JS + GLB)
        ↓
Copy to WebGameWrapper/app/src/main/assets/game/
        ↓
Gradle → assembleDebug
        ↓
app-debug.apk → APK-Output/<project>-debug.apk
        ↓
termux-open → Android package installer
```

### Build Settings (studio.json)

```json
{
  "name": "MyGame",
  "engine": "babylon",
  "engines": ["babylon", "three"],
  "app_name": "My Awesome Game",
  "package": "com.zihad.mygame",
  "version_name": "1.0",
  "version_code": 1,
  "orientation": "landscape",
  "icon": "icon.png",
  "created": 1700000000
}
```

### Android Requirements

- **minSdk**: 23 (Android 6.0)
- **targetSdk**: 35 (Android 15)
- **compileSdk**: 35
- **Java**: 21
- **AGP**: 8.7.3

### WebView Configuration

MainActivity তে optimized WebView:

```java
s.setJavaScriptEnabled(true);
s.setDomStorageEnabled(true);
s.setDatabaseEnabled(true);
s.setAllowFileAccess(true);
s.setAllowContentAccess(true);
s.setAllowFileAccessFromFileURLs(true);
s.setAllowUniversalAccessFromFileURLs(true);
s.setMediaPlaybackRequiresUserGesture(false);
WebView.setWebContentsDebuggingEnabled(true);
```

---

## 🌐 API Reference

### Project Routes

| Method | Endpoint | কাজ |
|---|---|---|
| GET | `/` | Studio UI |
| GET | `/api/status` | Server status |
| GET | `/api/projects` | সব প্রজেক্ট |
| POST | `/api/projects` | নতুন প্রজেক্ট |
| DELETE | `/api/projects/<name>` | প্রজেক্ট ডিলিট |
| POST | `/api/projects/<name>/rename` | Rename |
| GET | `/api/projects/<name>/settings` | Settings পড়া |
| POST | `/api/projects/<name>/settings` | Settings সেভ |
| POST | `/api/projects/<name>/icon` | Icon upload |

### File Routes

| Method | Endpoint | কাজ |
|---|---|---|
| GET | `/api/tree/<project>?path=` | ফোল্ডার লিস্ট |
| GET | `/api/file/<project>?path=` | ফাইল পড়া |
| PUT | `/api/file/<project>` | ফাইল সেভ |
| DELETE | `/api/file/<project>?path=` | ফাইল ডিলিট |
| POST | `/api/mkdir/<project>` | ফোল্ডার তৈরি |
| POST | `/api/rename/<project>` | Rename |
| POST | `/api/upload/<project>` | ফাইল আপলোড |
| POST | `/api/download-url/<project>` | URL download |
| POST | `/api/export-zip/<project>` | ZIP export |
| POST | `/api/import-zip/<project>` | ZIP import |
| GET | `/api/search/<project>?q=` | Project search |

### Preview & Build

| Method | Endpoint | কাজ |
|---|---|---|
| GET | `/preview/<project>/` | Live preview |
| POST | `/api/build/<project>` | Build শুরু |
| GET | `/api/build-status` | Build status |
| GET | `/api/apks` | APK list |
| GET | `/api/download-apk/<name>` | APK download |
| POST | `/api/install-apk` | APK install |
| GET | `/api/templates` | Template list |
| POST | `/api/templates/<id>/apply/<project>` | Template apply |

---

## 🐛 Troubleshooting

### সমস্যা: `pkg: command not found`

**সমাধান:** Play Store এর Termux ইউজ করছ। **F-Droid** থেকে ইনস্টল করো।

### সমস্যা: `sdkmanager: command not found`

**সমাধান:** 
```bash
source ~/.bashrc
# অথবা terminal restart করো
```

### সমস্যা: `Address already in use`

**সমাধান:** Server auto-port নেয় (3030-3059)। অথবা:
```bash
pkill -f "python server.py"
fuser -k 3030/tcp 2>/dev/null
```

### সমস্যা: `aapt2` error during build

**সমাধান:**
```bash
pkg install aapt2
echo 'android.aapt2FromMavenOverride=/data/data/com.termux/files/usr/bin/aapt2' >> ~/.gradle/gradle.properties
```

### সমস্যা: Gradle slow first build

**কারণ:** Gradle প্রথমবার dependencies ডাউনলোড করে (~৫-১০ মিনিট)

**সমাধান:** ধৈর্য ধরো। পরের builds দ্রুত হবে (cache থেকে)।

### সমস্যা: Termux মাঝে মাঝে বন্ধ হয়

**সমাধান:** Android Settings → Battery → Termux → **Unrestricted**

### সমস্যা: `index.html not found`

**কারণ:** Godot প্রজেক্টে `index.html` থাকে না

**সমাধান:** Godot থেকে **Web Export** করে `index.html` বানাও, তারপর upload করো।

### সমস্যা: Preview খালি দেখাচ্ছে

**সমাধান:**
- Internet connection চেক করো (CDN লোড হয়)
- Browser console (F12) দেখো
- **Reload Preview** চাপো

### সমস্যা: `Could not open installer`

**সমাধান:** APK ম্যানুয়ালি ফাইল ম্যানেজার দিয়ে খুলে ইনস্টল করো। Path:
```
/storage/emulated/0/GodotProjects/Games/ZihadGameStudio/APK-Output/
```

### সমস্যা: Build fails with Java error

**সমাধান:**
```bash
pkg install openjdk-21
java -version    # 21.x.x দেখা উচিত
```

---

## 📤 GitHub এ আপলোড

### প্রথমবার

```bash
cd ~/Zihad3DGameStudio

# Git init
git init
git branch -M main

# Config (তোমার name/email দাও)
git config user.name "Zihad"
git config user.email "zihad@example.com"

# Files add
git add .
git status

# First commit
git commit -m "⚡ Initial commit — Zihad 3D Game Studio v3"

# Remote add
git remote add origin https://github.com/zihadza/Game-developer.git

# Push
git push -u origin main
```

### Token দিয়ে authentication

GitHub এ password আর কাজ করে না। **Personal Access Token** লাগবে:

1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. **Generate new token (classic)**
3. Scope: `repo` চেক করো
4. Copy করো
5. Push করার সময়:
   - Username: `zihadza`
   - Password: `<token paste>`

অথবা credential cache:

```bash
git config --global credential.helper store
git push -u origin main
# একবার username + token দাও, save হবে
```

### পরবর্তী Commits

```bash
git add .
git commit -m "✨ Added new feature"
git push
```

### .gitignore বানাও

```bash
nano .gitignore
```

কনটেন্ট:

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/

# Flask
instance/
*.log

# Build temp
.zihad3d-build/
*.apk
*.keystore
*.jks

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db

# Termux
.gradle/
```

---

## 🎓 শেখার রিসোর্স

### Babylon.js
- 📖 [Documentation](https://doc.babylonjs.com/)
- 🎥 [YouTube](https://www.youtube.com/@BabylonJS)
- 💬 [Forum](https://forum.babylonjs.com/)

### Three.js
- 📖 [Documentation](https://threejs.org/docs/)
- 📚 [Examples](https://threejs.org/examples/)
- 💬 [Discourse](https://discourse.threejs.org/)

### Android + Gradle
- 📖 [Android Developer](https://developer.android.com/)
- 📖 [Gradle Docs](https://docs.gradle.org/)

### Termux
- 📖 [Termux Wiki](https://wiki.termux.com/)
- 💬 [Reddit r/termux](https://reddit.com/r/termux)

---

## 🤝 Contributing

Contributions স্বাগতম! 

1. Fork করো
2. Feature branch বানাও (`git checkout -b feature/AmazingFeature`)
3. Commit করো (`git commit -m 'Add AmazingFeature'`)
4. Push করো (`git push origin feature/AmazingFeature`)
5. Pull Request খুলো

---

## 📜 License

MIT License — [LICENSE](LICENSE) ফাইল দেখো।

```
Copyright (c) 2026 Zihad

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
```

---

## 👨‍💻 Author

**Zihad**
- GitHub: [@zihadza](https://github.com/zihadza)
- Repository: [Game-developer](https://github.com/zihadza/Game-developer)

---

## ⭐ Support

যদি এই প্রজেক্ট তোমার কাজে লাগে, একটা **⭐ Star** দাও!

---

## 🗺️ Roadmap

### v3.0 (Current) ✅
- [x] Multi-engine projects
- [x] Command palette
- [x] Multi-file tabs
- [x] Auto-save
- [x] Live reload
- [x] Project search
- [x] Build settings panel
- [x] Icon upload
- [x] Starter templates
- [x] ZIP export/import
- [x] Dark/Light theme
- [x] Confetti animation

### v3.1 (Next)
- [ ] Release APK signing
- [ ] Debug/Release toggle
- [ ] Build queue (multi-project)
- [ ] In-app console (FPS, draw calls)
- [ ] GLB inspector
- [ ] Recent files list
- [ ] Better error messages

### v4.0 (Future)
- [ ] Node graph editor
- [ ] Multiplayer signaling
- [ ] Asset store browser
- [ ] Cloud build
- [ ] Performance profiler
- [ ] Localization (বাংলা/English)
- [ ] Git integration UI
- [ ] Crash reporter

---

## 🙏 Acknowledgments

- [Babylon.js](https://www.babylonjs.com/) — Amazing 3D engine
- [Three.js](https://threejs.org/) — WebGL made easy
- [Flask](https://flask.palletsprojects.com/) — Lightweight Python framework
- [CodeMirror](https://codemirror.net/) — In-browser code editor
- [Termux](https://termux.dev/) — Linux on Android
- [Android SDK](https://developer.android.com/studio) — APK build tools

---

<div align="center">

**⚡ Made with ❤️ by Zihad**

**🌟 যদি ভালো লাগে, Star দাও! 🌟**

</div>
