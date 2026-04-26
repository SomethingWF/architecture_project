from prometheus_client import Counter, Histogram

USERS_CREATED_TOTAL = Counter(
    "users_new_total",
    "Total number of created users"
)

API_REQUEST_DURATION = Histogram(
    "api_user_request_duration_seconds",
    "Duration of user API requests",
    ["method", "endpoint"]
)