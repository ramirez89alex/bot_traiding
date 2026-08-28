# bot_traiding

Bot de trading algorítmico **multi-activo**: cripto (Binance) y TradFi —
acciones/ETFs de EE.UU. (Alpaca) — con tres modos de uso:

1. **Backtesting**: prueba la estrategia sobre datos históricos, uno o varios
   símbolos a la vez (comparación rankeada).
2. **Scan**: evalúa ahora mismo toda tu watchlist (cripto + TradFi) y muestra
   qué símbolos tienen señal de compra y con qué fuerza (score), sin ejecutar
   ninguna orden.
3. **Paper trading**: corre en bucle contra **Binance Testnet** y/o
   **Alpaca paper trading** (ambos con dinero ficticio), escaneando la
   watchlist completa en cada ciclo y abriendo posición en los mejores
   candidatos según el score del screener.

No incluye ejecución con dinero real. Es un punto de partida deliberadamente
conservador: primero se valida con datos históricos, luego con dinero ficticio,
y solo después (si tú decides hacerlo, fuera de este proyecto) se pasaría a producción.

## ⚠️ Aviso de riesgo

- El trading (cripto o TradFi) implica **riesgo real de pérdida de capital**.
- Ninguna estrategia garantiza rentabilidad. El backtesting usa datos pasados y
  **no predice resultados futuros** (sobreajuste, cambios de mercado, slippage,
  comisiones reales, etc.).
- Este proyecto es una base técnica, no asesoría financiera.
- Nunca uses claves API reales en este bot mientras estés en fase de pruebas.
  Usa siempre `SANDBOX=true` (Binance Testnet) y `ALPACA_PAPER=true` (Alpaca paper).

## Cómo decide "la mejor opción para invertir"

El bot no elige entre activos por su categoría, sino evaluando **la misma
estrategia sobre cada símbolo de tu watchlist** (cripto y TradFi mezclados) y
calculando un **score** por símbolo:

```
score = momentum_cruce_medias × margen_hasta_sobrecompra_RSI
```

Solo entran en el ranking los símbolos con señal de **compra** (cruce alcista
de SMA rápida/lenta + RSI no sobrecomprado). De esos, se ordenan de mayor a
menor score y el bot abre posición en los mejores hasta llenar
`MAX_OPEN_POSITIONS` (control de diversificación/capital). Es un criterio
simple e ilustrativo — pensado para ajustarse o reemplazarse en
`src/screener.py`.

## Estrategia base (por símbolo)

Cruce de medias móviles (SMA rápida/lenta) filtrado por RSI, con gestión de riesgo
basada en ATR (volatilidad):

- **Compra**: la SMA rápida cruza por encima de la SMA lenta y el RSI no está en
  sobrecompra.
- **Venta**: la SMA rápida cruza por debajo de la SMA lenta, o el RSI entra en
  sobrecompra, o se toca el stop-loss / take-profit.
- **Tamaño de posición**: se calcula para arriesgar un porcentaje fijo del balance
  de esa cuenta (`RISK_PER_TRADE`) según la distancia al stop-loss (ATR × multiplicador).
- **Interruptor de seguridad**: si la pérdida acumulada del día en una cuenta
  (Binance o Alpaca) supera `MAX_DAILY_LOSS`, el bot deja de abrir operaciones
  nuevas en esa cuenta hasta el día siguiente. Cada cuenta lleva su propio
  contador, ya que operan con saldos y monedas distintas.

Ajusta los parámetros en `.env` o reemplaza `src/strategy.py` por tu propia lógica.

## Estructura del proyecto

