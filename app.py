"""
Akkido Platform - FinAstro Engine for Panchang-based Financial Backtesting
Flask application for PythonAnywhere deployment
"""

from flask import Flask, render_template, request, jsonify, redirect
from flask_cors import CORS
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import swisseph as swe
from math import floor
import logging
import os
import platform
import re

# ==================== CONFIGURATION ====================

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Enable CORS for cross-origin requests
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== PANCHANG CONSTANTS ====================

TITHI_DEGREES = 12  # 30 tithis × 12° = 360°
NAKSHATRA_DEGREES = 13.333  # 27 nakshatras × 13.333° = 360°
YOGA_DEGREES = 13.333  # 27 yogas × 13.333° = 360°
KARANA_DEGREES = 6  # 60 karanas × 6° = 360°

MAX_TITHI = 30
MAX_NAKSHATRA = 27
MAX_YOGA = 27
MAX_KARANA = 60

YFINANCE_TIMEOUT = 15  # seconds

# ==================== EPHEMERIS INITIALIZATION ====================

def initialize_ephemeris():
    """Initialize Swiss Ephemeris with cross-platform path handling"""
    ephe_path = None
    
    # Try common paths based on platform
    if platform.system() == 'Windows':
        # Windows paths
        paths_to_try = [
            r'C:\swisseph',
            os.path.expanduser('~/.swisseph'),
        ]
    else:
        # Unix/Linux/macOS paths
        paths_to_try = [
            '/usr/share/swisseph',
            '/usr/local/share/swisseph',
            os.path.expanduser('~/.swisseph'),
        ]
    
    for path in paths_to_try:
        if os.path.exists(path):
            ephe_path = path
            logger.info(f"Swiss Ephemeris path found: {ephe_path}")
            break
    
    if ephe_path:
        try:
            swe.set_ephe_path(ephe_path)
            logger.info("Swiss Ephemeris initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to set ephemeris path: {e}. Using default.")
    else:
        logger.warning("Swiss Ephemeris path not found. Using default path.")

initialize_ephemeris()

# ==================== INPUT VALIDATION ====================

def validate_ticker(ticker):
    """Validate stock ticker symbol"""
    if not ticker:
        return False, "Ticker is required"
    
    ticker = ticker.upper().strip()
    
    # Allow letters, numbers, dots, hyphens (common for stocks)
    if not re.match(r'^[A-Z0-9\-\.]{1,10}$', ticker):
        return False, "Invalid ticker format (max 10 chars, alphanumeric, -, .)"
    
    return True, ticker

def validate_dates(start_date_str, end_date_str):
    """Validate and parse date range"""
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        return False, None, None, "Invalid date format (use YYYY-MM-DD)"
    
    today = datetime.now().date()
    
    if start_date >= end_date:
        return False, None, None, "Start date must be before end date"
    
    if end_date > today:
        return False, None, None, "End date cannot be in the future"
    
    if (end_date - start_date).days < 1:
        return False, None, None, "Date range must be at least 1 day"
    
    if (end_date - start_date).days > 5000:
        return False, None, None, "Date range too large (max ~13 years)"
    
    return True, start_date, end_date, None

def validate_filter(filter_type, filter_value):
    """Validate filter type and value"""
    valid_filters = ['All', 'Weekday', 'Tithi', 'Nakshatra', 'Yoga', 'Karana']
    
    if filter_type not in valid_filters:
        return False, f"Invalid filter type: {filter_type}"
    
    if filter_type == 'All':
        return True, None
    
    if not filter_value:
        return False, f"Filter value required for {filter_type}"
    
    try:
        if filter_type == 'Weekday':
            valid_weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            if filter_value not in valid_weekdays:
                return False, f"Invalid weekday: {filter_value}"
        
        elif filter_type == 'Tithi':
            val = int(filter_value)
            if not (1 <= val <= MAX_TITHI):
                return False, f"Tithi must be 1-{MAX_TITHI}"
        
        elif filter_type == 'Nakshatra':
            val = int(filter_value)
            if not (1 <= val <= MAX_NAKSHATRA):
                return False, f"Nakshatra must be 1-{MAX_NAKSHATRA}"
        
        elif filter_type == 'Yoga':
            val = int(filter_value)
            if not (1 <= val <= MAX_YOGA):
                return False, f"Yoga must be 1-{MAX_YOGA}"
        
        elif filter_type == 'Karana':
            val = int(filter_value)
            if not (1 <= val <= MAX_KARANA):
                return False, f"Karana must be 1-{MAX_KARANA}"
    
    except ValueError:
        return False, f"Invalid {filter_type} value"
    
    return True, None

