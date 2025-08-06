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
            # Get current price using new method
            price = binance_client.get_current_price(symbol)
            if not price or price <= 0:
                logging.error(f"Could not get price for {symbol}")
                notifier.notify_error(f"Could not get price for {symbol}", "Order placement")
                return False
            
            logging.info(f"Current price for {symbol}: {price}")
            
            # Get precision
            qty_precision = binance_client.get_qty_precision(symbol)
            price_precision = binance_client.get_price_precision(symbol)
            
            if qty_precision is None or price_precision is None:
                logging.error(f"Could not get precision for {symbol}")
                return False
            
            # Calculate quantity with better validation
            calculated_qty = TradingConfig.VOLUME / price
            qty = round(calculated_qty, qty_precision)
            
            # More lenient order size validation
            min_notional = 5.0  # USDT
            order_value = qty * price
            
            if qty <= 0:
                logging.error(f"Invalid quantity for {symbol}: {qty}")
                return False
            
            if order_value < min_notional:
                # Adjust quantity to meet minimum
                qty = round(min_notional / price, qty_precision)
                order_value = qty * price
                logging.info(f"Adjusted quantity for {symbol} to meet minimum: {qty}")
            
            # Validate against balance (more lenient)
            balance = binance_client.get_balance_usdt()
            if balance and order_value > balance * 0.8:  # Use 80% instead of 10%
                logging.error(f"Order size too large for {symbol}: {order_value} > {balance * 0.8}")
                return False
            
            logging.info(f"Placing order: {symbol} {side} qty={qty} value={order_value:.2f} USDT")
            
            # Place main order
            order_side = 'BUY' if side == 'buy' else 'SELL'
            resp1 = binance_client.place_order(symbol, order_side, qty)
            
            if not resp1:
                return False
            
            logging.info(f"Order placed for {symbol} {side}: {resp1}")
            notifier.notify_order_placed(symbol, side, qty, price)
            
            sleep(2)
            
            # Set stop loss and take profit with better error handling
            try:
                # Ensure take_profit covers fees and is profitable
                effective_take_profit = max(
                    TradingConfig.TAKE_PROFIT, 
                    TradingConfig.STOP_LOSS + TradingConfig.BINANCE_FEE + 0.001 # min profit
                )

                if side == 'buy':
                    sl_price = round(price * (1 - TradingConfig.STOP_LOSS), price_precision)
                    tp_price = round(price * (1 + effective_take_profit), price_precision)
                    sl_side, tp_side = 'SELL', 'SELL'
                else:
                    sl_price = round(price * (1 + TradingConfig.STOP_LOSS), price_precision)
                    tp_price = round(price * (1 - effective_take_profit), price_precision)
                    sl_side, tp_side = 'BUY', 'BUY'
                
                # Place stop loss
                resp2 = binance_client.place_order(
                    symbol, sl_side, qty, 'STOP_MARKET', stop_price=sl_price
                )
                if resp2:
                    logging.info(f"Stop loss set for {symbol}: {resp2}")
                else:
                    logging.warning(f"Failed to set stop loss for {symbol}")
                
                sleep(2)
                
                # Place take profit
                resp3 = binance_client.place_order(
                    symbol, tp_side, qty, 'TAKE_PROFIT_MARKET', stop_price=tp_price
                )
                if resp3:
                    logging.info(f"Take profit set for {symbol}: {resp3}")
                else:
                    logging.warning(f"Failed to set take profit for {symbol}")
            
            except Exception as sl_tp_error:
                logging.warning(f"Error setting SL/TP for {symbol}: {str(sl_tp_error)}")
                # Continue anyway since main order was placed
            
            return True
            
        except Exception as e:
            error_msg = f"Unexpected order error for {symbol}: {str(e)}"
            logging.error(error_msg)
            notifier.notify_error(error_msg, "Order placement")
            return False

# Global trading manager instance
trading_manager = TradingManager()
