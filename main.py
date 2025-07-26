import os
import logging
from datetime import datetime, timedelta
from binance.um_futures import UMFutures
import ta
import pandas as pd
from time import sleep
from binance.error import ClientError

# Security: Use environment variables for API credentials
api = os.getenv('BINANCE_API_KEY')
secret = os.getenv('BINANCE_SECRET_KEY')

# Security: Validate API credentials
if not api or not secret:
    raise ValueError("API credentials not found. Set BINANCE_API_KEY and BINANCE_SECRET_KEY environment variables")

# Security: Add logging for monitoring
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler()
    ]
)

client = UMFutures(key=api, secret=secret)

# Security: Validate configuration parameters
tp = max(0.001, min(0.1, 0.012))  # Limit TP between 0.1% and 10%
sl = max(0.001, min(0.1, 0.009))  # Limit SL between 0.1% and 10%
volume = max(1, min(1000, 10))    # Limit volume between 1 and 1000
leverage = max(1, min(125, 10))   # Limit leverage between 1 and 125
type = 'ISOLATED' if type in ['ISOLATED', 'CROSS'] else 'ISOLATED'
qty = max(1, min(50, 100))        # Limit concurrent positions

# Security: Rate limiting variables
last_api_call = {}
MIN_API_INTERVAL = 0.1  # Minimum time between API calls

def rate_limit_check(function_name):
    """Security: Implement rate limiting for API calls"""
    current_time = datetime.now()
    if function_name in last_api_call:
        time_diff = (current_time - last_api_call[function_name]).total_seconds()
        if time_diff < MIN_API_INTERVAL:
            sleep(MIN_API_INTERVAL - time_diff)
    last_api_call[function_name] = datetime.now()

def validate_symbol(symbol):
    """Security: Validate symbol format"""
    if not isinstance(symbol, str) or len(symbol) < 6 or not symbol.endswith('USDT'):
        return False
    return True

def get_balance_usdt():
    """
    Security: Enhanced balance retrieval with validation
    """
    rate_limit_check('get_balance')
    try:
        response = client.balance(recvWindow=6000)
        if not response or not isinstance(response, list):
            logging.error("Invalid balance response format")
            return None
            
        for elem in response:
            if elem.get('asset') == 'USDT':
                balance = float(elem.get('balance', 0))
                # Security: Validate balance is reasonable
                if balance < 0 or balance > 1000000:  # Max 1M USDT check
                    logging.warning(f"Unusual balance detected: {balance}")
                return balance
        return 0.0

    except ClientError as error:
        logging.error(f"Balance error: {error.status_code}, {error.error_code}, {error.error_message}")
        return None
    except Exception as e:
        logging.error(f"Unexpected balance error: {str(e)}")
        return None

def get_tickers_usdt():
    """Security: Enhanced ticker retrieval with validation"""
    rate_limit_check('get_tickers')
    try:
        resp = client.ticker_price()
        if not resp or not isinstance(resp, list):
            logging.error("Invalid ticker response format")
            return []
            
        tickers = []
        for elem in resp:
            symbol = elem.get('symbol', '')
            if validate_symbol(symbol) and symbol not in ['USDCUSDT', 'BUSDUSDT']:  # Exclude stablecoins
                tickers.append(symbol)
        
        logging.info(f"Retrieved {len(tickers)} valid USDT pairs")
        return tickers[:200]  # Security: Limit to 200 symbols max
        
    except ClientError as error:
        logging.error(f"Ticker error: {error.status_code}, {error.error_code}, {error.error_message}")
        return []

def klines(symbol):
    """Security: Enhanced klines with validation"""
    if not validate_symbol(symbol):
        logging.error(f"Invalid symbol: {symbol}")
        return None
        
    rate_limit_check('klines')
    try:
        resp = pd.DataFrame(client.klines(symbol, '15m', limit=200))  # Security: Limit data
        if resp.empty or len(resp.columns) < 6:
            logging.error(f"Invalid klines data for {symbol}")
            return None
            
        resp = resp.iloc[:,:6]
        resp.columns = ['Time', 'Open', 'High', 'Low', 'Close', 'Volume']
        resp = resp.set_index('Time')
        resp.index = pd.to_datetime(resp.index, unit='ms')
        resp = resp.astype(float)
        
        # Security: Validate price data
        if (resp <= 0).any().any():
            logging.error(f"Invalid price data detected for {symbol}")
            return None
            
        return resp
    except ClientError as error:
        logging.error(f"Klines error for {symbol}: {error.status_code}, {error.error_code}, {error.error_message}")
        return None

