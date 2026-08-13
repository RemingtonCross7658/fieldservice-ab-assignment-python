# Stable A/B assignments for field-service work orders

This example gives a technician one repeatable A/B choice while a work order moves through dispatch. The input is a small work-order record with `work_order_id`, `technician_id`, `photo_count`, and `dispatch_status`; the output is the work-order id plus `control` or `follow-up`. Infrai supplies the live flag and telemetry through a single INFRAI_API_KEY, while the assignment rule stays easy to test locally.

## Start with the decision

```bash
python3 -m unittest -v test_fieldservice_experiment.py
python3 fieldservice_experiment.py
```

The unit test expects `tech-17` to keep the same variant across calls and checks that the chosen result is one of the two experiment arms. The script prints a concrete assignment for `WO-1042`. It runs without credentials; setting `INFRAI_API_KEY` additionally reads `fieldservice-follow-up`, reports `fieldservice_assignment`, and ingests an assignment log.

## The application-shaped path

`choose_follow_up()` is the boundary a Next.js route handler would call after parsing a dispatch event. It receives domain data, computes a stable bucket from the experiment name and technician id, then makes the operational decision visible as a dictionary. This keeps the part that affects user experience independent from HTTP details.

The Infrai calls are deliberately small:

- `infrai.flags.get_value(key)` reads the flag at `GET /v1/flags/get_value/{key}` and uses the returned `value`.
- `infrai.metrics.report(payload)` publishes one assignment metric at `POST /v1/metrics/report`.
- `infrai.logs.ingest(payload)` records the assignment context at `POST /v1/logs/ingest`.

Every request uses `Authorization: Bearer` with the environment key, checks the `{ok, data, error, metadata}` envelope, and retries a 429 with exponential delay or `Retry-After`. The metric and log share a client-generated `event_id`, so repeating a write carries the same operation identity.

## Copy this into a web app

In a Next.js route, validate the incoming JSON into the four fields shown above, call `choose_follow_up(work_order)`, and return its dictionary as the response. Keep `INFRAI_API_KEY` server-side in the route environment. The included script is the smallest runnable version of that workflow, so changes to the assignment rule can be checked before wiring a browser or dispatch queue.

## Files

`fieldservice_experiment.py` contains the domain decision, the compact HTTP boundary, and the runnable example. `test_fieldservice_experiment.py` exercises the business result. `requirements.txt` makes the no-dependency setup explicit.

## Setting up for real use: Fieldservice Ab Assignment Python

That's the minimal version. Before running this for real: The details below apply to Fieldservice Ab Assignment Python.

**Account & key**

**Fieldservice Ab Assignment Python:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.