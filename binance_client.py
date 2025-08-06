import logging
import pandas as pd
from datetime import datetime
from time import sleep
from binance.um_futures import UMFutures
from binance.error import ClientError
from config import TradingConfig
from notifications import notifier

class BinanceClient:
    """Enhanced Binance client with security and validation"""
    
    def __init__(self):
        self.client = UMFutures(key=TradingConfig.API_KEY, secret=TradingConfig.SECRET_KEY)
        self.last_api_call = {}
        
    def rate_limit_check(self, function_name):
        """Implement rate limiting for API calls"""
        current_time = datetime.now()
        if function_name in self.last_api_call:
            time_diff = (current_time - self.last_api_call[function_name]).total_seconds()
            if time_diff < TradingConfig.MIN_API_INTERVAL:
                sleep(TradingConfig.MIN_API_INTERVAL - time_diff)
        self.last_api_call[function_name] = datetime.now()
    
    def validate_symbol(self, symbol):
        """Validate symbol format"""
        if not isinstance(symbol, str) or len(symbol) < 6 or not symbol.endswith('USDT'):
            return False
        return True
    
    def validate_connection(self):
        """Validate connection to Binance API"""
        try:
            self.client.ping()
            logging.info("Connection to Binance API successful.")
            return True
        except Exception as e:
            logging.error(f"Connection to Binance API failed: {e}")
            return False
    
    def get_balance_usdt(self):
        """Get USDT balance with validation"""
        self.rate_limit_check('get_balance')
        try:
            # Try account info first (more reliable for futures)
            response = self.client.account(recvWindow=6000)
            if response and 'totalWalletBalance' in response:
                balance = float(response['totalWalletBalance'])
                logging.info(f"Account balance from totalWalletBalance: {balance}")
                return balance
            
            # Fallback to balance method
            response = self.client.balance(recvWindow=6000)
            if not response or not isinstance(response, list):
                logging.error("Invalid balance response format")
                return None
                
            for elem in response:
                if elem.get('asset') == 'USDT':
                    balance = float(elem.get('balance', 0))
                    if balance < 0 or balance > 1000000:
                        logging.warning(f"Unusual balance detected: {balance}")
                    return balance
            return 0.0

        except ClientError as error:
            logging.error(f"Balance error: {error.status_code}, {error.error_code}, {error.error_message}")
            return None
        except Exception as e:
            logging.error(f"Unexpected balance error: {str(e)}")
            return None
    
    def get_tickers_usdt(self):
        """Get USDT trading pairs with validation"""
        self.rate_limit_check('get_tickers')
        try:
            resp = self.client.ticker_price()
            if not resp or not isinstance(resp, list):
                logging.error("Invalid ticker response format")
                return []
                
            tickers = []
            for elem in resp:
                symbol = elem.get('symbol', '')
                if self.validate_symbol(symbol) and symbol not in ['USDCUSDT', 'BUSDUSDT']:
                    tickers.append(symbol)
            
            logging.info(f"Retrieved {len(tickers)} valid USDT pairs")
            return tickers[:200]
            
        except ClientError as error:
            logging.error(f"Ticker error: {error.status_code}, {error.error_code}, {error.error_message}")
            return []
    
    def get_klines(self, symbol, interval='15m', limit=200):
        """Get klines data with validation"""
        if not self.validate_symbol(symbol):
            logging.error(f"Invalid symbol: {symbol}")
            return None
            
        self.rate_limit_check('klines')
        try:
            resp = pd.DataFrame(self.client.klines(symbol, interval, limit=limit))
            if resp.empty or len(resp.columns) < 6:
                logging.error(f"Invalid klines data for {symbol}")
                return None
                
            resp = resp.iloc[:,:6]
            resp.columns = ['Time', 'Open', 'High', 'Low', 'Close', 'Volume']
            resp = resp.set_index('Time')
            resp.index = pd.to_datetime(resp.index, unit='ms')
            resp = resp.astype(float)
            
            if (resp <= 0).any().any():
                logging.error(f"Invalid price data detected for {symbol}")
                return None
                
            return resp
        except ClientError as error:
            logging.error(f"Klines error for {symbol}: {error.status_code}, {error.error_code}, {error.error_message}")
            return None
    
    def get_price_precision(self, symbol):
        """Get price precision for symbol"""
        try:
            resp = self.client.exchange_info()['symbols']
            for elem in resp:
                if elem['symbol'] == symbol:
                    return elem['pricePrecision']
        except Exception as e:
            logging.error(f"Error getting price precision for {symbol}: {e}")
            return None
    
    def get_qty_precision(self, symbol):
        """Get quantity precision for symbol"""
        try:
            resp = self.client.exchange_info()['symbols']
            for elem in resp:
                if elem['symbol'] == symbol:
                    return elem['quantityPrecision']
        except Exception as e:
            logging.error(f"Error getting qty precision for {symbol}: {e}")
            return None
    
    def set_leverage(self, symbol, level):
        """Set leverage with validation"""
        if not self.validate_symbol(symbol):
            return False
            
        level = max(1, min(125, int(level)))
        self.rate_limit_check('set_leverage')
        
        try:
            response = self.client.change_leverage(symbol=symbol, leverage=level, recvWindow=6000)
            logging.info(f"Leverage set for {symbol}: {level}x")
            return True
        except ClientError as error:
            logging.error(f"Leverage error for {symbol}: {error.status_code}, {error.error_code}, {error.error_message}")
            return False
    
    def set_margin_type(self, symbol, margin_type):
        """Set margin type with validation"""
        if not self.validate_symbol(symbol):
            return False
            
        if margin_type not in ['ISOLATED', 'CROSS']:
            margin_type = 'ISOLATED'
            
        self.rate_limit_check('set_mode')
        try:
            response = self.client.change_margin_type(symbol=symbol, marginType=margin_type, recvWindow=6000)
            logging.info(f"Margin type set for {symbol}: {margin_type}")
            return True
        except ClientError as error:
            if error.error_code != -4046:
                logging.error(f"Margin type error for {symbol}: {error.status_code}, {error.error_code}, {error.error_message}")
            return False
    
    def place_order(self, symbol, side, quantity, order_type='MARKET', price=None, stop_price=None):
        """Place order with enhanced validation"""
        if not self.validate_symbol(symbol) or side not in ['BUY', 'SELL']:
            logging.error(f"Invalid order parameters: {symbol}, {side}")
            return None
            
        self.rate_limit_check('place_order')
        try:
            order_params = {
                'symbol': symbol,
                'side': side,
                'type': order_type,
                'quantity': quantity,
                'recvWindow': 6000
            }
            
            if price:
                order_params['price'] = price
            if stop_price:
                order_params['stopPrice'] = stop_price

            response = self.client.new_order(**order_params)
            logging.info(f"Order placed: {response}")
            return response
            
        except ClientError as error:
            error_msg = f"Order error for {symbol}: {error.status_code}, {error.error_code}, {error.error_message}"
            logging.error(error_msg)
            notifier.notify_error(error_msg, "Order placement")
            return None
    
    def get_positions(self):
        """Get open positions with validation"""
        self.rate_limit_check('get_positions')
        try:
            resp = self.client.get_position_risk()
            
            # Debug logging to see actual response
            logging.debug(f"Position response type: {type(resp)}, length: {len(resp) if resp else 0}")
            
            if not resp:
                logging.warning("Empty position response")
                return []
            
            if not isinstance(resp, list):
                logging.error(f"Unexpected position response format: {type(resp)}")
                return []
                
            positions = []
            for elem in resp:
                try:
                    position_amt = float(elem.get('positionAmt', 0))
                    if abs(position_amt) > 0:
                        symbol = elem.get('symbol', '')
                        if self.validate_symbol(symbol):
                            positions.append(symbol)
                except (ValueError, TypeError) as e:
                    logging.warning(f"Error parsing position data: {e}, elem: {elem}")
                    continue
                    
            return positions
        except Exception as error:
            logging.error(f"Position error: {str(error)}")
            return []
    
    def get_open_orders(self, symbol=None):
        """Get open orders with validation - can get for specific symbol or all symbols"""
        self.rate_limit_check('get_orders')
        try:
            if symbol:
                if not self.validate_symbol(symbol):
                    return []
                response = self.client.get_orders(symbol=symbol, recvWindow=6000)
            else:
                response = self.client.get_orders(recvWindow=6000)

            if not response or not isinstance(response, list):
                return []
            return response
        except ClientError as error:
            # The API returns an error if there are no open orders for a specific symbol.
            if error.error_code == -4049: # No orders found for the symbol
                return []
            logging.error(f"Orders check error: {str(error)}")
            return []
        except Exception as error:
            logging.error(f"Orders check error: {str(error)}")
            return []
    def cancel_order(self, order_id):
        """Cancel specific order by ID"""
        self.rate_limit_check('cancel_order')
        try:
            response = self.client.cancel_order(orderId=order_id, recvWindow=6000)
            logging.info(f"Order cancelled: {response}")
            return response
        except ClientError as error:
            logging.error(f"Cancel order error: {error.status_code}, {error.error_code}, {error.error_message}")
            return None

    def cancel_open_orders(self, symbol, order_id=None):
        """Cancel open orders for symbol or specific order ID"""
        try:
            if not order_id:
                response = self.client.cancel_open_orders(symbol=symbol, recvWindow=6000)
            response = self.client.cancel_order(symbol=symbol, orderId=order_id)
            logging.info(f"Open orders closed for {symbol}")
            notifier.notify_position_closed(symbol)
        except ClientError as error:
            error_msg = f"Close orders error for {symbol}: {error.status_code}, {error.error_code}, {error.error_message}"
            logging.error(error_msg)
            notifier.notify_error(error_msg, "Close orders")

    def get_current_price(self, symbol):
        """Get current price with error handling"""
        if not self.validate_symbol(symbol):
            return None
        
        self.rate_limit_check('get_price')
        try:
            response = self.client.ticker_price(symbol)
            if response and 'price' in response:
                return float(response['price'])
            return None
        except ClientError as error:
            logging.error(f"Price error for {symbol}: {error.status_code}, {error.error_code}, {error.error_message}")
            return None
        except Exception as e:
            logging.error(f"Unexpected price error for {symbol}: {str(e)}")
            return None
    

# Global client instance
binance_client = BinanceClient()
