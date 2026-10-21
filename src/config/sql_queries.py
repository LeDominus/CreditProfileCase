CREATE_CONVERSATION_QUERY = """
    INSERT INTO conversations (user_id, state, created_at, updated_at)
    VALUES (:user_id, :state, :created_at, :updated_at)
"""

SEND_MESSAGE_CONVERSATION_QUERY = """
    INSERT INTO messages (conversation_id, role, content, created_at)
    VALUES (:conversation_id, :role, :content, :created_at)
"""

GET_CONVERSATION_QUERY = """
    SELECT id, user_id, state, created_at, updated_at
    FROM conversations
    WHERE id = :id
"""

LIST_CONVERSATIONS_QUERY = """
    SELECT id, user_id, state, created_at, updated_at
    FROM conversations
    WHERE user_id = :user_id
    ORDER BY updated_at DESC, id DESC
"""

CREATE_PROFILE_QUERY = """
    INSERT INTO business_profiles (
        user_id, business_name, industry, funding_purpose, requested_amount,
        business_age_months, monthly_revenue, monthly_profit,
        preferred_term_months, max_monthly_payment, created_at, updated_at
    )
    VALUES (
        :user_id, :business_name, :industry, :funding_purpose, :requested_amount,
        :business_age_months, :monthly_revenue, :monthly_profit,
        :preferred_term_months, :max_monthly_payment, :created_at, :updated_at
    )
"""

GET_PROFILE_QUERY = """
    SELECT id, user_id, business_name, industry, funding_purpose, requested_amount,
           business_age_months, monthly_revenue, monthly_profit,
           preferred_term_months, max_monthly_payment, created_at, updated_at
    FROM business_profiles
    WHERE id = :id
"""

UPDATE_PROFILE_QUERY = """
    UPDATE business_profiles
    SET business_name = :business_name,
        industry = :industry,
        funding_purpose = :funding_purpose,
        requested_amount = :requested_amount,
        business_age_months = :business_age_months,
        monthly_revenue = :monthly_revenue,
        monthly_profit = :monthly_profit,
        preferred_term_months = :preferred_term_months,
        max_monthly_payment = :max_monthly_payment,
        updated_at = :updated_at
    WHERE id = :id
"""

GET_MESSAGES_QUERY = """
    SELECT id, conversation_id, role, content, created_at
    FROM messages
    WHERE conversation_id = :conversation_id
    ORDER BY id
"""

CREATE_CONVERSATIONS_TABLE = """
    CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        state TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
"""

CREATE_MESSAGES_TABLE = """
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
"""

CREATE_BUSINESS_PROFILES_TABLE = """
    CREATE TABLE IF NOT EXISTS business_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        business_name TEXT,
        industry TEXT NOT NULL,
        funding_purpose TEXT NOT NULL,
        requested_amount REAL,
        business_age_months INTEGER,
        monthly_revenue REAL,
        monthly_profit REAL,
        preferred_term_months INTEGER,
        max_monthly_payment REAL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
"""

CREATE_APPLICATION_QUERY = """
    INSERT INTO applications (
        profile_id, product_id, product_name, requested_amount, term_months,
        monthly_payment, total_repayment, overpayment, status,
        score, decision, decision_details, created_at, updated_at
    ) VALUES (
        :profile_id, :product_id, :product_name, :requested_amount, :term_months,
        :monthly_payment, :total_repayment, :overpayment, :status,
        :score, :decision, :decision_details, :created_at, :updated_at
    )
"""

GET_APPLICATION_QUERY = """
    SELECT id, profile_id, product_id, product_name, requested_amount, term_months,
           monthly_payment, total_repayment, overpayment, status,
           score, decision, decision_details, created_at, updated_at
    FROM applications
    WHERE id = :id
"""

GET_PROFILE_APPLICATIONS_QUERY = """
    SELECT id, profile_id, product_id, product_name, requested_amount, term_months,
           monthly_payment, total_repayment, overpayment, status,
           score, decision, decision_details, created_at, updated_at
    FROM applications
    WHERE profile_id = :profile_id
    ORDER BY id DESC
"""

UPDATE_APPLICATION_QUERY = """
    UPDATE applications
    SET status = :status,
        score = :score,
        decision = :decision,
        decision_details = :decision_details,
        updated_at = :updated_at
    WHERE id = :id
"""

UPDATE_APPLICATION_DETAILS_QUERY = """
    UPDATE applications
    SET requested_amount = :requested_amount,
        term_months = :term_months,
        monthly_payment = :monthly_payment,
        total_repayment = :total_repayment,
        overpayment = :overpayment,
        updated_at = :updated_at
    WHERE id = :id
"""

CREATE_APPLICATION_STATUS_HISTORY_TABLE = """
    CREATE TABLE IF NOT EXISTS application_status_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        application_id INTEGER NOT NULL,
        from_status TEXT NOT NULL,
        to_status TEXT NOT NULL,
        actor_type TEXT NOT NULL,
        actor_id INTEGER,
        comment TEXT,
        created_at TEXT NOT NULL
    )
"""

CREATE_APPLICATION_STATUS_HISTORY_QUERY = """
    INSERT INTO application_status_history (
        application_id, from_status, to_status, actor_type, actor_id, comment, created_at
    ) VALUES (
        :application_id, :from_status, :to_status, :actor_type, :actor_id, :comment, :created_at
    )
"""

GET_APPLICATION_STATUS_HISTORY_QUERY = """
    SELECT id, application_id, from_status, to_status, actor_type, actor_id, comment, created_at
    FROM application_status_history
    WHERE application_id = :application_id
    ORDER BY id
"""

CREATE_APPLICATIONS_TABLE = """
    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        profile_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        product_name TEXT NOT NULL,
        requested_amount REAL NOT NULL,
        term_months INTEGER NOT NULL,
        monthly_payment REAL NOT NULL,
        total_repayment REAL NOT NULL,
        overpayment REAL NOT NULL,
        status TEXT NOT NULL,
        score REAL,
        decision TEXT,
        decision_details TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
"""

CREATE_USERS_TABLE = """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'client',
        created_at TEXT NOT NULL
    )
"""

CREATE_AUTH_TOKENS_TABLE = """
    CREATE TABLE IF NOT EXISTS auth_tokens (
        token TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        created_at TEXT NOT NULL
    )
"""

CREATE_USER_QUERY = """
    INSERT INTO users (username, password_hash, salt, role, created_at)
    VALUES (:username, :password_hash, :salt, :role, :created_at)
"""

GET_USER_BY_USERNAME_QUERY = """
    SELECT id, username, password_hash, salt, role, created_at
    FROM users
    WHERE username = :username
"""

GET_USER_BY_ID_QUERY = """
    SELECT id, username, role, created_at
    FROM users
    WHERE id = :id
"""

CREATE_AUTH_TOKEN_QUERY = """
    INSERT INTO auth_tokens (token, user_id, created_at)
    VALUES (:token, :user_id, :created_at)
"""

GET_USER_BY_TOKEN_QUERY = """
    SELECT u.id, u.username, u.role, u.created_at
    FROM auth_tokens t
    JOIN users u ON u.id = t.user_id
    WHERE t.token = :token
"""