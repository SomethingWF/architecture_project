from eventsourcing.application import Application
from balance_service.domain import Wallet

class WalletApplication(Application):
    def create_wallet(self, user_id: str) -> str:
        wallet = Wallet(user_id=user_id)
        self.save(wallet)
        return str(wallet.id)

    def deposit(self, wallet_id: str, amount: float):
        wallet = self.repository.get(wallet_id)
        wallet.deposit(amount)
        self.save(wallet)

    def withdraw(self, wallet_id: str, amount: float):
        wallet = self.repository.get(wallet_id)
        wallet.withdraw(amount)
        self.save(wallet)