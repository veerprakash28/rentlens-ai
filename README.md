# 🚀 RentLens: AI-Powered Rental Scraper

**RentLens** is a sophisticated full-stack tool designed to cut through the noise of Facebook Group rental listings. Using **Playwright** for robust scraping and **Google Gemini AI** for intelligent parsing, it finds, filters, and organizes rental posts (flats, flatmates, PGs) into a clean, searchable, and professional dashboard.

---

## 🌟 Key Features

- **Automated Scraping**: Efficiently scrolls through Facebook Groups to capture the latest listings.
- **AI-Powered Parsing**: Uses Gemini AI to extract structured data (Rent, Location, Room Type, Gender Preference) from messy post text.
- **Smart Filtering**: Filter by budget, accommodation type, gender, and more directly on your dashboard.
- **Premium UI**: A modern, sleek interface built with Next.js and TailwindCSS for a superior user experience.

---

## 🛠️ Architecture

- **Frontend**: Next.js 15+, TailwindCSS, TypeScript.
- **Backend**: Python 3.9+, FastAPI, Playwright (Chromium).
- **AI Engine**: Google Gemini API via `google-generativeai` SDK.

---

## 🚦 Prerequisites

Before you begin, ensure you have the following installed:
- **Python 3.9+**
- **Node.js 18+**
- **Google Gemini API Key**: Obtain one from the [Google AI Studio](https://aistudio.google.com/app/apikey).

---

## ⚡ Quick Start

### 1. Backend Setup

```bash
cd backend

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium

# Configure Environment Variables
# Copy .env.example to .env and add your GEMINI_API_KEY
cp .env.example .env
```

**Run Backend:**
```bash
uvicorn main:app --reload --port 8000
```
Backend will be available at: `http://localhost:8000`

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run Development Server
npm run dev
```
Frontend will be available at: `http://localhost:3000`

---

## 📖 How to Use

1. **Launch**: Start both backend and frontend servers.
2. **Navigate**: Open `http://localhost:3000` in your browser.
3. **Target**: Paste the URL of a public Facebook Group (e.g., *Bangalore Flat and Flatmates*).
4. **Filter**: Set your preferences for Rent, Gender, and Room Type.
5. **Execute**: Click **"Start Scrape"** and watch the AI organize the chaos!

---

## 🤝 Contributing

Contributions are welcome! Feel free to open issues or submit pull requests to improve the scraper's efficiency or the dashboard's features.

---

*Made with ❤️ for easier house hunting.*

