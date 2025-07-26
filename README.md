# Bot de Trading Binance - Stratégies Avancées

Un bot de trading automatisé pour Binance Futures utilisant des stratégies techniques avancées avec indicateurs multiples, backtesting et gestion des risques.

## ⚠️ AVERTISSEMENT

**CE BOT UTILISE DE L'ARGENT RÉEL. VOUS POUVEZ PERDRE TOUT VOTRE CAPITAL.**
- Utilisez uniquement sur un compte de test au début
- Ne jamais risquer plus que ce que vous pouvez vous permettre de perdre
- Les performances passées ne garantissent pas les résultats futurs
- Surveillez constamment le bot pendant son fonctionnement

## 🚀 Fonctionnalités

### Stratégies de Trading
- **RSI + Bollinger Bands + VWAP** : Détection de surachat/survente avec confirmation de volume
- **MACD + EMA + Volume** : Signaux de croisement avec filtres de tendance
- **Stochastic + Fibonacci + Trend** : Analyse des retracements avec confirmation de tendance

### Gestion des Risques
- Stop-loss et take-profit automatiques
- Limitation du nombre de positions simultanées
- Validation de la taille des ordres
- Filtre de balance minimum

### Backtesting
- Test des stratégies sur données historiques
- Sélection automatique de la meilleure stratégie
- Métriques de performance détaillées

### Notifications
- Alertes en temps réel via Telegram, Discord, Email, Slack
- Notifications de signaux, ordres, erreurs
- Rapports de performance

## 📦 Installation

### Prérequis
- Python 3.8 ou supérieur
- Compte Binance avec API activée
- Fonds sur le compte Binance Futures

### Étapes d'installation

1. **Cloner le repository**
```bash
git clone https://github.com/votre-username/trading-bot-binance.git
cd trading-bot-binance
```

2. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

3. **Créer le fichier de configuration**
```bash
cp .env.example .env
```

## ⚙️ Configuration

### 1. Configuration de l'API Binance

Éditez le fichier `.env` :

```bash
# Clés API Binance (OBLIGATOIRE)
BINANCE_API_KEY=votre_cle_api_ici
BINANCE_SECRET_KEY=votre_cle_secrete_ici

# Paramètres de trading
LEVERAGE=10                    # Levier (1-125)
VOLUME=20                      # Volume par trade en USDT
TAKE_PROFIT=0.015             # Take profit (1.5%)
STOP_LOSS=0.010               # Stop loss (1.0%)
MAX_POSITIONS=3               # Nombre max de positions

# Stratégies
MIN_SIGNAL_STRENGTH=3         # Force minimum du signal (1-5)
MIN_BACKTEST_SCORE=60.0       # Score minimum de backtest
ENABLE_BACKTESTING=true       # Activer le backtesting

# Notifications
NOTIFY_ON_TRADES=true
NOTIFY_ON_ERRORS=true
```

### 2. Configuration des notifications (optionnel)

Pour recevoir des alertes, ajoutez vos services de notification :

```bash
# Telegram
APPRISE_SERVICES=tgram://BOT_TOKEN/CHAT_ID

# Discord
APPRISE_SERVICES=discord://WEBHOOK_ID/WEBHOOK_TOKEN

# Email
APPRISE_SERVICES=mailto://user:password@domain.com?to=recipient@domain.com

# Plusieurs services (séparés par des virgules)
APPRISE_SERVICES=tgram://BOT_TOKEN/CHAT_ID,discord://WEBHOOK_ID/WEBHOOK_TOKEN
```

### 3. Obtenir les clés API Binance

