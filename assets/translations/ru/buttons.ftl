btn-back = 
    .general = Назад
    .menu = ↩️ Главное меню
    .menu-return = ↩️ Вернуться в главное меню
    .dashboard = ↩️ Вернуться в панель управления

btn-common =
    .notification-close = ❌ Закрыть
    .cancel = Отмена

    .squad-choice = { $selected ->
    [1] 🔘
    *[0] ⚪
    } { $name }

    .duration = ⌛ { $value ->
    [0] { unlimited }
    *[other] { unit-day }
    }

btn-remnashop-info =
    .release-latest = 👀 Посмотреть
    .how-upgrade = ❓ Как обновить
    .github = ⭐ GitHub
    .telegram = 👪 Telegram
    .donate = 💰 Поддержать разработчика
    .guide = ❓ Инструкция

btn-requirement =
    .rules-accept = ✅ Принять правила
    .channel-join = ❤️ Перейти в канал
    .channel-confirm = ✅ Подтвердить

btn-menu =
    .trial = 🎁 ПОПРОБОВАТЬ БЕСПЛАТНО
    .connect = 🚀 Подключиться
    .subscription = Мои консультации
    .instruction = Правила консультации
    .invite = Реферальная программа
    .support = Помощь
    .dashboard = 🛠 Панель управления

btn-experts =
    .catalog = 👩‍⚕️ Выбрать эксперта
    .consultations = 💬 Мои консультации
    .clients = 🩺 Мои клиенты
    .buy = Оплатить консультацию
    .become = 🧑‍⚕️ Стать экспертом
    .stats = 📊 Статистика
    .prices = 💰 Мои тарифы
    .price-edit = ✏️ Изменить стоимость
    .price-decrease = − 100
    .price-increase = + 100
    .price-custom = ⌨️ Ввести сумму
    .price-save = ✅ Сохранить стоимость
    .profile-edit = ✏️ Редактировать профиль
    .profile-name = ФИО
    .profile-specialization = Специализация
    .profile-experience = Опыт работы
    .profile-photo = Фотография
    .withdraw = 💸 Вывод
    .cabinet = 🩺 Кабинет эксперта
    .finance = 💰 Финансы

    .connect-not-available =
    ⚠️ { $status ->
    [LIMITED] ПРЕВЫШЕН ЛИМИТ ТРАФИКА
    [EXPIRED] СРОК ДЕЙСТВИЯ ИСТЕК
    *[OTHER] ВАША ПОДПИСКА НЕ РАБОТАЕТ
    } ⚠️

btn-invite =
    .about = ❓ Подробнее о награде
    .copy = 📋 Скопировать ссылку
    .send = Пригласить
    .qr = 🧾 QR-код
    .withdraw-points = 💎 Обменять баллы

btn-support =
    .user-agreement = Пользовательское соглашение
    .privacy-policy = Политика конфиденциальности
    .contact = Написать в поддержку

btn-instruction =
    .ios = iPhone/iPad
    .android = Android
    .windows = Windows
    .macos = MacOS
    .download = 1. Скачать приложение
    .download_ru = 1. Скачать приложение(RU AppStore)
    .download_global = 1. Скачать приложение(Global AppStore)
    .connect = 2. Подключиться
    .back = Вернуться назад

btn-dashboard =
    .statistics = 📊 Статистика
    .users = 👥 Пользователи
    .broadcast = 📢 Рассылка
    .promocodes = 🎟 Промокоды
    .access = 🔓 Режим доступа
    .remnawave = 🌊 RemnaWave
    .remnashop = 🛍 RemnaShop
    .importer = 📥 Импорт пользователей

btn-statistics =
    .users = 👥 Пользователи
    .subscriptions = 💳 Подписки
    .transactions = 🧾 Транзакции
    .promocodes = 🎁 Промокоды
    .referrals = 👪 Рефералы

    .subscription-page =
    { $page ->
        [0] { $is_current ->
            [1] [ Общая статистика ]
            *[0] Общая статистика
        }
        *[other] { $is_current ->
            [1] [ { $plan_name } ]
            *[0] { $plan_name }
        }
    }

    .transaction-page =
    { $page ->
        [0] { $is_current ->
            [1] [ Общая статистика ]
            *[0] Общая статистика
        }
        *[other] { $is_current ->
            [1] [ { gateway-type } ]
            *[0] { gateway-type }
        }
    }

