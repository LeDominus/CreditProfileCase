CREATE_CONVERSATION_QUERY = """
    INSERT INTO conversations (state, created_at, updated_at)
    VALUES (:state, :created_at, :updated_at)
"""

SEND_MESSAGE_CONVERSATION_QUERY = """
    INSERT INTO messages (conversation_id, role, content, created_at)
    VALUES (:conversation_id, :role, :content, :created_at)
"""

GET_CONVERSATION_QUERY = """
    SELECT id, state, created_at, updated_at
    FROM conversations
    WHERE id = :id
"""

LIST_CONVERSATIONS_QUERY = """
    SELECT id, state, created_at, updated_at
    FROM conversations
    ORDER BY updated_at DESC, id DESC
"""

CREATE_PROFILE_QUERY = """
    INSERT INTO business_profiles (
        business_name, industry, funding_purpose, requested_amount,
        business_age_months, monthly_revenue, monthly_profit,
        preferred_term_months, max_monthly_payment, created_at, updated_at
    )
    VALUES (
        :business_name, :industry, :funding_purpose, :requested_amount,
        :business_age_months, :monthly_revenue, :monthly_profit,
        :preferred_term_months, :max_monthly_payment, :created_at, :updated_at
    )
"""

GET_PROFILE_QUERY = """
    SELECT id, business_name, industry, funding_purpose, requested_amount,
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