1. Connectez-vous à [Binance](https://www.binance.com)
2. Allez dans **Compte** → **Sécurité** → **Gestion API**
3. Créez une nouvelle clé API
4. **IMPORTANT** : Activez uniquement les permissions "Futures Trading"
5. Ajoutez votre IP à la liste blanche pour plus de sécurité

## 🏃‍♂️ Utilisation

### Démarrage du bot

```bash
python main.py
```

### Test sur compte démo

**FORTEMENT RECOMMANDÉ** : Testez d'abord sur Binance Testnet :

1. Créez un compte sur [Binance Testnet](https://testnet.binancefuture.com)
2. Obtenez les clés API de test
3. Modifiez `binance_client.py` pour pointer vers l'URL de test
4. Lancez le bot avec les clés de test

### Surveillance

Le bot génère plusieurs fichiers de logs :
- `trading_bot.log` : Log principal
- Console : Affichage en temps réel

Surveillez ces métriques :
- Balance USDT
- Nombre de positions ouvertes
- Performance des stratégies
- Erreurs d'API

## 📊 Stratégies Détaillées

### 1. RSI + Bollinger Bands + VWAP
- **Achat** : RSI < 30, prix près de la bande inférieure, prix au-dessus du VWAP
- **Vente** : RSI > 70, prix près de la bande supérieure, prix en-dessous du VWAP
- **Filtres** : Volume, tendance EMA200

### 2. MACD + EMA + Volume
- **Achat** : Croisement haussier MACD, EMA50 > EMA200
- **Vente** : Croisement baissier MACD, EMA50 < EMA200
- **Confirmation** : Volume élevé

### 3. Stochastic + Fibonacci + Trend
- **Achat** : Stochastic < 20 et rebond, prix près des niveaux Fibonacci
- **Vente** : Stochastic > 80 et retournement
- **Filtre** : Tendance EMA100

## 🛡️ Gestion des Risques

### Paramètres de sécurité
- **Stop-loss** : Limite les pertes par trade
- **Take-profit** : Sécurise les gains
- **Taille maximale** : Limite l'exposition par position
- **Balance minimum** : Arrête le trading si balance trop faible

### Recommandations
- Commencez avec un petit capital
- Utilisez un levier faible (2-5x max pour débuter)
- Surveillez quotidiennement
- Ajustez les paramètres selon les conditions de marché

## 📈 Analyse des performances

Le bot inclut un analyseur de performance :

```bash
python strategy_analyzer.py
```

Génère :
- Rapports de performance par stratégie
- Graphiques comparatifs
- Recommandations d'optimisation

## 🔧 Maintenance

### Mise à jour
```bash
git pull origin main
pip install -r requirements.txt
```

### Nettoyage des logs
```bash
# Nettoyer les anciens logs (plus de 7 jours)
find . -name "*.log" -mtime +7 -delete
```

### Sauvegarde
Sauvegardez régulièrement :
- Fichier `.env` (sans le partager)
- Logs de performance
- Configuration personnalisée

## 🆘 Dépannage

### Erreurs courantes

**"Connection validation failed"**
- Vérifiez les clés API
- Vérifiez la connexion internet
- Vérifiez que l'IP est autorisée

**"Invalid symbol"**
- Le symbole n'existe pas ou n'est pas actif
- Vérifiez la liste des paires disponibles

**"Insufficient balance"**
- Balance trop faible pour le trade
- Réduisez le volume ou ajoutez des fonds

**"Order placement failed"**
- Vérifiez les permissions API
- Vérifiez les paramètres de l'ordre
- Possible maintenance Binance

### Support

1. Vérifiez les logs en détail
2. Consultez la documentation Binance API
3. Testez sur le compte démo

## 📄 Licence

MIT License - Voir le fichier `LICENSE` pour plus de détails.

## ⚖️ Disclaimer

Ce bot est fourni à des fins éducatives uniquement. L'utilisation de ce bot pour le trading avec de l'argent réel est à vos propres risques. Les développeurs ne sont pas responsables des pertes financières.

**TRADEZ RESPONSABLEMENT ET NE RISQUEZ JAMAIS PLUS QUE CE QUE VOUS POUVEZ VOUS PERMETTRE DE PERDRE.**
