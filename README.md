# Akkido Platform - FinAstro Engine

A fully functional Flask web application for Panchang-based financial backtesting using Vedic astrological principles.

## 🔮 Features

### FinAstro Engine (Fully Functional)
- **Panchang Calculations**: Accurate Sun and Moon position calculations using Swiss Ephemeris
- **Lunar Analysis**: Tithi (30), Nakshatra (27), Yoga (27), Karana (60)
- **Stock Backtesting**: Download historical OHLC data from Yahoo Finance
- **Multi-Filter Support**: Filter by Weekday, Tithi, Nakshatra, Yoga, Karana
- **Performance Analytics**: Win rate, average return, total return, best/worst trades
- **CSV Export**: Download backtest results for further analysis
- **Responsive Design**: Dark modern gradient UI, mobile-friendly

### Platform Overview
- Landing page with 3 engine cards (FinAstro active, Vedic/Numerology coming soon)
- About section with Panchang information
- Modern dark gradient theme with smooth animations

## 📋 Requirements

### Python 3.10+

### Python Packages
```
Flask==2.3.3
pyswisseph==2.10.3.2
pandas==2.0.3
numpy==1.24.3
yfinance==0.2.32
Werkzeug==2.3.7
```

## 📁 Project Structure

```
akkido-platform/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── templates/
│   ├── index.html        # Landing page
│   └── finastro.html     # FinAstro engine page
└── static/
    └── css/
        └── style.css     # Dark gradient styling
```

## 🚀 Local Setup

### 1. Clone the Repository
```bash
git clone https://github.com/mmgsumit762-hash/akkido-platform.git
cd akkido-platform
```

### 2. Create Virtual Environment
```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run Locally
```bash
python app.py
```

Open browser: `http://localhost:5000`

## 🌐 PythonAnywhere Deployment

