ALLOWED_TABLES = {
    "loan_products",
    "business_profiles",
    "conversations",
    "messages",
    "applications",
}

ROLE_CLIENT = "client"
ROLE_BANK_MANAGER = "bank_manager"
ROLE_BANK_ANALYST = "bank_analyst"
ROLE_SYSTEM = "system"

BANK_ROLES = (ROLE_BANK_MANAGER, ROLE_BANK_ANALYST)

ALLOWED_ROLES = (ROLE_CLIENT, *BANK_ROLES)

PBKDF2_ITERATIONS = 100_000