btn-users =
    .search = 🔍 Поиск пользователя
    .recent-registered = 🆕 Последние зарегистрированные
    .recent-activity = 📝 Последние взаимодействующие
    .blacklist = 🚫 Черный список
    .unblock-all = 🔓 Разблокировать всех

btn-user =
    .expert-profile-toggle = { $is_active ->
    [1] 🔴 Отключить анкету эксперта
    *[0] 🟢 Включить анкету эксперта
    }
    .discount = 💸 Скидка
    .discount-personal = 👤 Персональная скидка
    .discount-purchase = 🎟 На следующую покупку
    .points = 💎 Баллы
    .statistics = 📊 Статистика
    .referrals = 👪 Рефералы
    .message = 📩 Сообщение
    .role = 👮‍♂️ Роль
    .transactions = 🧾 Транзакции
    .give-access = 🔑 Доступ к планам
    .current-subscription = 💳 Текущая подписка
    .subscription-expire-time = ⏳ Время истечения
    .subscription-url = 📋 Скопировать ссылку
    .subscription-set = ✅ Установить подписку
    .subscription-delete = ❌ Удалить
    .message-preview = 👀 Предпросмотр
    .message-confirm = ✅ Отправить
    .sync = 🌀 Синхронизировать
    .sync-remnawave = 🌊 Использовать данные Remnawave
    .sync-remnashop = 🛍 Использовать данные Remnashop
    .give-subscription = 🎁 Выдать подписку

    .allowed-plan-choice = { $selected ->
    [1] 🔘
    *[0] ⚪
    } { $plan_name }

    .subscription-active-toggle = { $is_active ->
    [1] 🔴 Выключить
    *[0] 🟢 Включить
    }

    .transaction = { $status ->
    [PENDING] 🕓
    [COMPLETED] ✅
    [CANCELED] ❌
    [REFUNDED] 💸
    [FAILED] ⚠️
    *[OTHER] { $status }
    } { $created_at }

    .trial-toggle = { $is_trial_available ->
    [1] 🧪 Пробник: доступен
    *[0] 🧪 Пробник: не доступен
    }

    .block = { $is_blocked ->
    [1] 🔓 Разблокировать
    *[0] 🔒 Заблокировать
    }

btn-broadcast =
    .list = 📄 Список всех рассылок
    .all = 👥 Всем
    .plan = 📦 По плану
    .subscribed = ✅ С подпиской
    .unsubscribed = ❌ Без подписки
    .expired = ⌛ Просроченным
    .trial = ✳️ С пробником
    .content = ✉️ Редактировать содержимое
    .buttons = ✳️ Редактировать кнопки
    .preview = 👀 Предпросмотр
    .confirm = ✅ Запустить рассылку
    .refresh = 🔄 Обновить данные
    .viewing = 👀 Просмотр
    .cancel = ⛔ Остановить рассылку
    .delete = ❌ Удалить отправленное

    .plan-title = { $is_active ->
    [1] 🟢
    *[0] 🔴
    } { $name }

    .button-choice = { $selected ->
    [1] 🔘
    *[0] ⚪
    }

    .title = { $status ->
    [PROCESSING] ⏳
    [COMPLETED] ✅
    [CANCELED] ⛔
    [DELETED] ❌
    [ERROR] ⚠️
    *[OTHER] { $status }
    } { $created_at }

btn-goto =
    .subscription = 💳 Выбрать эксперта
    .promocode = 🎟 Активировать промокод
    .invite = 👥 Пригласить
    .subscription-renew = 🔄 Продлить подписку
    .user-profile = 👤 Перейти к пользователю
    .referrer-profile = 🤝 Перейти к пригласителю
    .contact-support = 📩 Перейти в поддержку

btn-promocodes =
    .list = 📃 Список промокодов
    .search = 🔍 Поиск промокода
    .create = 🆕 Создать
    .delete = 🗑️ Удалить
    .edit = ✏️ Редактировать