def set_leverage(symbol, level):
    """Security: Enhanced leverage setting with validation"""
    if not validate_symbol(symbol):
        return False
        
    level = max(1, min(125, int(level)))  # Security: Validate leverage
    rate_limit_check('set_leverage')
    
    try:
        response = client.change_leverage(symbol=symbol, leverage=level, recvWindow=6000)
        logging.info(f"Leverage set for {symbol}: {level}x")
        return True
    except ClientError as error:
        logging.error(f"Leverage error for {symbol}: {error.status_code}, {error.error_code}, {error.error_message}")
        return False

def set_mode(symbol, margin_type):
    """Security: Enhanced margin type setting with validation"""
    if not validate_symbol(symbol):
        return False
        
    if margin_type not in ['ISOLATED', 'CROSS']:
        margin_type = 'ISOLATED'
        
    rate_limit_check('set_mode')
    try:
        response = client.change_margin_type(symbol=symbol, marginType=margin_type, recvWindow=6000)
        logging.info(f"Margin type set for {symbol}: {margin_type}")
        return True
    except ClientError as error:
        if error.error_code != -4046:  # Ignore "No need to change margin type"
            logging.error(f"Margin type error for {symbol}: {error.status_code}, {error.error_code}, {error.error_message}")
        return False

# Price precision. BTC has 1, XRP has 4
def get_price_precision(symbol):
    """
    Get the price precision for a given symbol.

    Parameters:
    symbol (str): The symbol for which to retrieve the price precision.

    Returns:
    int: The price precision for the given symbol.

    """
    resp = client.exchange_info()['symbols']
    for elem in resp:
        if elem['symbol'] == symbol:
            return elem['pricePrecision']


# Amount precision. BTC has 3, XRP has 1
def get_qty_precision(symbol):
    """
    Get the quantity precision for a given symbol.

    Parameters:
    symbol (str): The symbol for which to retrieve the quantity precision.

    Returns:
    int: The quantity precision for the given symbol.
    """
    resp = client.exchange_info()['symbols']
    for elem in resp:
        if elem['symbol'] == symbol:
            return elem['quantityPrecision']


# Open new order with the last price, and set TP and SL:
def open_order(symbol, side):
    """Security: Enhanced order placement with validation"""
    if not validate_symbol(symbol) or side not in ['buy', 'sell']:
        logging.error(f"Invalid order parameters: {symbol}, {side}")
        return False
        
    rate_limit_check('open_order')
    try:
        # Security: Get current price with validation
        price_data = client.ticker_price(symbol)
        if not price_data or 'price' not in price_data:
            logging.error(f"Could not get price for {symbol}")
            return False
            
        price = float(price_data['price'])
        if price <= 0:
            logging.error(f"Invalid price for {symbol}: {price}")
            return False
            
        qty_precision = get_qty_precision(symbol)
        price_precision = get_price_precision(symbol)
        
        if qty_precision is None or price_precision is None:
            logging.error(f"Could not get precision for {symbol}")
            return False
            
        # Security: Calculate and validate quantity
        calculated_qty = volume / price
        qty = round(calculated_qty, qty_precision)
        
        # Security: Validate minimum order size
        if qty <= 0 or calculated_qty * price < 5:  # Minimum 5 USDT order
            logging.error(f"Order size too small for {symbol}: {qty}")
            return False
            
        # Security: Validate maximum order size (10% of balance)
        balance = get_balance_usdt()
        if balance and calculated_qty * price > balance * 0.1:
            logging.error(f"Order size too large for {symbol}: {calculated_qty * price} > {balance * 0.1}")
            return False
        
        # Place main order
        order_side = 'BUY' if side == 'buy' else 'SELL'
        resp1 = client.new_order(
            symbol=symbol, 
            side=order_side, 
            type='MARKET',  # Security: Use market orders for better execution
            quantity=qty,
            recvWindow=6000
        )
        logging.info(f"Order placed for {symbol} {side}: {resp1}")
        
        sleep(2)  # Security: Wait between orders
        
        # Set stop loss and take profit
        if side == 'buy':
            sl_price = round(price * (1 - sl), price_precision)
            tp_price = round(price * (1 + tp), price_precision)
            sl_side, tp_side = 'SELL', 'SELL'
        else:
            sl_price = round(price * (1 + sl), price_precision)
            tp_price = round(price * (1 - tp), price_precision)
            sl_side, tp_side = 'BUY', 'BUY'
        
        # Place stop loss
        resp2 = client.new_order(
            symbol=symbol, 
            side=sl_side, 
            type='STOP_MARKET', 
            quantity=qty, 
            stopPrice=sl_price,
            recvWindow=6000
        )
        logging.info(f"Stop loss set for {symbol}: {resp2}")
        
        sleep(2)
        
        # Place take profit
        resp3 = client.new_order(
            symbol=symbol, 
            side=tp_side, 
            type='TAKE_PROFIT_MARKET', 
            quantity=qty, 
            stopPrice=tp_price,
            recvWindow=6000
        )
        logging.info(f"Take profit set for {symbol}: {resp3}")
        
        return True
        
    except ClientError as error:
        logging.error(f"Order error for {symbol}: {error.status_code}, {error.error_code}, {error.error_message}")
        return False
    except Exception as e:
        logging.error(f"Unexpected order error for {symbol}: {str(e)}")
        return False