### Step 1: Create PythonAnywhere Account
1. Go to [pythonanywhere.com](https://www.pythonanywhere.com)
2. Create a free account
3. Verify email

### Step 2: Upload Code
1. Go to "Files" section
2. Create a directory: `/home/yourusername/akkido-platform`
3. Upload all files or use Git:
```bash
git clone https://github.com/mmgsumit762-hash/akkido-platform.git
cd akkido-platform
```

### Step 3: Create Python Virtual Environment
From PythonAnywhere bash console:
```bash
cd /home/yourusername/akkido-platform
mkvirtualenv --python=/usr/bin/python3.10 akkido
pip install -r requirements.txt
```

### Step 4: Configure WSGI
1. Go to "Web" → "Add a new web app"
2. Select "Manual configuration" → "Python 3.10"
3. Edit the WSGI file at `/var/www/yourusername_pythonanywhere_com_wsgi.py`

Replace content with:
```python
import sys
import os

path = '/home/yourusername/akkido-platform'
if path not in sys.path:
    sys.path.append(path)

os.chdir(path)

from app import app as application
```

### Step 5: Set Python Path
In "Web" tab, set:
- **Virtualenv path**: `/home/yourusername/.virtualenvs/akkido`
- **Working directory**: `/home/yourusername/akkido-platform`

### Step 6: Static Files Configuration
In "Web" tab, add static mapping:
- URL: `/static`
- Directory: `/home/yourusername/akkido-platform/static`

### Step 7: Reload Web App
1. Click "Reload" button in the Web tab
2. Your app should be live at: `https://yourusername.pythonanywhere.com`

## 📊 Using the FinAstro Engine

### Basic Workflow

1. **Go to FinAstro**: Click "Launch FinAstro" on homepage
2. **Enter Ticker**: E.g., AAPL, MSFT, GOOGL, RELIANCE, TCS
3. **Select Date Range**: Choose start and end dates
4. **Choose Filter Type**:
   - **All**: Analyze all trading days
   - **Weekday**: Filter by day of week
   - **Tithi**: Filter by lunar day (1-30)
   - **Nakshatra**: Filter by lunar mansion (1-27)
   - **Yoga**: Filter by yoga (1-27)
   - **Karana**: Filter by karana (1-60)
5. **Run Backtest**: Click "Run Backtest"
6. **View Results**:
   - Summary statistics (trades, win rate, returns)
   - Detailed trade table with Panchang values
   - Export as CSV

### Example Queries

- **Best days for tech stocks?**: Filter by Tithi 10 or 25 (Shukla/Krishna Dasami)
- **Weekday performance**: Filter by specific weekday
- **Nakshatra effect**: Compare different nakshatras
- **Moon phase impact**: Use Tithi filter (1-15 = waxing, 16-30 = waning)

## 🧮 Panchang Calculation Details

### Tithi (Lunar Day)
- 30 tithis in a lunar month
- Each tithi = 12° of Moon-Sun separation
- Waxing: 1-15 (Shukla Paksha)
- Waning: 16-30 (Krishna Paksha)

### Nakshatra (Lunar Mansion)
- 27 nakshatras (lunar constellations)
- Each nakshatra ≈ 13.33° of Moon's longitude
- Named: Ashwini, Bharani, Kritika, etc.

### Yoga
- 27 yogas (combinations of Sun + Moon longitude)
- Each yoga ≈ 13.33° total
- Auspicious: Harshan, Shobhan, Atiganda
- Inauspicious: Visha, Vishkumbh

### Karana
- 60 karanas (half-tithis)
- Each karana = 6° of Moon-Sun separation
- Used for timing specific actions

## 🔧 Technical Details

### Swiss Ephemeris Integration
- Accurate astronomical calculations
- Sun and Moon longitudes in ecliptic coordinates
- Proper handling of time zones and Julian Day conversion

### Yahoo Finance Integration
- Real-time and historical OHLC data
- Support for stocks, ETFs, indices
- Automatic handling of weekends/holidays

### Performance Metrics
- **Return %**: (Close - Open) / Open * 100
- **Win Rate**: % of days with positive returns
- **Avg Return**: Mean return across filter
- **Total Return**: Sum of all returns in period
- **Best/Worst Trade**: Best and worst single-day return

## 📝 API Endpoints

### GET /
Landing page

### GET /finastro
FinAstro engine page

### POST /api/backtest
Backtest calculation
```json
{
    "ticker": "AAPL",
    "start_date": "2023-01-01",
    "end_date": "2024-01-01",
    "filter_type": "Tithi",
    "filter_value": "10"
}
```

### GET /api/filter-options/<filter_type>
Get options for filter type

## 🐛 Troubleshooting

### Issue: "No module named 'swisseph'"
**Solution**: Install with correct platform:
```bash
pip install pyswisseph --no-binary :all:
```

### Issue: Swiss Ephemeris path error
**Solution**: Update path in app.py:
```python
swe.set_ephe_path('/path/to/ephemeris')
```

### Issue: No data for ticker
**Solution**: 
- Verify ticker is correct (use Yahoo Finance symbol)
- Check date range has market data
- Try different date range

### Issue: Slow backtest
**Solution**: Use shorter date range or filter for more specific criteria

## 📄 License

This project is open source. Use freely for educational purposes.

## ⚠️ Disclaimer

This platform is for **educational and analytical purposes only**. It is not financial advice. Past performance does not guarantee future results. Always conduct your own research and consult with financial advisors before making investment decisions.

## 🤝 Contributing

Contributions welcome! Areas for enhancement:
- Additional Panchang filters
- More sophisticated return calculations
- User authentication
- Database for saving backtests
- Mobile app
- Advanced charting

## 📞 Support

For issues or questions:
1. Check the troubleshooting section
2. Review code comments
3. Test with different inputs
4. Create an issue on GitHub

---

**Akkido Platform** - Vedic Financial Analysis Engine  
*Combining ancient wisdom with modern data science*
