# FaceGuard-Attendance

AI-Powered Offline Attendance System

---

**FaceGuard-Attendance** replaces the traditional 15-minute roll-call ritual with sub-3-second face recognition. It integrates robust fraud prevention, passive liveness detection, and auto-generates AI-written insights about student engagement—all 100% offline. No paid APIs required, and it runs smoothly on any local environment.

---

## ✨ Features

| Feature                  | Description                                                                                 |
| ------------------------ | ------------------------------------------------------------------------------------------- |
| 👤 Face Attendance       | Mark IN/OUT in under 3 seconds via webcam or photo upload                                   |
| 🤖 AI Narrative Insights | Natural-language summaries (e.g., "3 students at risk. Monday absences 35% above average.") |
| 🔒 Liveness Verification | Passive anti-spoofing using texture, specular, and edge analysis scoring                    |
| ⚠️ Proxy Detection       | Multi-face detection reliably blocks fraudulent buddy-marking before it happens             |
| 😷 Mask Detection        | Intelligent heuristic face-covering check with configurable block/warn modes                |
| 🧠 Focus Monitoring      | Real-time engagement scoring from eye detection, centering, blur, and brightness            |
| 📊 Analytics Dashboard   | Beautiful charts covering daily trends, student performance, and predictions                |
| 📄 PDF Reports           | One-click comprehensive attendance report export                                            |
| 🔐 Secure Auth           | bcrypt passwords, TOTP 2FA for admin, rate-limited resets, and detailed audit logging       |
| 🎬 Demo Mode             | "Load Demo Data" injects testing students + 30 days of realistic attendance history         |

---

## 🔐 Privacy & Offline-First

* No OpenAI / no cloud vision API dependencies
* No GPU required (CPU-friendly design)
* Database: Local SQLite with zero setup required

---

## 🚀 Quick Start

### Prerequisites

* Python 3.9+
* Webcam (for active live attendance)

### 1. Install Dependencies

```bash
git clone <your-repository-url>
cd FaceGuard-Attendance
pip install -r requirements.txt
```

---

### 2. Configure Environment Variables

```bash
cp .env.example .env
```

Open `.env` and configure:

```
SECRET_KEY=<at least 32 characters>
SALT=<at least 16 characters>
ADMIN_EMAIL=admin@yourdomain.com
ADMIN_PASSWORD=<strong password>
```

---

### 3. Run the Application

```bash
streamlit run main.py
```

Open:
👉 [http://localhost:8501](http://localhost:8501)

Login using your admin credentials.

💡 Tip: Use **🎬 Load Demo Data** for quick testing.

---

## 🐳 Docker Deployment

```bash
docker-compose up --build
```

---

## 🏗️ Technical Architecture

```
FaceGuard-Attendance/
├── main.py
├── config/settings.py
├── auth/
├── database/
├── face_recognition/
│   ├── recognition_engine.py
│   ├── liveness_detector.py
│   └── image_utils.py
├── face_mask/
├── face_focus/
├── services/
├── scripts/
├── ui/pages/
└── data/attendance.db
```

---

## 🧠 Face Recognition Stack

* **Detection:** OpenCV Haar Cascade
* **Descriptor:** LBP + HOG + Gabor + DCT → 512-d vector
* **Matching:** Cosine similarity with margin constraints

---

## 🧪 Testing

```bash
pytest tests/ -v
```

---

## 🔒 Security Practices

* Face data stored as non-reversible vectors
* bcrypt password hashing
* Audit logging enabled
* Rate-limited authentication attempts
* Spoof detection alerts

---

## 📜 License

MIT License — free to use, modify, and deploy.

