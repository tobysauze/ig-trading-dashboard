from app.models.instrument_universe import INSTRUMENTS
for i, inst in enumerate(INSTRUMENTS[20:60]):
    print(f"{i+21}: {inst['name']} ({inst['yahoo']}) - {inst['market_type']}")
