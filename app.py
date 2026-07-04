"""
Akkido Platform - FinAstro Engine for Panchang-based Financial Backtesting
Flask application for PythonAnywhere deployment
"""

from flask import Flask, render_template, request, jsonify
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import swisseph as swe
from math import floor

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Initialize Swiss Ephemeris
swe.set_ephe_path('/usr/share/swisseph')

# ==================== PANCHANG CALCULATIONS ====================

def get_tithi_nakshatra_yoga_karana(jd, lat=0, lon=0):
    """
    Calculate Panchang elements (Tithi, Nakshatra, Yoga, Karana) for a given Julian Day.
    
    Args:
        jd: Julian Day number
        lat, lon: Latitude and Longitude (default 0, 0 for simple calculation)
    
    Returns:
        dict with tithi, nakshatra, yoga, karana
    """
    try:
        # Calculate Sun and Moon longitudes
        sun_pos = swe.calc_ut(jd, swe.SUN)[0]
        moon_pos = swe.calc_ut(jd, swe.MOON)[0]
        
        # Normalize to 0-360
        sun_long = sun_pos[0] % 360
        moon_long = moon_pos[0] % 360
        
        # Calculate Tithi (lunar day)
        tithi_angle = (moon_long - sun_long) % 360
        tithi = int(tithi_angle / 12) + 1  # Each tithi is 12 degrees
        if tithi > 30:
            tithi = 30
        if tithi == 0:
            tithi = 1
        
        # Calculate Nakshatra (lunar mansion)
        nakshatra = int(moon_long / 13.333) + 1  # 27 nakshatras, each ~13.33 degrees
        if nakshatra > 27:
            nakshatra = 27
        if nakshatra == 0:
            nakshatra = 1
        
        # Calculate Yoga
        yoga_angle = (sun_long + moon_long) % 360
        yoga = int(yoga_angle / 13.333) + 1  # 27 yogas
        if yoga > 27:
            yoga = 27
        if yoga == 0:
            yoga = 1
        
        # Calculate Karana (half-tithi)
        karana = int(tithi_angle / 6) + 1  # Each karana is 6 degrees
        if karana > 60:
            karana = 60
        if karana == 0:
            karana = 1
        
        return {
            'tithi': tithi,
            'nakshatra': nakshatra,
            'yoga': yoga,
            'karana': karana
        }
    except Exception as e:
        print(f"Error calculating panchang: {e}")
        return {
            'tithi': 1,
            'nakshatra': 1,
            'yoga': 1,
            'karana': 1
        }

def get_weekday_name(date):
    """Get weekday name from date"""
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    return days[date.weekday()]

def get_jd_from_date(date):
    """Convert Python date to Julian Day number"""
    year = date.year
    month = date.month
    day = date.day
    
    # Simple Julian Day calculation
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    
    jdn = day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
    return jdn + 0.5  # Add 0.5 for noon

def apply_filter(df, filter_type, filter_value):
    """Filter dataframe based on filter type and value"""
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

def calculate_backtest(ticker, start_date, end_date, filter_type, filter_value):
    """
    Download stock data and perform Panchang-based backtesting
    """
    try:
        # Download historical data
        data = yf.download(ticker, start=start_date, end=end_date, progress=False)
        
        if data.empty:
            return {'error': f'No data found for ticker {ticker}'}
        
        data = data.reset_index()
        data.columns = [col.lower() for col in data.columns]
        
        # Calculate Panchang for each date
        panchang_data = []
        for idx, row in data.iterrows():
            date = row['date']
            if hasattr(date, 'date'):
                date = date.date()
            
            jd = get_jd_from_date(date)
            panchang = get_tithi_nakshatra_yoga_karana(jd)
            
            panchang_data.append({
                'date': date,
                'weekday': get_weekday_name(date),
                'tithi': panchang['tithi'],
                'nakshatra': panchang['nakshatra'],
                'yoga': panchang['yoga'],
                'karana': panchang['karana'],
                'open': row['open'],
                'close': row['close'],
                'high': row['high'],
                'low': row['low'],
                'volume': row['volume']
            })
        
        df = pd.DataFrame(panchang_data)
        
        # Apply filter
        df_filtered = apply_filter(df, filter_type, filter_value)
        
        if df_filtered.empty:
            return {
                'error': f'No data matching filter: {filter_type} = {filter_value}',
                'results': [],
                'stats': {}
            }
        
        # Calculate returns
        df_filtered = df_filtered.copy()
        df_filtered['return_pct'] = ((df_filtered['close'] - df_filtered['open']) / df_filtered['open'] * 100).round(2)
        
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
        
        return {
            'results': results,
            'stats': stats,
            'ticker': ticker,
            'filter_type': filter_type,
            'filter_value': filter_value
        }
    
    except Exception as e:
        return {'error': str(e)}

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
    """API endpoint for backtesting"""
    try:
        data = request.get_json()
        
        ticker = data.get('ticker', '').upper()
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        filter_type = data.get('filter_type', 'All')
        filter_value = data.get('filter_value', '')
        
        if not ticker or not start_date or not end_date:
            return jsonify({'error': 'Missing required parameters'}), 400
        
        result = calculate_backtest(ticker, start_date, end_date, filter_type, filter_value)
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/filter-options/<filter_type>')
def api_filter_options(filter_type):
    """Get filter options based on filter type"""
    options = {
        'All': [],
        'Weekday': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
        'Tithi': list(range(1, 31)),
        'Nakshatra': list(range(1, 28)),
        'Yoga': list(range(1, 28)),
        'Karana': list(range(1, 61))
    }
    return jsonify(options.get(filter_type, []))

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    return render_template('index.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# ==================== WSGI FOR PYTHONANYWHERE ====================
# In PythonAnywhere, use this in your WSGI configuration file:
# import sys
# path = '/home/yourusername/akkido-platform'
# if path not in sys.path:
#     sys.path.append(path)
# from app import app as application

if __name__ == '__main__':
    app.run(debug=True)
