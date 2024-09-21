# CryptoExchange

Service for getting quotes for cryptocurrency exchange.

Support providers:
- binance
- kucoin

# Run

``docker-compose up app``

Tests

``docker-compose run test``

# Examples

POST `http://0.0.0.0:8080/api/v1/convert`

```
{
    "currency_from": "USDT",
    "currency_to": "BTC",
    "exchange": "binance",
    "amount": 10000,
    "cache_max_seconds": 10
}
```

Response:

```
{
    "currency_from": "USDT",
    "currency_to": "BTC",
    "exchange": "binance",
    "rate": "0.00001580",
    "result": "0.15803193",
    "updated_at": 1726941401
}
```
