from utils.api_response import error, success

print(success(
    data={"client": "AA:BB:CC"},
    message="OK",
).model_dump_json(indent=2))

print()

print(error(
    message="Not Found",
    errors=["Client does not exist"],
).model_dump_json(indent=2))
