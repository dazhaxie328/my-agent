#!/usr/bin/env python3
"""
测试从Binance获取持仓量数据
"""
import requests
import json

def get_binance_futures_oi(symbol):
    """获取Binance期货持仓量"""
    url = f"https://fapi.binance.com/fapi/v1/openInterest"
    params = {"symbol": symbol}
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        return data
    except Exception as e:
        print(f"获取{symbol}持仓量失败: {e}")
        return None

def get_binance_futures_oi_history(symbol, period="1h", limit=30):
    """获取持仓量历史数据"""
    url = "https://fapi.binance.com/futures/data/openInterestHist"
    params = {
        "symbol": symbol,
        "period": period,
        "limit": limit
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        return data
    except Exception as e:
        print(f"获取{symbol}持仓量历史失败: {e}")
        return None

def get_binance_price(symbol):
    """获取当前价格"""
    url = "https://fapi.binance.com/fapi/v1/ticker/price"
    params = {"symbol": symbol}
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        return float(data["price"])
    except Exception as e:
        print(f"获取{symbol}价格失败: {e}")
        return None

def get_binance_price_change(symbol):
    """获取24小时价格变化"""
    url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
    params = {"symbol": symbol}
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        return {
            "price_change_percent": float(data["priceChangePercent"]),
            "last_price": float(data["lastPrice"]),
            "volume": float(data["volume"])
        }
    except Exception as e:
        print(f"获取{symbol}价格变化失败: {e}")
        return None

# 测试几个主流币种
test_symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"]

print("=== Binance期货持仓量测试 ===")
for symbol in test_symbols:
    print(f"\n{symbol}:")
    
    # 获取当前持仓量
    oi_data = get_binance_futures_oi(symbol)
    if oi_data:
        print(f"  当前持仓量: {oi_data.get('openInterest', 'N/A')}")
    
    # 获取价格变化
    price_data = get_binance_price_change(symbol)
    if price_data:
        print(f"  24h价格变化: {price_data['price_change_percent']}%")
        print(f"  当前价格: {price_data['last_price']}")
    
    # 获取持仓量历史
    oi_history = get_binance_futures_oi_history(symbol, "1h", 24)
    if oi_history and len(oi_history) >= 2:
        first_oi = float(oi_history[0]["sumOpenInterest"])
        last_oi = float(oi_history[-1]["sumOpenInterest"])
        oi_change = ((last_oi - first_oi) / first_oi) * 100
        print(f"  24h持仓量变化: {oi_change:.2f}%")