import logging
import apprise
from datetime import datetime,timezone,timedelta
from config import TradingConfig

class NotificationManager:
    """Handle all notifications for the trading bot"""
    
    def __init__(self):
        self.apobj = apprise.Apprise()
        
        # Add notification services
        for service in TradingConfig.NOTIFICATION_SERVICES:
            if service.strip():
                self.apobj.add(service.strip())
    
    def send_notification(self, title, message, notification_type='info'):
        """Send notification using Apprise with different types"""
        if not TradingConfig.NOTIFICATION_SERVICES:
            return
            
        try:
            # Add emoji and formatting based on type
            if notification_type == 'success':
                title = f"✅ {title}"
            elif notification_type == 'warning':
                title = f"⚠️ {title}"
            elif notification_type == 'error':
                title = f"❌ {title}"
            elif notification_type == 'trade':
                title = f"💰 {title}"
            elif notification_type == 'info':
                title = f"ℹ️ {title}"
                
            # Format message with timestamp
            tz = timezone.utc if TradingConfig.TIMEZONE == 'UTC' else timezone(timedelta(hours=int(TradingConfig.TIMEZONE.replace('UTC',''))))
            formatted_message = f"{message}\n\n🕐 {datetime.now(tz=tz).strftime('%Y-%m-%d %H:%M:%S')}"
            
            # Send notification
            self.apobj.notify(title=title, body=formatted_message)
            logging.info(f"Notification sent: {title}")
            
        except Exception as e:
            logging.error(f"Failed to send notification: {str(e)}")
    
    def notify_trade_signal(self, symbol, side, signal_type, price=None, strategy_info=None):
        """Send notification for trading signals"""
        if not TradingConfig.NOTIFY_ON_TRADES:
            return
            
        title = f"Trade Signal: {symbol}"
        direction = "🟢 BUY" if side == 'buy' else "🔴 SELL"
        price_info = f" at ${price:.4f}" if price else ""
        message = f"{direction} signal detected for {symbol}{price_info}\nStrategy: {signal_type}"
        
        if strategy_info:
            message += f"\nScore: {strategy_info.get('backtest_score', 'N/A'):.1f}"
            message += f"\nStrength: {strategy_info.get('strength', 'N/A')}"
            
        self.send_notification(title, message, 'trade')
    
    def notify_order_placed(self, symbol, side, quantity, price):
        """Send notification when order is placed"""
        if not TradingConfig.NOTIFY_ON_TRADES:
            return
            
        title = f"Order Placed: {symbol}"
        direction = "🟢 BUY" if side == 'buy' else "🔴 SELL"
        message = f"{direction} order placed\nSymbol: {symbol}\nQuantity: {quantity}\nPrice: ${price:.4f}"
        self.send_notification(title, message, 'success')
    
    def notify_position_closed(self, symbol, pnl=None):
        """Send notification when position is closed"""
        if not TradingConfig.NOTIFY_ON_TRADES:
            return
            
        title = f"Position Closed: {symbol}"
        pnl_text = f"\nP&L: {pnl:.2f} USDT" if pnl else ""
        message = f"Position closed for {symbol}{pnl_text}"
        notification_type = 'success' if pnl and pnl > 0 else 'warning'
        self.send_notification(title, message, notification_type)
    
    def notify_error(self, error_message, context=""):
        """Send notification for errors"""
        if not TradingConfig.NOTIFY_ON_ERRORS:
            return
            
        title = "Trading Bot Error"
        message = f"Error occurred: {error_message}"
        if context:
            message += f"\nContext: {context}"
        self.send_notification(title, message, 'error')
    
    def notify_balance_low(self, balance):
        """Send notification for low balance"""
        if not TradingConfig.NOTIFY_ON_BALANCE_LOW:
            return
            
        title = "Low Balance Warning"
        message = f"Balance is low: {balance:.2f} USDT\nTrading paused until balance increases."
        self.send_notification(title, message, 'warning')
    
    def notify_bot_status(self, status, details=""):
        """Send notification for bot status changes"""
        title = f"Trading Bot {status}"
        message = f"Bot status: {status}"
        if details:
            message += f"\n{details}"
        
        if status == "Started":
            notification_type = 'success'
        elif status == "Stopped":
            notification_type = 'warning'
        else:
            notification_type = 'info'
            
        self.send_notification(title, message, notification_type)

# Global notification manager instance
notifier = NotificationManager()
