from app.models.instrument_universe import INSTRUMENTS
for i, inst in enumerate(INSTRUMENTS[22:35]):
    print(f"{i+23}: {inst['name']} ({inst['yahoo']})")
