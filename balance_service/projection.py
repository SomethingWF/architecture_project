from eventsourcing.dispatch import singledispatchmethod
from eventsourcing.projection import Projection
from balance_service.domain import Wallet
from balance_service.view import CustomPostgresWalletView

class WalletProjection(Projection[CustomPostgresWalletView]):
    #topics = ("Wallet.Created", "Wallet.Deposited", "Wallet.Withdrawn")

    @singledispatchmethod
    def process_event(self, event, tracking):
        pass

    @process_event.register
    def _(self, event: Wallet.Created, tracking):
        self.view.create_wallet(
            wallet_id=str(event.originator_id),
            timestamp=event.timestamp,
            tracking=tracking
        )

    @process_event.register
    def _(self, event: Wallet.Deposited, tracking):
        self.view.credit_balance(
            wallet_id=str(event.originator_id),
            amount=event.amount,
            timestamp=event.timestamp,
            tracking=tracking
        )

    @process_event.register
    def _(self, event: Wallet.Withdrawn, tracking):
        self.view.debit_balance(
            wallet_id=str(event.originator_id),
            amount=event.amount,
            timestamp=event.timestamp,
            tracking=tracking
        )