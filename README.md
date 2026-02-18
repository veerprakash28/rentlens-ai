# RentLens

**An AI-powered Facebook Group scraper that finds, filters, and organizes rental listings (like flats and flatmates) into a clean, searchable dashboard.**

A full-stack application using Playwright, Python (FastAPI), and Gemini AI.

## Prerequisites

- **Python 3.9+**
- **Node.js 18+**
- **Google Gemini API Key** (Get one from [Google AI Studio](https://makersuite.google.com/app/apikey))

## Quick Start

### 1. Backend (Python/FastAPI)

Open a terminal and run:

```bash
cd backend

# Create virtual environment (if not already done)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies (if not already done)
pip install -r requirements.txt
# Note: Since we use httpx directly now, ensure httpx is installed:
pip install httpx python-dotenv playwright uvicorn fastapi pydantic

# Install Playwright browsers (first time only)
playwright install chromium

# **IMPORANT**: Configure your API Key
# Create a .env file in backend/ based on .env.example
# Add: GEMINI_API_KEY=your_actual_key_here

# Run the Server
./venv/bin/uvicorn main:app --reload --port 8000
```

The backend will start at `http://localhost:8000`.

### 2. Frontend (Next.js)

Open a **new** terminal window and run:

```bash
cd frontend

# Install dependencies (first time only)
npm install

# Run the Development Server
npm run dev
```

The frontend will start at `http://localhost:3000`.

## Usage

1.  Open `http://localhost:3000` in your browser.
2.  Paste a Facebook Group URL (e.g., `https://www.facebook.com/groups/flat.and.flatmates.without.brokers.bangalore/`).
3.  Set your filters (Rent, Type, Gender, etc.).
4.  Click **"Start Scrape"**.
5.  Wait for the scraper to finish scrolling and the AI to parse the results.
6.  View the filtered list significantly cleaner than Facebook's feed!
