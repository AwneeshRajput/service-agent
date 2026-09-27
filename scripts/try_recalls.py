import asyncio
import json
import sys

from app.tools.recalls import check_recalls

make, model, year = sys.argv[1], sys.argv[2], int(sys.argv[3])
print(json.dumps(asyncio.run(check_recalls(make, model, year)), indent=2))
