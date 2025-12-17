# Price-Atlas 🗺️ 

### AI-Powered Amazon Competitor Analysis Tool

Price-Atlas is a full-stack tool designed to help users analyze Amazon products and their competitors using **web scraping**, **data persistence**, and **LLM-powered insights**.  
Users input an Amazon ASIN, trigger competitor discovery, and receive an AI-generated competitive analysis report.



## 🚀 Features

- 🔍 Amazon product scraping via **Oxylabs Web Scraping API**
- 🗄️ **Local Database Storage** for products and competitors
- 🧠 **LLM-Based Competitive Analysis**
- 📊 **Competitor Discovery & Comparison**
- 🧩 **Modular, Extensible Architecture**


## 🧠 How It Works (High-Level Overview)

Price-Atlas follows a clear, step-by-step pipeline:

```
1. User enters Amazon product ASIN
        ↓
2. Scrape details from Amazon
        ↓
3. Store product in local database
        ↓
4. User clicks "Start competitor analysis"
        ↓
5. Search for similar products on Amazon
        ↓
6. Scrape details for all competitors found
        ↓
7. Store competitors linked to original product
        ↓
8. User clicks "Analysis with LLM"
        ↓
9. Send product + competitors to AI
        ↓
10. Get competitive analysis report
        ↓
11. Display results to the user
```


## 🛠️ Tech Stack

| Layer            | Technology |
|------------------|------------|
| Language         | Python  |
| Database         | SQLite / PostgreSQL |
| Web Scraping     | Oxylabs Web Scraping API |
| AI Analysis      | LLM API (OpenAI / similar) |
| UI         | Streamlit |
| Frontend | Django Templates / React (future) |

> \* Scraping method depends on Amazon page complexity and anti-bot behavior.



## 📁 Project Structure 

price-atlas/
│
├── app.py                 # Streamlit entry point
├── scraper/
│   └── amazon.py          # Oxylabs scraping logic
│
├── analysis/
│   └── llm.py             # LLM prompt & analysis logic
│
├── storage/
│   └── database.py        # Local data persistence
│
├── pyproject.toml
├── uv.lock
└── README.md


## ⚙️ Running Locally

### 1️⃣ Clone the repository

```bash
git clone https://github.com/your-username/price-atlas.git
cd price-atlas
```

### 2️⃣ Install dependencies using uv

If you don’t have uv installed:

```bash
pip install uv

```

Install project dependencies:

```bash
uv sync

```

### 3️⃣ Set environment variables

Create a .env file in the root directory:

```env
OXYLABS_USERNAME=your_username
OXYLABS_PASSWORD=your_password
OPENAI_API_KEY=your_api_key

```

### 4️⃣ Run the Streamlit app

```bash
streamlit run app.py

```

### ☁️ Deployment

---

This project is deployed using Streamlit Community Cloud:

1.	Push the repository to GitHub
2.	Connect the repo on Streamlit Cloud
3.	Add environment variables in the Streamlit dashboard
4.	Deploy 🚀

## ⚠️ Disclaimer

This project is for educational and research purposes only.

•	Scraping Amazon may violate their Terms of Service

•	Use responsibly and ensure compliance with local laws

•	The author is not responsible for misuse


## 📜 License

Licenced under MIT
