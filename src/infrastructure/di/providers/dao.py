from dishka import Provider, Scope, provide

from src.application.common.dao import (
    BroadcastDao,
    ConsultationDao,
    ExpertDao,
    ExpertFinanceDao,
    PaymentGatewayDao,
    PlanDao,
    ReferralDao,
    SettingsDao,
    SubscriptionDao,
    TransactionDao,
    UserDao,
    WaitlistDao,
    WebhookDao,
)
from src.infrastructure.database.dao import (
    BroadcastDaoImpl,
    ConsultationDaoImpl,
    ExpertDaoImpl,
    ExpertFinanceDaoImpl,
    PaymentGatewayDaoImpl,
    PlanDaoImpl,
    ReferralDaoImpl,
    SettingsDaoImpl,
    SubscriptionDaoImpl,
    TransactionDaoImpl,
    UserDaoImpl,
    WaitlistDaoImpl,
    WebhookDaoImpl,
)


class DaoProvider(Provider):
    scope = Scope.REQUEST

    broadcast = provide(source=BroadcastDaoImpl, provides=BroadcastDao)
    consultation = provide(source=ConsultationDaoImpl, provides=ConsultationDao)
    expert = provide(source=ExpertDaoImpl, provides=ExpertDao)
    expert_finance = provide(source=ExpertFinanceDaoImpl, provides=ExpertFinanceDao)
    payment_gateway = provide(source=PaymentGatewayDaoImpl, provides=PaymentGatewayDao)
    plan = provide(source=PlanDaoImpl, provides=PlanDao)
    referral = provide(source=ReferralDaoImpl, provides=ReferralDao)
    settings = provide(source=SettingsDaoImpl, provides=SettingsDao)
    subscription = provide(source=SubscriptionDaoImpl, provides=SubscriptionDao)
    transaction = provide(source=TransactionDaoImpl, provides=TransactionDao)
    user = provide(source=UserDaoImpl, provides=UserDao)

    webhook = provide(source=WebhookDaoImpl, provides=WebhookDao, scope=Scope.APP)
    waitlist = provide(source=WaitlistDaoImpl, provides=WaitlistDao, scope=Scope.APP)
