import httpx
from langfuse import observe

NHTSA_URL = "https://api.nhtsa.gov/recalls/recallsByVehicle"
MAX_RESULTS = 5
TIMEOUT_SECONDS = 10.0

def _trim(recall: dict) -> dict:
    return {
        "campaign_number": recall.get("NHTSACampaignNumber"),
        "reported": recall.get("ReportReceivedDate"),
        "component": recall.get("Component"),
        "summary": (recall.get("Summary") or "")[:400],
        "consequence": recall.get("Consequence"),
        "remedy": (recall.get("Remedy") or "")[:300],
        "park_it": recall.get("parkIt", False),
    }

@observe(name="check_recalls")
async def check_recalls(make: str, model: str, year: int) -> dict:
    result = {"make": make, "model": model, "year": year, "total": 0, "recalls": [], "error": None}
    params = {"make": make.strip(), "model": model.strip(), "modelYear": year}

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            response = await client.get(NHTSA_URL, params=params)
            response.raise_for_status()
            data = response.json()
    except httpx.TimeoutException:
        result["error"] = "NHTSA did not respond within 10 seconds"
        return result
    except (httpx.HTTPError, ValueError):
        result["error"] = "could not get a valid response from NHTSA"
        return result

    recalls = data.get("results", [])
    result["total"] = data.get("Count", len(recalls))
    result["recalls"] = [_trim(r) for r in recalls[:MAX_RESULTS]]
    return result
