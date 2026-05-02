import uuid
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer
from sqlalchemy.orm import declarative_base, sessionmaker
from eventsourcing.postgres import PostgresTrackingRecorder
from balance_service.config import READ_MODEL_DB_URL

Base = declarative_base()

class WalletView(Base):
    __tablename__ = 'wallet_read_model'
    id = Column(String, primary_key=True)
    balance = Column(Float, default=0.0)

class WalletHistoryView(Base):
    __tablename__ = 'wallet_history_read_model'
    id = Column(Integer, primary_key=True, autoincrement=True)
    wallet_id = Column(String, index=True)
    operation = Column(String)
    amount = Column(Float)
    timestamp = Column(DateTime)

class CustomPostgresWalletView(PostgresTrackingRecorder):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.engine = create_engine(READ_MODEL_DB_URL)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def create_wallet(self, wallet_id: str, timestamp: datetime, tracking):
        with self.Session() as session:
            with session.begin():
                self._save_balance_view(session, wallet_id, 0.0)
                self._save_history_entry(session, wallet_id, "CREATE", 0.0, timestamp)
                self.insert_tracking(tracking)

    def credit_balance(self, wallet_id: str, amount: float, timestamp: datetime, tracking):
        with self.Session() as session:
            with session.begin():
                view = self._get_balance_view(session, wallet_id)
                view.balance += amount
                
                self._save_history_entry(session, wallet_id, "CREDIT", amount, timestamp)
                self.insert_tracking(tracking)

    def debit_balance(self, wallet_id: str, amount: float, timestamp: datetime, tracking):
        with self.Session() as session:
            with session.begin():
                view = self._get_balance_view(session, wallet_id)
                view.balance -= amount
                
                self._save_history_entry(session, wallet_id, "DEBIT", amount, timestamp)
                self.insert_tracking(tracking)


    def _get_balance_view(self, session, wallet_id: str) -> WalletView:
        view = session.query(WalletView).filter(WalletView.id == wallet_id).first()
        if not view:
            raise ValueError(f"Wallet {wallet_id} not found")
        return view

    def _save_balance_view(self, session, wallet_id: str, balance: float):
        view = WalletView(id=wallet_id, balance=balance)
        session.add(view)

    def _save_history_entry(self, session, wallet_id: str, operation: str, amount: float, timestamp: datetime):
        history_entry = WalletHistoryView(
            wallet_id=wallet_id,
            operation=operation,
            amount=amount,
            timestamp=timestamp
        )
        session.add(history_entry)