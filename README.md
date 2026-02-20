# GOOG & USD/CHF Daily Tracker

This is a lightweight financial dashboard built with Streamlit and Plotly to track the value of Alphabet Inc. (GOOG) stock in both USD and CHF.

### 🚀 Built with Gemini Vibe Coding
This project was entirely **vibe coded** in collaboration with **Gemini**. The development process was a continuous, prompt-driven dialogue—iterating through data alignment, visual styling, and deployment hurdles in real-time.

### Features
* **Real-time Data:** Fetches the latest daily/hourly data via Yahoo Finance.
* **Three Perspectives:**
    1. **GOOG in CHF:** The converted value of the stock for Swiss-based investors.
    2. **GOOG in USD:** The standard market price.
    3. **USD/CHF Rate:** The exchange rate affecting the conversion.
* **Interactive Views:** Toggle between 1 Week, 1 Month, 1 Year, and 10 Year timeframes.
* **Smart Annotations:** Bold lines, dynamic Max/Min reference lines, and "Latest Value" callouts.

### Live Demo
The app is automatically deployed and can be visited here:
👉 **[https://googchf.streamlit.app/](https://googchf.streamlit.app/)**

### How to Run Locally
1. Ensure you have a virtual environment with the dependencies:
   `pip install streamlit yfinance pandas plotly`
2. Make the script executable and run it:
   ```bash
   chmod +x goog_chf.py
   ./goog_chf.py