def get_pos():
    """Security: Enhanced position retrieval with validation"""
    rate_limit_check('get_pos')
    try:
        resp = client.get_position_risk()
        if not resp or not isinstance(resp, list):
            logging.error("Invalid position response format")
            return []
            
        pos = []
        for elem in resp:
            if abs(float(elem.get('positionAmt', 0))) > 0:
                symbol = elem.get('symbol', '')
                if validate_symbol(symbol):
                    pos.append(symbol)
        return pos
    except ClientError as error:
        logging.error(f"Position error: {error.status_code}, {error.error_code}, {error.error_message}")
        return []

def check_orders():
    """Security: Enhanced order checking with validation"""
    rate_limit_check('check_orders')
    try:
        response = client.get_open_orders(recvWindow=6000)
        if not response or not isinstance(response, list):
            return []
            
        sym = []
        for elem in response:
            symbol = elem.get('symbol', '')
            if validate_symbol(symbol):
                sym.append(symbol)
        return list(set(sym))  # Remove duplicates
    except ClientError as error:
        logging.error(f"Orders check error: {error.status_code}, {error.error_code}, {error.error_message}")
        return []

# Close open orders for the needed symbol. If one stop order is executed and another one is still there
def close_open_orders(symbol):
    """
    Cancel all open orders for a given symbol.

    Parameters:
    - symbol (str): The trading symbol for which to cancel open orders.

    Returns:
    - None

    Raises:
    - ClientError: If there is an error while canceling open orders.

    """
    try:
        response = client.cancel_open_orders(symbol=symbol, recvWindow=6000)
        logging.info(f"Open orders closed for {symbol}")
    except ClientError as error:
        logging.error(f"Close orders error for {symbol}: {error.status_code}, {error.error_code}, {error.error_message}")


# Strategy. Can use any other:
def str_signal(symbol):
    """
    Determines the trading signal based on the given symbol.

    Parameters:
    symbol (str): The symbol for which the trading signal is to be determined.

    Returns:
    str: The trading signal, which can be 'up', 'down', or 'none'.
    """
    kl = klines(symbol)
    rsi = ta.momentum.RSIIndicator(kl.Close).rsi()
    rsi_k = ta.momentum.StochRSIIndicator(kl.Close).stochrsi_k()
    rsi_d = ta.momentum.StochRSIIndicator(kl.Close).stochrsi_d()
    ema = ta.trend.ema_indicator(kl.Close, window=200)
    if rsi.iloc[-1] < 40 and ema.iloc[-1] < kl.Close.iloc[-1] and rsi_k.iloc[-1] < 20 and rsi_k.iloc[-3] < rsi_d.iloc[-3] and rsi_k.iloc[-2] < rsi_d.iloc[-2] and rsi_k.iloc[-1] > rsi_d.iloc[-1]:
        return 'up'
    if rsi.iloc[-1] > 60 and ema.iloc[-1] > kl.Close.iloc[-1] and rsi_k.iloc[-1] > 80 and rsi_k.iloc[-3] > rsi_d.iloc[-3] and rsi_k.iloc[-2] > rsi_d.iloc[-2] and rsi_k.iloc[-1] < rsi_d.iloc[-1]:
        return 'down'

    else:
        return 'none'


def rsi_signal(symbol):
    """
    Calculates the RSI signal for a given symbol.

    Parameters:
    symbol (str): The symbol for which to calculate the RSI signal.

    Returns:
    str: The RSI signal, which can be 'up', 'down', or 'none'.
    """
    kl = klines(symbol)
    rsi = ta.momentum.RSIIndicator(kl.Close).rsi()
    ema = ta.trend.ema_indicator(kl.Close, window=200)
    if rsi.iloc[-2] < 30 and rsi.iloc[-1] > 30:
        return 'up'
    if rsi.iloc[-2] > 70 and rsi.iloc[-1] < 70:
        return 'down'
    else:
        return 'none'


