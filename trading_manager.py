import logging
from time import sleep
from config import TradingConfig
from binance_client import binance_client
from notifications import notifier

class TradingManager:
    """Handle order placement and position management"""
    
    def __init__(self):
        self.last_symbol = ''
    
    def open_order(self, symbol, side):
        """Enhanced order placement with validation"""
        if not binance_client.validate_symbol(symbol) or side not in ['buy', 'sell']:
            logging.error(f"Invalid order parameters: {symbol}, {side}")
            return False
        
        try:
            # Get current price
            price_data = binance_client.client.ticker_price(symbol)
            if not price_data or 'price' not in price_data:
                logging.error(f"Could not get price for {symbol}")
                notifier.notify_error(f"Could not get price for {symbol}", "Order placement")
                return False
            
            price = float(price_data['price'])
            if price <= 0:
                logging.error(f"Invalid price for {symbol}: {price}")
                return False
            
            # Get precision
            qty_precision = binance_client.get_qty_precision(symbol)
            price_precision = binance_client.get_price_precision(symbol)
            
            if qty_precision is None or price_precision is None:
                logging.error(f"Could not get precision for {symbol}")
                return False
            
            # Calculate quantity
            calculated_qty = TradingConfig.VOLUME / price
            qty = round(calculated_qty, qty_precision)
            
            # Validate order size
            if qty <= 0 or calculated_qty * price < 5:
                logging.error(f"Order size too small for {symbol}: {qty}")
                return False
            
            # Validate against balance
            balance = binance_client.get_balance_usdt()
            if balance and calculated_qty * price > balance * 0.1:
                logging.error(f"Order size too large for {symbol}")
                notifier.notify_error(f"Order size too large for {symbol}", "Risk management")
                return False
            
            # Place main order
            order_side = 'BUY' if side == 'buy' else 'SELL'
            resp1 = binance_client.place_order(symbol, order_side, qty)
            
            if not resp1:
                return False
            
            logging.info(f"Order placed for {symbol} {side}: {resp1}")
            notifier.notify_order_placed(symbol, side, qty, price)
            
            sleep(2)
            
            # Set stop loss and take profit
            if side == 'buy':
                sl_price = round(price * (1 - TradingConfig.STOP_LOSS), price_precision)
                tp_price = round(price * (1 + TradingConfig.TAKE_PROFIT), price_precision)
                sl_side, tp_side = 'SELL', 'SELL'
            else:
                sl_price = round(price * (1 + TradingConfig.STOP_LOSS), price_precision)
                tp_price = round(price * (1 - TradingConfig.TAKE_PROFIT), price_precision)
                sl_side, tp_side = 'BUY', 'BUY'
            
            # Place stop loss
            resp2 = binance_client.place_order(
                symbol, sl_side, qty, 'STOP_MARKET', stop_price=sl_price
            )
            if resp2:
                logging.info(f"Stop loss set for {symbol}: {resp2}")
            
            sleep(2)
            
            # Place take profit
            resp3 = binance_client.place_order(
                symbol, tp_side, qty, 'TAKE_PROFIT_MARKET', stop_price=tp_price
            )
            if resp3:
                logging.info(f"Take profit set for {symbol}: {resp3}")
            
            return True
            
        except Exception as e:
            error_msg = f"Unexpected order error for {symbol}: {str(e)}"
            logging.error(error_msg)
            notifier.notify_error(error_msg, "Order placement")
            return False

# Global trading manager instance
trading_manager = TradingManager()