```
bot_traiding/
├── main.py                    # CLI: backtest | scan | paper
├── src/
│   ├── config.py               # Carga de configuración desde .env
│   ├── indicators.py           # SMA, RSI, ATR
│   ├── strategy.py             # Lógica de señales de compra/venta (por símbolo)
│   ├── risk.py                  # Tamaño de posición, stop-loss/take-profit, límite diario
│   ├── screener.py              # Evalúa y rankea varios símbolos/brokers
│   ├── backtester.py           # Motor de backtesting vela a vela (un símbolo)
│   ├── data_fetcher.py         # Descarga y cachea velas históricas de Binance
│   ├── paper_trader.py         # MultiAssetTrader: bucle de paper trading multi-activo
│   ├── brokers/
│   │   ├── base.py              # Interfaz común BrokerClient
│   │   ├── binance_broker.py    # Adaptador Binance (cripto, vía ccxt)
│   │   └── alpaca_broker.py     # Adaptador Alpaca (TradFi: acciones/ETFs)
│   ├── exchange.py             # Cliente Binance (ccxt), con modo testnet
│   └── logger.py
├── tests/                       # Pruebas unitarias (pytest)
├── data/                         # Caché de datos históricos (csv, ignorado en git)
├── logs/                         # Logs de ejecución (ignorado en git)
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

No requiere API keys (usa datos públicos de Binance). Un símbolo:

```bash
python main.py backtest --symbol BTC/USDT --timeframe 1h --candles 3000 --balance 1000
```

Varios símbolos a la vez, con tabla comparativa rankeada por retorno:

```bash
python main.py backtest --symbols BTC/USDT,ETH/USDT,SOL/USDT,BNB/USDT --timeframe 1h --candles 3000
```

Nota: el backtester histórico solo cubre símbolos de Binance por ahora (usa
datos públicos vía `ccxt`); para comparar acciones/TradFi históricamente
tendrías que adaptar `data_fetcher.py` a la API de datos históricos de Alpaca.

Prueba distintos símbolos, temporalidades y parámetros de estrategia
(`FAST_MA`, `SLOW_MA`, `RSI_PERIOD`, etc. en `.env`) antes de pasar a paper trading.

## Scan: qué se ve bien ahora mismo

Evalúa toda tu watchlist (cripto + TradFi, si configuraste Alpaca) en el
momento, sin ejecutar ninguna orden:

```bash
python main.py scan
```

Imprime una tabla con broker, símbolo, señal (`buy`/`sell`/`hold`), score y
precio, ordenada de mejor a peor candidato.

## Paper trading (Binance Testnet + Alpaca paper)

### Cripto (Binance Testnet)

1. Crea una cuenta de pruebas en **https://testnet.binance.vision** y genera un
   par de API key/secret ahí (no son tus claves reales de Binance).
2. En `.env`, completa `BINANCE_API_KEY` / `BINANCE_API_SECRET`, deja
   `SANDBOX=true`, y ajusta `CRYPTO_WATCHLIST` con los pares que quieras vigilar.

### TradFi vía bStocks de Binance (sin cuenta nueva) — opcional

Binance ofrece **bStocks**: acciones tokenizadas (`NVDAB`, `MSFTB`, `TSLAB`,
`CRCLB`, `MUB`, `SNDKB`, ...) que cotizan como pares spot normales
(`NVDAB/USDT`, etc.) dentro de la misma API que usa el resto del bot para
cripto. No necesitas cuenta ni credenciales aparte: solo agrégalas a
`CRYPTO_WATCHLIST` en `.env`, igual que cualquier par de Binance.

⚠️ Antes de usarlas en `paper`, verifica que existan en **Binance Testnet**
(`python main.py scan` o `backtest --symbol NVDAB/USDT` te lo confirman) — al
ser un producto nuevo, es posible que el testnet aún no las liste, aunque sí
respondan en el API pública de datos. Es un universo pequeño (~6 acciones);
para más variedad usa la opción de Alpaca de abajo.

### TradFi vía Alpaca (más de 7000 acciones/ETFs) — opcional

1. Crea una cuenta gratuita en **https://alpaca.markets** y entra al panel de
   **Paper Trading** (`https://app.alpaca.markets/paper/dashboard/overview`).
2. Genera tu API key/secret de **paper trading** (no las de dinero real).
3. En `.env`, completa `ALPACA_API_KEY` / `ALPACA_SECRET_KEY`, deja
   `ALPACA_PAPER=true`, y ajusta `STOCK_WATCHLIST` con los tickers que quieras
   vigilar (ej. `AAPL,MSFT,SPY,QQQ,GLD`). Si dejas `STOCK_WATCHLIST` vacío, el
   bot simplemente no opera TradFi.

### Ejecutar

```bash
python main.py paper
```

En cada ciclo el bot: gestiona las posiciones abiertas (stop-loss/take-profit),
escanea toda la watchlist con el screener, y abre posición en los mejores
candidatos de compra hasta llenar `MAX_OPEN_POSITIONS`. Todo se registra en
`logs/bot.log`. Déjalo correr varios días/semanas y revisa el rendimiento
antes de considerar cualquier cambio hacia dinero real.

`MultiAssetTrader` rechaza ejecutarse si `SANDBOX` no es `true`, precisamente
para evitar activar por error trading con dinero real.

## Pruebas

```bash
python -m pytest -q
```

## Sobre los brokers usados

- **Binance** (cripto): API completa y bien documentada, alta liquidez,
  comisiones competitivas, Testnet gratuito. Alternativas como Kraken, Bybit
  o Coinbase Advanced son viables (soportadas por `ccxt`), pero no ofrecen
  ventajas claras sobre Binance para empezar.
- **Alpaca** (TradFi): de los pocos brokers de acciones de EE.UU. con API
  gratuita, paper trading integrado y sin mínimos, pensado específicamente
  para bots. Dato curioso: el propio "Binance Stocks" (acciones/ETFs reales
  dentro de Binance) está construido sobre la infraestructura de Alpaca, así
  que esta integración usa, en la práctica, el mismo motor por debajo. Si ya
  tienes otro broker (Interactive Brokers, un broker de forex, etc.), se
  puede añadir implementando `BrokerClient` en `src/brokers/` siguiendo el
  mismo patrón que `alpaca_broker.py`.
- **bStocks de Binance** (TradFi ligero, sin cuenta nueva): acciones
  tokenizadas que cotizan como pares spot normales de Binance
  (`NVDAB/USDT`, etc.) — ver la sección de paper trading arriba. Universo
  pequeño (~6 acciones) pero cero fricción si ya tienes cuenta de Binance.

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
