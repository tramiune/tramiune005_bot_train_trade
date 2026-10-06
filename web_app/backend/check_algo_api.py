import ccxt
ex = ccxt.binance()
methods = [m for m in dir(ex) if 'algo' in m.lower() and not m.startswith('_')]
print("Algo methods:", methods)
