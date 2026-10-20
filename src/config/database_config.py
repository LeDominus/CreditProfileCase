ALLOWED_TABLES = {
    "loan_products",
    "business_profiles",
    "conversations",
    "messages",
    "applications",
}

ALLOWED_ROLES = ("client", "bank_manager", "bank_analyst")

PBKDF2_ITERATIONS = 100_000