# ==================== PANCHANG CALCULATIONS ====================

def normalize_date(d):
    """Convert datetime to date if needed"""
    if isinstance(d, datetime):
        return d.date()
    return d

def get_jd_from_date(date):
    """
    Convert Python date to Julian Day number
    
    Args:
        date: Python date object
    
    Returns:
        float: Julian Day number at noon
    """
    year = date.year
    month = date.month
    day = date.day
    
    # Standard Julian Day calculation
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    
    jdn = day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
    return jdn + 0.5  # Add 0.5 for noon

def clamp(value, min_val, max_val):
    """Clamp value between min and max"""
    return max(min_val, min(max_val, value))

def get_tithi_nakshatra_yoga_karana(jd, lat=0, lon=0):
    """
    Calculate Panchang elements (Tithi, Nakshatra, Yoga, Karana) for a given Julian Day.
    
    Args:
        jd (float): Julian Day number
        lat (float): Latitude (default 0 for simple calculation)
        lon (float): Longitude (default 0 for simple calculation)
    
    Returns:
        dict: Contains tithi, nakshatra, yoga, karana (all 1-indexed)
    
    Raises:
        Exception: If calculation fails
    """
    try:
        # Calculate Sun and Moon longitudes
        sun_pos = swe.calc_ut(jd, swe.SUN)[0]
        moon_pos = swe.calc_ut(jd, swe.MOON)[0]
        
        # Normalize to 0-360 range
        sun_long = sun_pos[0] % 360
        moon_long = moon_pos[0] % 360
        
        # Tithi (lunar day): Moon-Sun separation
        tithi_angle = (moon_long - sun_long) % 360
        tithi = int(tithi_angle / TITHI_DEGREES) + 1
        tithi = clamp(tithi, 1, MAX_TITHI)
        
        # Nakshatra (lunar mansion): Moon's longitude
        nakshatra = int(moon_long / NAKSHATRA_DEGREES) + 1
        nakshatra = clamp(nakshatra, 1, MAX_NAKSHATRA)
        
        # Yoga: Sun + Moon longitude
        yoga_angle = (sun_long + moon_long) % 360
        yoga = int(yoga_angle / YOGA_DEGREES) + 1
        yoga = clamp(yoga, 1, MAX_YOGA)
        
        # Karana (half-tithi): Moon-Sun separation / 6
        karana = int(tithi_angle / KARANA_DEGREES) + 1
        karana = clamp(karana, 1, MAX_KARANA)
        
        return {
            'tithi': tithi,
            'nakshatra': nakshatra,
            'yoga': yoga,
            'karana': karana
        }
    
    except Exception as e:
        logger.error(f"Error calculating panchang for JD {jd}: {e}")
        # Return default values on error
        return {
            'tithi': 1,
            'nakshatra': 1,
            'yoga': 1,
            'karana': 1
        }

def get_weekday_name(date):
    """
    Get weekday name from date
    
    Args:
        date: Python date object
    
    Returns:
        str: Weekday name
    """
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    return days[date.weekday()]

def apply_filter(df, filter_type, filter_value):
    """
    Filter dataframe based on filter type and value
    
    Args:
        df (pd.DataFrame): Data with panchang columns
        filter_type (str): Type of filter
        filter_value (str): Value to filter by
    
    Returns:
        pd.DataFrame: Filtered data
    """
    if filter_type == 'All':
        return df
    elif filter_type == 'Weekday':
        return df[df['weekday'] == filter_value]
    elif filter_type == 'Tithi':
        return df[df['tithi'] == int(filter_value)]
    elif filter_type == 'Nakshatra':
        return df[df['nakshatra'] == int(filter_value)]
    elif filter_type == 'Yoga':
        return df[df['yoga'] == int(filter_value)]
    elif filter_type == 'Karana':
        return df[df['karana'] == int(filter_value)]
    
    return df

# ==================== CSV EXPORT ====================

def escape_csv_field(value):
    """
    Escape CSV field to prevent injection attacks
    
    Args:
        value: Any value to escape
    
    Returns:
        str: Safely escaped value
    """
    s = str(value)
    
    # Prevent formula injection
    if s and s[0] in ('=', '+', '-', '@'):
        s = "'" + s
    
    # Escape quotes
    if '"' in s:
        s = s.replace('"', '""')
    
    # Quote if contains comma or newline
    if ',' in s or '\n' in s or '"' in s:
        s = '"' + s + '"'
    
    return s