btn-access =
    .mode = { access-mode }
    .conditions = ⚙️ Условия доступа
    .rules = ✳️ Принятие правил
    .channel = ❇️ Подписка на канал

    .payments-toggle = { $enabled ->
    [1] 🔘
    *[0] ⚪
    } Платежи

    .registration-toggle = { $enabled ->
    [1] 🔘
    *[0] ⚪
    } Регистрация

    .condition-toggle = { $enabled ->
    [1] 🔘 Включено
    *[0] ⚪ Выключено
    }

btn-remnashop =
    .admins = 👮‍♂️ Администраторы
    .gateways = 🌐 Платежные системы
    .referral = 👥 Реф. система
    .advertising = 🎯 Реклама
    .plans = 📦 Планы
    .notifications = 🔔 Уведомления
    .logs = 📄 Логи
    .menu-editor = 🎛 Доп. кнопки

btn-menu-editor =
    .text = 🏷️ Текст
    .availability = ✴️ Доступ
    .type = 🔖 Тип
    .payload = 📄 Данные
    .confirm = ✅ Сохранить

    .button = { $is_active ->
        [1] 🟢
        *[0] 🔴
    } { $text }

    .active = { $is_active ->
        [1] 🟢 Включена
        *[0] 🔴 Выключена
    }

btn-gateway =
    .title = { gateway-type }
    .setting = { $field }
    .webhook-copy = 📋 Скопировать вебхук
    .test = 🐞 Тест
    .default-currency = 💸 Валюта по умолчанию
    .placement = 🔢 Изменить позиционирование

    .active = { $is_active ->
    [1] 🟢 Включено
    *[0] 🔴 Выключено
    }

    .default-currency-choice = { $enabled ->
    [1] 🔘
    *[0] ⚪
    } { $symbol } { $currency }

btn-referral =
    .level = 🔢 Уровень
    .reward-type = 🎀 Тип награды
    .accrual-strategy = 📍 Условие начисления
    .reward-strategy = ⚖️ Форма начисления
    .reward = 🎁 Награда
    .trial-reward = { $reward_for_trial ->
    [1] 🟢 Награда за пробник
    *[0] 🔴 Награда за пробник
    }

    .enable = { $is_enable ->
    [1] 🟢 Включена
    *[0] 🔴 Выключена
    }

    .level-choice = { $type ->
    [1] 1️⃣
    [2] 2️⃣
    [3] 3️⃣
    *[OTHER] { $type }
    }

    .reward-choice = { $type ->
    [POINTS] 💎 Баллы
    [EXTRA_DAYS] ⏳ Дни
    *[OTHER] { $type }
    }

    .accrual-strategy-choice = { $type ->
    [ON_FIRST_PAYMENT] 💳 Первый платеж
    [ON_EACH_PAYMENT] 💸 Каждый платеж
    *[OTHER] { $type }
    }

    .reward-strategy-choice = { $type ->
    [AMOUNT] 🔸 Фиксированная
    [PERCENT] 🔹 Процентная
    *[OTHER] { $type }
    }

btn-notifications =
    .user = 👥 Пользовательские
    .system = ⚙️ Системные

    .user-choice = { $enabled ->
    [1] 🔘
    *[0] ⚪
    } { $type ->
    [EXPIRES_IN_3_DAYS] Подписка истекает (3 дня)
    [EXPIRES_IN_2_DAYS] Подписка истекает (2 дня)
    [EXPIRES_IN_1_DAY] Подписка истекает (1 день)
    [EXPIRES_IN_1_HOUR] Подписка истекает (1 час)
    [EXPIRED] Подписка истекла
    [EXPIRED_1_DAY_AGO] Подписка истекла (1 день)
    [LIMITED] Трафик исчерпан
    [TRIAL_NOT_CONNECTED] Пробник без подключения (1 час)
    [REFERRAL_ATTACHED] Реферал закреплен
    [REFERRAL_REWARD_RECEIVED] Вознаграждение за реферала
    *[OTHER] { $type }
    }

    .system-choice = { $enabled ->
    [1] 🔘
    *[0] ⚪
    } { $type ->
    [BOT_LIFECYCLE] Жизненный цикл бота
    [BOT_UPDATE] Обновления бота
    [USER_REGISTERED] Регистрация пользователя
    [SUBSCRIPTION] Оформление подписки
    [PROMOCODE_ACTIVATED] Активация промокода
    [TRIAL_ACTIVATED] Активация пробника
    [NODE_STATUS_CHANGED] Статус узла
    [NODE_TRAFFIC_REACHED] Трафик узла
    [USER_FIRST_CONNECTION] Первое подключение
    [USER_DEVICES_UPDATED] Устройства пользователя
    [USER_REVOKED_SUBSCRIPTION] Сброс подписки
    *[OTHER] { $type }
    }

