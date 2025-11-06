# authentication-service
auth_service/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── security.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── user.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   └── user.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ldap_service.py
│   │   └── token_service.py
│   ├── routers/
│   │   ├── __init__.py
│   │   └── auth.py
│   └── database/
│       ├── __init__.py
│       └── session.py
├── alembic/
├── .env
├── .env.example
├── pyproject.toml
└── README.md