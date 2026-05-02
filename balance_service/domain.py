from eventsourcing.domain import Aggregate, event

class Wallet(Aggregate):
    class Created(Aggregate.Created):
        user_id: str

    class Deposited(Aggregate.Event):
        amount: float

    class Withdrawn(Aggregate.Event):
        amount: float

    @event(Created)
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.balance = 0.0

    @event(Deposited)
    def deposit(self, amount: float):
        if amount <= 0:
            raise ValueError("Сумма пополнения должна быть больше нуля")
        self.balance += amount

    @event(Withdrawn)
    def withdraw(self, amount: float):
        if amount <= 0:
            raise ValueError("Сумма списания должна быть больше нуля")
        if self.balance < amount:
            raise ValueError("Недостаточно средств на балансе")
        self.balance -= amount