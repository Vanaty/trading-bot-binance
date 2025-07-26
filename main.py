import logging
from time import sleep
from config import TradingConfig
from binance_client import binance_client
from notifications import notifier
from strategies import strategy_engine
from trading_manager import trading_manager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler()
    ]
)

def main():
    """Main trading bot loop"""
    consecutive_errors = 0
    
    # Validate connection
    if not binance_client.validate_connection():
        logging.error("Connection validation failed. Exiting.")
        notifier.notify_error("Connection validation failed", "Startup")
        return
    
    # Get symbols
    symbols = binance_client.get_tickers_usdt()
    if not symbols:
        logging.error("No symbols retrieved. Exiting.")
        notifier.notify_error("No symbols retrieved", "Startup")
        return
    
    logging.info("Trading bot started with enhanced multi-strategy system")
    
    # Send startup notification
    if TradingConfig.NOTIFY_ON_STARTUP:
        startup_details = f"Symbols: {len(symbols)}\nLeverage: {TradingConfig.LEVERAGE}x\nMax positions: {TradingConfig.MAX_POSITIONS}"
        notifier.notify_bot_status("Started", startup_details)
    
    while True:
        try:
            # Check balance
            balance = binance_client.get_balance_usdt()
            sleep(1)
            
            if balance is None:
                consecutive_errors += 1
                logging.warning(f'Connection issue. Error count: {consecutive_errors}')
                
                if consecutive_errors >= TradingConfig.MAX_CONSECUTIVE_ERRORS:
                    error_msg = "Too many consecutive errors. Exiting for safety."
                    logging.error(error_msg)
                    notifier.notify_error(error_msg, "Connection issues")
                    break
                    
                sleep(30)
                continue
            else:
                consecutive_errors = 0
            
            # Check minimum balance
            if balance < TradingConfig.MIN_BALANCE:
                logging.warning(f"Balance too low: {balance} USDT. Stopping trading.")
                notifier.notify_balance_low(balance)
                sleep(300)
                continue
            
            logging.info(f"Balance: {balance} USDT")
            
            # Get current positions
            positions = binance_client.get_positions()
            
            # Get open orders only for symbols that have positions
            open_orders = {}
            for symbol in positions:
                try:
                    orders = binance_client.get_open_orders(symbol)
                    if orders:
                        open_orders[symbol] = orders
                except Exception as e:
                    logging.warning(f"Error getting open orders for {symbol}: {str(e)}")
            
            logging.info(f'Open positions ({len(positions)}): {positions}')
            
            # Note: We can't clean up orphaned orders since we can't get all orders without symbols
            # This is a Binance API limitation
            
            # Look for new trading opportunities
            if len(positions) < min(TradingConfig.MAX_POSITIONS, 10):
                for symbol in symbols[:50]:  # Limit symbol processing
                    if len(positions) >= TradingConfig.MAX_POSITIONS:
                        break
                    try:
                        # Get enhanced signal
                        signal_data = strategy_engine.get_best_strategy_signal(symbol)
                        signal = signal_data.get('signal')
                        
                        if signal in ['buy', 'sell'] and symbol not in positions and symbol not in open_orders:
                            logging.info(f'Enhanced signal found: {signal} for {symbol}')
                            
                            # Get current price for notification
                            try:
                                price_data = binance_client.client.ticker_price(symbol)
                                current_price = float(price_data['price']) if price_data else None
                            except:
                                current_price = None
                            
                            # Send signal notification
                            notifier.notify_trade_signal(
                                symbol, signal, 'Enhanced Multi-Indicator', 
                                current_price, signal_data
                            )
                            
                            # Set leverage and margin type
                            if (binance_client.set_margin_type(symbol, TradingConfig.MARGIN_TYPE) and 
                                binance_client.set_leverage(symbol, TradingConfig.LEVERAGE)):
                                sleep(1)
                                
                                # Place order
                                if trading_manager.open_order(symbol, signal):
                                    trading_manager.last_symbol = symbol
                                    positions = binance_client.get_positions()
                                    # Update open_orders after placing new order
                                    if symbol in positions:
                                        try:
                                            orders = binance_client.get_open_orders(symbol)
                                            if orders:
                                                open_orders[symbol] = orders
                                        except:
                                            pass
                                    sleep(10)  # Cool down
                                    break  # Only one order per cycle
                    
                    except Exception as e:
                        error_msg = f"Error processing {symbol}: {str(e)}"
                        logging.error(error_msg)
                        notifier.notify_error(error_msg, f"Processing {symbol}")
                        continue
            
            logging.info('Cycle completed. Waiting 3 minutes...')
            sleep(180)
            
        except KeyboardInterrupt:
            logging.info("Bot stopped by user")
            notifier.notify_bot_status("Stopped", "Stopped by user")
            break
        except Exception as e:
            error_msg = f"Unexpected error in main loop: {str(e)}"
            logging.error(error_msg)
            notifier.notify_error(error_msg, "Main loop")
            consecutive_errors += 1
            if consecutive_errors >= TradingConfig.MAX_CONSECUTIVE_ERRORS:
                logging.error("Too many errors. Exiting.")
                notifier.notify_bot_status("Stopped", "Too many errors")
                break
            sleep(60)
    
    logging.info("Trading bot stopped")
    notifier.notify_bot_status("Stopped", "Normal shutdown")

if __name__ == "__main__":
    main()


