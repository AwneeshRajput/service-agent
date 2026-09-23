---
title: Engine Warning Light and Diagnostics
doc_id: engine-warning-light
category: ENG
service_codes: [DIA, SPK, FIC, EXH]
updated: 2026-09-01
---

# Engine Warning Light and Diagnostics

Internal reference for service advisors.

## Steady light or flashing light

This is the first question to ask, and it changes the answer completely.

- **Steady amber.** A fault is stored. The car is usually drivable. Book a diagnostic
  in the next few days.
- **Flashing.** Active misfire. Unburnt fuel is passing into the exhaust and can destroy
  the catalytic converter within minutes. Tell the customer to stop driving, and offer
  the earliest slot.
- **Red warning of any kind**, especially oil pressure or temperature, means stop now.
  See [oil-change.md](oil-change.md).

## What the light does not mean

It is not a severity gauge. A loose fuel cap and a failing catalytic converter light
the same lamp. This is why we never quote a repair over the phone from the light alone.

## Common fault families

| Area | Typical cause |
|---|---|
| Misfire on one cylinder | Worn spark plug, failing coil, injector |
| Running lean across the bank | Air leak after the airflow sensor, weak fuel pump |
| Evaporative emissions | Fuel cap not sealing, perished purge valve hose |
| Catalyst efficiency below threshold | Often an upstream misfire that was ignored, not the catalyst itself |
| Airflow or pressure sensor implausible | Dirty sensor, split intake hose |

The pattern worth remembering: a cheap ignored fault becomes an expensive one. A coil
left misfiring for months takes the catalytic converter with it.

## The jobs

- **DIA — diagnostic scan, 45 min.** Read codes plus the freeze frame data showing
  conditions when the fault occurred, then live data to confirm. We do not clear codes
  and hand the car back; that only hides the fault until the customer has left.
- **SPK — spark plugs, 60 min.** Replaced as a full set.
- **FIC — injector cleaning, 90 min.** For rough idle and hesitation with no failed part.
- **EXH — exhaust repair, 120 min.** For blowing joints and corroded sections.

## What to tell customers about "limp mode"

Reduced power with the light on is the engine protecting itself. It is not a breakdown,
but it is not something to live with either. The car can usually be driven gently to us.

## Electric vehicles

EVs have no engine warning light in this sense. Their equivalent warnings relate to the
drive system or battery and are covered in [ev-high-voltage.md](ev-high-voltage.md).

## Escalation

Internal engine faults — timing chain rattle, low compression, coolant in the oil — are
beyond what we take on. Run the diagnostic, document the findings, and refer.