def generate_csv_report(data):
    """
    Generate CSV report from backtest results
    
    Args:
        data (dict): Backtest results
    
    Returns:
        str: CSV content
    """
    results = data['results']
    stats = data['stats']
    
    csv = 'Akkido FinAstro Backtest Results\n'
    csv += f'Ticker: {escape_csv_field(data["ticker"])}\n'
    csv += f'Filter: {escape_csv_field(data["filter_type"])} = {escape_csv_field(data["filter_value"] or "All")}\n'
    csv += f'Generated: {datetime.now().isoformat()}\n\n'
    
    csv += 'Summary Statistics\n'
    csv += 'Trades,Win Rate,Avg Return,Total Return,Best Trade,Worst Trade\n'
    csv += f'{stats["trades"]},{stats["win_rate"]}%,{stats["avg_return"]}%,{stats["total_return"]}%,{stats["best_trade"]}%,{stats["worst_trade"]}%\n\n'
    
    csv += 'Trade Details\n'
    csv += 'Date,Weekday,Tithi,Nakshatra,Yoga,Karana,Open,Close,Return %\n'
    
    for row in results:
        csv += f'{row["date"]},{row["weekday"]},{row["tithi"]},{row["nakshatra"]},{row["yoga"]},{row["karana"]},{row["open"]:.2f},{row["close"]:.2f},{row["return_pct"]:.2f}\n'
    
    return csv

# ==================== BACKTESTING ENGINE ====================

def calculate_backtest(ticker, start_date, end_date, filter_type, filter_value):
    """
    Download stock data and perform Panchang-based backtesting
    
    Args:
        ticker (str): Stock symbol
        start_date (str): Start date (YYYY-MM-DD)
        end_date (str): End date (YYYY-MM-DD)
        filter_type (str): Filter type
        filter_value (str): Filter value
    
    Returns:
        dict: Results or error message
    """
    try:
        logger.info(f"Starting backtest: {ticker} from {start_date} to {end_date}, filter: {filter_type}={filter_value}")
        
        # Download historical data with timeout
        data = yf.download(
            ticker,
            start=start_date,
            end=end_date,
            progress=False,
            timeout=YFINANCE_TIMEOUT
        )
        
        if data.empty:
            logger.warning(f"No data found for ticker: {ticker}")
            return {'error': f'No data found for ticker {ticker}. Verify the symbol and try again.'}
        
        # Normalize column names
        data = data.reset_index()
        data.columns = [col.lower() for col in data.columns]
        
        logger.info(f"Downloaded {len(data)} rows for {ticker}")
        
        # Calculate Panchang for each date
        panchang_data = []
        for idx, row in data.iterrows():
            date = normalize_date(row['date'])
            
            jd = get_jd_from_date(date)
            panchang = get_tithi_nakshatra_yoga_karana(jd)
            
            panchang_data.append({
                'date': date,
                'weekday': get_weekday_name(date),
                'tithi': panchang['tithi'],
                'nakshatra': panchang['nakshatra'],
                'yoga': panchang['yoga'],
                'karana': panchang['karana'],
                'open': float(row['open']),
                'close': float(row['close']),
                'high': float(row['high']),
                'low': float(row['low']),
                'volume': float(row['volume'])
            })
        
        df = pd.DataFrame(panchang_data)
        
        # Apply filter
        df_filtered = apply_filter(df, filter_type, filter_value)
        
        if df_filtered.empty:
            logger.warning(f"No data matching filter: {filter_type} = {filter_value}")
            return {
                'error': f'No data matching filter: {filter_type} = {filter_value}',
                'results': [],
                'stats': {}
            }
        
        # Calculate returns
        df_filtered = df_filtered.copy()
        df_filtered['return_pct'] = (
            (df_filtered['close'] - df_filtered['open']) / df_filtered['open'] * 100
        ).round(2)
        
        # Calculate statistics
        trades = len(df_filtered)
        wins = len(df_filtered[df_filtered['return_pct'] > 0])
        win_rate = (wins / trades * 100) if trades > 0 else 0
        avg_return = df_filtered['return_pct'].mean()
        total_return = df_filtered['return_pct'].sum()
        best_trade = df_filtered['return_pct'].max()
        worst_trade = df_filtered['return_pct'].min()
        
        results = df_filtered.to_dict('records')
        
        # Format dates for JSON
        for r in results:
            r['date'] = str(r['date'])
        
        stats = {
            'trades': int(trades),
            'win_rate': round(win_rate, 2),
            'avg_return': round(avg_return, 2),
            'total_return': round(total_return, 2),
            'best_trade': round(best_trade, 2),
            'worst_trade': round(worst_trade, 2)
        }
        
        logger.info(f"Backtest completed: {trades} trades, {win_rate:.2f}% win rate")
        
        return {
            'results': results,
            'stats': stats,
            'ticker': ticker,
            'filter_type': filter_type,
            'filter_value': filter_value
        }
    
    except Exception as e:
        logger.error(f"Backtest error for {ticker}: {str(e)}", exc_info=True)
        return {'error': f'Backtest failed: {str(e)}'}