btn-plans =
    .statistics = 📊 Статистика
    .create = 🆕 Создать
    .save = ✅ Сохранить
    .create = ✅ Создать план
    .delete = ❌ Удалить
    .name = 🏷️ Название
    .description = 💬 Описание
    .description-remove = ❌ Удалить текущее описание
    .tag = 📌 Тег
    .tag-remove = ❌ Удалить текущий тег
    .availability = ✴️ Доступ
    .durations-prices = ⏳ Длительности и 💰 Цены
    .allowed = 👥 Разрешенные пользователи
    .allowed-user = { $id }
    .duration-add = 🆕 Добавить длительность
    .price-choice = 💸 { $price } { $currency }
    .export = 📤 Экспорт
    .import = 📥 Импорт
    .exporting = 📤 Экспортировать
    .importing = 📥 Импортировать
    .url = 📋 Скопировать ссылку на план

    .trial = { $is_trial ->
    [1] 🔘
    *[0] ⚪
    } Пробник

    .export-choice = { $selected ->
    [1] 🔘
    *[0] ⚪
    } { $name }

    .title = { $is_active ->
    [1] 🟢
    *[0] 🔴
    } { $name }

    .active = { $is_active ->
    [1] 🟢 Включен
    *[0] 🔴 Выключен
    }

    .availability-choice = { $type ->
    [ALL] 🌍 Для всех
    [NEW] 🌱 Для новых
    [EXISTING] 👥 Для клиентов
    [INVITED] ✉️ Для приглашенных
    [ALLOWED] 🔐 Для разрешенных
    [LINK] 🔗 По ссылке
    *[OTHER] { $type }
    }

btn-remnawave =
    .users = 👥 Пользователи
    .hosts = 🌐 Хосты
    .nodes = 🖥️ Ноды
    .inbounds = 🔌 Инбаунды

btn-importer =
    .from-xui = 💩 Импорт из панели 3X-UI
    .from-xui-shop = 🛒 Бот 3xui-shop
    .sync = 🌀 Запустить синхронизацию
    .squads = 🔗 Внутренние сквады
    .import-all = ✅ Импортировать всех
    .import-active = ❇️ Импортировать активных

btn-subscription =
    .plan = 💳 Перейти к оформлению консультации
    .new = Купить консультацию
    .renew = Продлить
    .change = 🔃 Изменить
    .promocode = 🎟 Активировать промокод
    .payment-method = { $payment_label } | { $final_amount ->
    [0] 🎁
    *[HAS] { $final_amount }{ $currency }
    }
    .pay = 💳 Оплатить
    .get = 🎁 Получить бесплатно
    .back-plans = ⬅️ Назад к выбору плана
    .back-duration = ⬅️ Изменить длительность
    .back-payment-method = ⬅️ Изменить способ оплаты
    .connect = 💬 Открыть консультацию

    .duration = { $period } | { $final_amount ->
    [0] 🎁
    *[HAS] { $final_amount }{ $currency }
    }

btn-promocode =
    .code = 🏷️ Код
    .type = 🔖 Тип награды
    .availability = ✴️ Доступ
    .reward = 🎁 Награда
    .lifetime = ⌛ Время жизни
    .allowed = 👥 Разрешенные пользователи
    .confirm = ✅ Подтвердить

    .active = { $is_active ->
    [1] 🟢
    *[0] 🔴
    } Статус