def macd_ema(symbol):
    """
    Calculates the MACD (Moving Average Convergence Divergence) and EMA (Exponential Moving Average) indicators for a given symbol.

    Parameters:
    symbol (str): The symbol for which to calculate the indicators.

    Returns:
    str: The signal indicating the trend based on the MACD and EMA indicators. Possible values are 'up', 'down', or 'none'.
    """
    kl = klines(symbol)
    macd = ta.trend.macd_diff(kl.Close)
    ema = ta.trend.ema_indicator(kl.Close, window=200)
    if macd.iloc[-3] < 0 and macd.iloc[-2] < 0 and macd.iloc[-1] > 0 and ema.iloc[-1] < kl.Close.iloc[-1]:
        return 'up'
    if macd.iloc[-3] > 0 and macd.iloc[-2] > 0 and macd.iloc[-1] < 0 and ema.iloc[-1] > kl.Close.iloc[-1]:
        return 'down'
    else:
        return 'none'


def ema200_50(symbol):
    """
    Calculates the EMA (Exponential Moving Average) for a given symbol and determines the trend based on the relationship between the EMA200 and EMA50.

    Parameters:
    - symbol (str): The symbol for which the EMA is calculated.

    Returns:
    - str: The trend based on the relationship between EMA200 and EMA50. Possible values are 'up', 'down', or 'none'.
    """
    kl = klines(symbol)
    ema200 = ta.trend.ema_indicator(kl.Close, window=100)
    ema50 = ta.trend.ema_indicator(kl.Close, window=50)
    if ema50.iloc[-3] < ema200.iloc[-3] and ema50.iloc[-2] < ema200.iloc[-2] and ema50.iloc[-1] > ema200.iloc[-1]:
        return 'up'
    if ema50.iloc[-3] > ema200.iloc[-3] and ema50.iloc[-2] > ema200.iloc[-2] and ema50.iloc[-1] < ema200.iloc[-1]:
        return 'down'
    else:
        return 'none'


orders = 0
symbol = ''
consecutive_errors = 0
MAX_CONSECUTIVE_ERRORS = 5

def validate_connection():
    """Security: Validate connection to Binance API"""
    try:
        client.ping()
        logging.info("Connection to Binance API successful.")
        return True
    except Exception as e:
        logging.error(f"Connection to Binance API failed: {e}")
        return False

# Security: Validate connection before starting
if not validate_connection():
    logging.error("Connection validation failed. Exiting.")
    exit(1)

symbols = get_tickers_usdt()
if not symbols:
    logging.error("No symbols retrieved. Exiting.")
    exit(1)

logging.info("Trading bot started with enhanced security features")

while True:
    try:
        balance = get_balance_usdt()
        sleep(1)
        
        if balance is None:
            consecutive_errors += 1
            logging.warning(f'Connection issue. Error count: {consecutive_errors}')
            
            # Security: Exit if too many consecutive errors
            if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                logging.error("Too many consecutive errors. Exiting for safety.")
                break
                
            sleep(30)  # Wait longer on connection issues
            continue
        else:
            consecutive_errors = 0  # Reset error counter
            
        # Security: Validate minimum balance
        if balance < 10:  # Minimum 10 USDT
            logging.warning(f"Balance too low: {balance} USDT. Stopping trading.")
            sleep(300)  # Wait 5 minutes
            continue
            
        logging.info(f"Balance: {balance} USDT")
        
        pos = get_pos()
        logging.info(f'Open positions ({len(pos)}): {pos}')
        
        ord = check_orders()
        
        # Clean up orphaned orders
        for elem in ord:
            if elem not in pos:
                close_open_orders(elem)
                sleep(1)

        # Security: Limit concurrent positions
        if len(pos) < min(qty, 10):  # Max 10 positions for safety
            for elem in symbols[:50]:  # Security: Limit symbol processing
                if len(pos) >= qty:  # Check again in case positions increased
                    break
                    
                try:
                    signal = rsi_signal(elem)
                    
                    if signal in ['up', 'down'] and elem not in pos and elem not in ord and elem != symbol:
                        logging.info(f'Signal found: {signal} for {elem}')
                        
                        if set_mode(elem, type) and set_leverage(elem, leverage):
                            sleep(1)
                            
                            order_side = 'buy' if signal == 'up' else 'sell'
                            if open_order(elem, order_side):
                                symbol = elem
                                pos = get_pos()
                                ord = check_orders()
                                sleep(10)  # Cool down after successful order
                                break  # Only one order per cycle
                                
                except Exception as e:
                    logging.error(f"Error processing {elem}: {str(e)}")
                    continue
        
        logging.info('Cycle completed. Waiting 3 minutes...')
        sleep(180)
        
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
        break
    except Exception as e:
        logging.error(f"Unexpected error in main loop: {str(e)}")
        consecutive_errors += 1
        if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
            logging.error("Too many errors. Exiting.")
            break
        sleep(60)

logging.info("Trading bot stopped")