# ==================== ROUTES ====================

@app.route('/')
def index():
    """Landing page with platform overview"""
    return render_template('index.html')

@app.route('/finastro')
def finastro():
    """FinAstro engine page"""
    return render_template('finastro.html')

@app.route('/api/backtest', methods=['POST'])
def api_backtest():
    """
    API endpoint for backtesting
    
    Expected JSON body:
    {
        "ticker": "AAPL",
        "start_date": "2023-01-01",
        "end_date": "2024-01-01",
        "filter_type": "Tithi",
        "filter_value": "10"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body must be JSON'}), 400
        
        # Validate ticker
        is_valid, ticker_result = validate_ticker(data.get('ticker', ''))
        if not is_valid:
            return jsonify({'error': ticker_result}), 400
        ticker = ticker_result
        
        # Validate dates
        is_valid, start_date, end_date, error = validate_dates(
            data.get('start_date', ''),
            data.get('end_date', '')
        )
        if not is_valid:
            return jsonify({'error': error}), 400
        
        start_date_str = start_date.isoformat()
        end_date_str = end_date.isoformat()
        
        # Validate filter
        filter_type = data.get('filter_type', 'All')
        filter_value = data.get('filter_value', '')
        
        is_valid, error = validate_filter(filter_type, filter_value)
        if not is_valid:
            return jsonify({'error': error}), 400
        
        # Run backtest
        result = calculate_backtest(ticker, start_date_str, end_date_str, filter_type, filter_value)
        
        if 'error' in result and result.get('results') == []:
            return jsonify(result), 400
        
        return jsonify(result), 200
    
    except Exception as e:
        logger.error(f"API error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/filter-options/<filter_type>')
def api_filter_options(filter_type):
    """
    Get filter options based on filter type
    
    Args:
        filter_type (str): Type of filter
    
    Returns:
        json: List of available values for the filter
    """
    options = {
        'All': [],
        'Weekday': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
        'Tithi': list(range(1, MAX_TITHI + 1)),
        'Nakshatra': list(range(1, MAX_NAKSHATRA + 1)),
        'Yoga': list(range(1, MAX_YOGA + 1)),
        'Karana': list(range(1, MAX_KARANA + 1))
    }
    
    return jsonify(options.get(filter_type, [])), 200

@app.route('/api/export-csv', methods=['POST'])
def api_export_csv():
    """
    Generate and return CSV export of backtest results
    
    Expected JSON body: Same as /api/backtest response
    """
    try:
        data = request.get_json()
        
        if not data or 'results' not in data or 'stats' not in data:
            return jsonify({'error': 'Invalid data'}), 400
        
        csv_content = generate_csv_report(data)
        
        return csv_content, 200, {
            'Content-Type': 'text/csv',
            'Content-Disposition': f'attachment; filename=finastro-{data["ticker"]}-{datetime.now().date()}.csv'
        }
    
    except Exception as e:
        logger.error(f"Export error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Export failed'}), 500

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    logger.warning(f"404 error: {request.path}")
    return render_template('index.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"500 error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

@app.before_request
def enforce_https():
    """Enforce HTTPS in production"""
    if os.getenv('FLASK_ENV') == 'production':
        if request.headers.get('X-Forwarded-Proto', 'http') == 'http':
            url = request.url.replace('http://', 'https://', 1)
            return redirect(url, code=301)

# ==================== APP ENTRY POINT ====================

if __name__ == '__main__':
    # Production: use WSGI server (Gunicorn, uWSGI)
    # Development: use Flask development server
    debug = os.getenv('FLASK_ENV') != 'production'
    app.run(debug=debug, host='0.0.0.0', port=5000)
