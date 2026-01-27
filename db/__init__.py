"""Database utilities for the bot."""

from db.db_setup import (
    init_db,
    add_user,
    get_user,
    update_user,
    revoke_trial,
    get_referees,
    User,
    check_payment_processed,
    add_processed_payment,
    deduct_balance
)

__all__ = [
    "init_db",
    "add_user",
    "get_user",
    "update_user",
    "revoke_trial",
    "get_referees",
    "User",
    "check_payment_processed",
    "add_processed_payment",
    "deduct_balance"
]
