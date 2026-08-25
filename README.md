# bot_traiding

Bot de trading algorítmico para Binance (spot), con dos modos de uso:

1. **Backtesting**: prueba la estrategia sobre datos históricos.
2. **Paper trading**: ejecuta la estrategia en tiempo real contra **Binance Testnet**
   (dinero ficticio), usando la misma API que Binance real.

No incluye ejecución con dinero real. Es un punto de partida deliberadamente
conservador: primero se valida con datos históricos, luego con dinero ficticio,
y solo después (si tú decides hacerlo, fuera de este proyecto) se pasaría a producción.

## ⚠️ Aviso de riesgo

- El trading de criptomonedas implica **riesgo real de pérdida de capital**.
- Ninguna estrategia garantiza rentabilidad. El backtesting usa datos pasados y
  **no predice resultados futuros** (sobreajuste, cambios de mercado, slippage,
  comisiones reales, etc.).
- Este proyecto es una base técnica, no asesoría financiera.
- Nunca uses tus claves API reales de Binance en este bot mientras estés en fase
  de pruebas. Usa siempre `SANDBOX=true` con claves de **Binance Testnet**.

## Estrategia incluida

Cruce de medias móviles (SMA rápida/lenta) filtrado por RSI, con gestión de riesgo
basada en ATR (volatilidad):

- **Compra**: la SMA rápida cruza por encima de la SMA lenta y el RSI no está en
  sobrecompra.
- **Venta**: la SMA rápida cruza por debajo de la SMA lenta, o el RSI entra en
  sobrecompra, o se toca el stop-loss / take-profit.
- **Tamaño de posición**: se calcula para arriesgar un porcentaje fijo del balance
  (`RISK_PER_TRADE`) según la distancia al stop-loss (ATR × multiplicador).
- **Interruptor de seguridad**: si la pérdida acumulada del día supera
  `MAX_DAILY_LOSS`, el bot deja de abrir operaciones nuevas hasta el día siguiente.

Es una estrategia simple e ilustrativa, pensada para modificarse. Ajusta los
parámetros en `.env` o reemplaza `src/strategy.py` por tu propia lógica.

## Estructura del proyecto

```
bot_traiding/
├── main.py                # CLI: backtest | paper
├── src/
│   ├── config.py           # Carga de configuración desde .env
│   ├── indicators.py       # SMA, RSI, ATR
│   ├── strategy.py         # Lógica de señales de compra/venta
│   ├── risk.py              # Tamaño de posición, stop-loss/take-profit, límite diario
│   ├── backtester.py       # Motor de backtesting vela a vela
│   ├── data_fetcher.py     # Descarga y cachea velas históricas de Binance
│   ├── exchange.py         # Cliente Binance (ccxt), con modo testnet
│   ├── paper_trader.py     # Bucle de paper trading contra Binance Testnet
│   └── logger.py
├── tests/                   # Pruebas unitarias (pytest)
├── data/                     # Caché de datos históricos (csv, ignorado en git)
├── logs/                     # Logs de ejecución (ignorado en git)
├── .env.example
└── requirements.txt
```

## Instalación

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edita `.env` con tus parámetros. Los valores por defecto son razonables para empezar.

## Backtesting

No requiere API keys (usa datos públicos de Binance):

```bash
python main.py backtest --symbol BTC/USDT --timeframe 1h --candles 3000 --balance 1000
```

Esto descarga (o reutiliza si ya está en caché) velas históricas, corre la
estrategia y muestra métricas: retorno total, win rate, máximo drawdown,
profit factor y número de operaciones.

Prueba distintos símbolos, temporalidades y parámetros de estrategia
(`FAST_MA`, `SLOW_MA`, `RSI_PERIOD`, etc. en `.env`) antes de pasar a paper trading.

## Paper trading (Binance Testnet)

1. Crea una cuenta de pruebas en **https://testnet.binance.vision** y genera un
   par de API key/secret ahí (no son tus claves reales de Binance).
2. En `.env`, completa `BINANCE_API_KEY` y `BINANCE_API_SECRET` con esas claves
   de testnet, y deja `SANDBOX=true`.
3. Ejecuta:

```bash
python main.py paper
```

El bot consultará precios, calculará señales y enviará órdenes de mercado
**contra el entorno de pruebas de Binance** (dinero ficticio), registrando todo
en `logs/bot.log`. Déjalo correr varios días/semanas y revisa el rendimiento
antes de considerar cualquier cambio hacia dinero real.

`PaperTrader` rechaza ejecutarse si `SANDBOX` no es `true`, precisamente para
evitar activar por error trading con dinero real.

## Pruebas

```bash
python -m pytest -q
```

## Sobre Binance vs. otros brokers/exchanges

Binance es una opción sólida para este tipo de bot: API completa y bien
documentada, alta liquidez, comisiones competitivas, y un Testnet gratuito
para validar sin riesgo. Alternativas como Kraken, Bybit o Coinbase Advanced
son viables (todas soportadas por `ccxt` cambiando el exchange en
`src/exchange.py`), pero no ofrecen ventajas claras sobre Binance para
empezar.

## Si en el futuro decides operar con dinero real

Este proyecto lo deja fuera de alcance intencionalmente. Si algún día decides
avanzar a trading en vivo, como mínimo:

- Corre el bot en paper trading por un período largo y revisa que el
  rendimiento sea consistente con el backtest.
- Empieza con capital que puedas permitirte perder por completo.
- Añade monitoreo/alertas (ej. Telegram) y un límite de pérdida diaria más
  conservador.
- Revisa a fondo el manejo de errores de red/API (reconexiones, órdenes
  duplicadas, desincronización de balance).
