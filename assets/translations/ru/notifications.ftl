ntf-error =
    .unknown = ⚠️ <i>Произошла ошибка.</i>
    .permission-denied = ⚠️ <i>У вас недостаточно прав.</i>
    .log-not-found = ⚠️ <i>Лог файл не найден.</i>
    .logs-disabled = ⚠️ <i>Логирование в файл отключено.</i>
    
    .lost-context = ⚠️ <i>Произошла ошибка. Перезапустите диалог командой /start.</i>
    .lost-context-restart = ⚠️ <i>Произошла ошибка. Диалог перезапущен.</i>

ntf-common =
    .trial-unavailable = ⚠️ <i>Пробная подписка временно недоступна.</i>
    .throttling = ⚠️ <i>Вы отправляете слишком много запросов. Пожалуйста, подождите.</i>
    .double-click-confirm = ⚠️ <i>Нажмите еще раз, чтобы подтвердить действие.</i>
    .withdraw-points = ❌ <i>У вас недостаточно баллов для выполнения обмена.</i>

    .invalid-value = ❌ <i>Некорректное значение.</i>
    .value-updated = ✅ <i>Параметр успешно обновлен.</i>

    .plan-not-found = ❌ <i>План не найден или недоступен.</i>

    .connect-not-available =
    ⚠️ { $status ->
    [LIMITED] Доступ по подписке временно ограничен. Обратитесь в поддержку.
    [EXPIRED]  
    { $is_trial ->
    [0] Срок действия вашей подписки истек. Продлите подписку или оформите новую.
    *[1] Бесплатный пробный период завершен. Оформите подписку, чтобы продолжить пользоваться сервисом.
    }
    *[OTHER] Произошла ошибка при проверке статуса или подписка была отключена. Обратитесь в поддержку.
    }
    
ntf-command =
    .paysupport = 💸 <b>Чтобы запросить возврат, обратитесь в службу поддержки.</b>
    .rules = ⚠️ <b>Пожалуйста, ознакомьтесь с <a href="{ $url }">Условиями использования</a> перед использованием сервиса.</b>
    .help = 🆘 <b>Нажмите кнопку ниже, чтобы связаться с поддержкой.</b>

ntf-requirement =
    .channel-join-required = ❇️ Подпишитесь на наш канал и получайте <b>бесплатные дни, акции и новости</b>. После подписки нажмите «Подтвердить».
    .channel-join-required-left = ⚠️ Вы отписались от канала. Подпишитесь, чтобы продолжить пользоваться ботом.
    .rules-accept-required = ⚠️ <b>Перед использованием сервиса ознакомьтесь и примите <a href="{ $url }">Условия использования</a>.</b>
    .channel-join-error = ⚠️ Мы не видим вашу подписку на канал. Проверьте подписку и попробуйте снова.
    
ntf-user =
    .not-found = <i>❌ Пользователь не найден.</i>
    .transactions-empty = ❌ <i>Список транзакций пуст.</i>
    .subscription-empty = ❌ <i>Активная подписка не найдена.</i>
    .subscription-deleted = ✅ <i>Подписка успешно удалена.</i>
    .plans-empty = ❌ <i>Нет доступных планов.</i>
    .allowed-plans-empty = ❌ <i>Нет доступных планов для предоставления доступа.</i>
    .message-success = ✅ <i>Сообщение успешно отправлено.</i>
    .message-failed = ❌ <i>Не удалось отправить сообщение.</i>
    .discount-issued =
        Вам выдана { $discount_kind } на тариф «{ $plan_name }». Убедитесь в лучшей скорости и свободном интернете. 🚀🌐

        <blockquote>🎯 <s>{ $original_amount }{ $currency }</s> > { $final_amount }{ $currency }</blockquote>
    .expired-trial-discount =
        <b>Мы сохранили для вас персональную скидку на тариф «{ $plan_name }»

        Скидка будет действовать ещё 24 часа. После этого стоимость вернётся к обычной.</b>

    .sync-already = ✅ <i>Данные подписки идентичны.</i>
    .sync-missing-data = ⚠️ <i>Синхронизация невозможна. Данные подписки отсутствуют в панели и в боте.</i>
    .sync-success = ✅ <i>Синхронизация подписки выполнена.</i>

    .invalid-expire-time = ❌ <i>Невозможно { $operation ->
    [ADD] продлить
    *[SUB] сократить
    } срок подписки на указанное количество дней.</i>

    .invalid-points = ❌ <i>Невозможно { $operation ->
    [ADD] добавить
    *[SUB] списать
    } указанное количество баллов.</i>

ntf-access =
    .maintenance = 🚧 <i>Бот находится на обслуживании. Попробуйте позже.</i>
    .registration-disabled = ❌ <i>Регистрация новых пользователей отключена.</i>
    .registration-invite-only = ❌ <i>Регистрация доступна только по приглашению.</i>
    .payments-disabled = 🚧 <i>Платежи временно недоступны! Вы получите уведомление после восстановления.</i>
    .payments-restored = ❇️ <i>Платежи восстановленны! Теперь вы можете купить или продлить подписку. Спасибо за ожидание.</i>

ntf-plan =
    .not-file = ⚠️ <i>Отправьте планы в виде json файла.</i>
    .import-failed = ❌ <i>Не удалось импортировать.</i>
    .import-success = ✅ <i>Успешно импотированно.</i>
    .export-plans_not_selected =  ❌ <i>Выберите хотя бы один план для экспорта.</i>
    .export-failed = ❌ <i>Не удалось экспортировать.</i>
    .export-success = ✅ <i>Выбранные планы экспортированы.</i>
    .trial-single-duration = ❌ <i>Пробный план может иметь только одну длительность.</i>
    .duration-already-exists = ❌ <i>Такая длительность уже существует.</i>
    .name-already-exists = ❌ <i>План с таким именем уже существует.</i>
    .user-already-allowed = ❌ <i>Индентификтор пользователя уже добавлен.</i>

    .updated = ✅ <i>План успешно обновлен.</i>
    .created = ✅ <i>План успешно создан.</i>
    .deleted = ✅ <i>План успешно удален.</i>

ntf-gateway =
    .not-configured = ❌ <i>Платежный шлюз не настроен.</i>
    .not-configurable = ❌ <i>У платежного шлюза отсутствуют настройки.</i>

    .test-payment-created = ✅ <i><a href="{ $url }">Тестовый платеж</a> успешно создан.</i>
    .test-payment-error = ❌ <i>Ошибка при создании тестового платежа.</i>
    .test-payment-confirmed = ✅ <i>Тестовый платеж успешно обработан.</i>

ntf-subscription =
    .plans-unavailable = ❌ <i>У выбранного эксперта сейчас нет доступных тарифов.</i>
    .gateways-unavailable = ❌ <i>В данный момент нет доступных платежных систем.</i>
    .renew-plan-unavailable = ❌ <i>Текущий план устарел и недоступен для продления.</i>
    .payment-creation-failed = ❌ <i>Ошибка при создании платежа. Попробуйте позже.</i>

ntf-broadcast =
    .message = { $content }
    .text-too-long = ❌ Превышено максимальное кол-во символов ({ $max_limit }).
    .list-empty = ❌ <i>Список рассылок пуст.</i>
    .plans-unavailable = ❌ <i>Нет доступных планов.</i>
    .audience-unavailable = ❌ <i>Нет пользователей для выбранной аудитории.</i>
    .content-empty = ❌ <i>Контент пуст.</i>
    .content-saved = ✅ <i>Контент успешно сохранен.</i>

    .not-cancelable = ❌ <i>Рассылку невозможно отменить.</i>
    .canceled = ✅ <i>Рассылка успешно отменена.</i>
    .deleting = ⚠️ <i>Выполняется удаление отправленных сообщений.</i>
    .already-deleted = ❌ <i>Рассылка уже удалена или находится в процессе удаления.</i>

    .deleted-success =
        ✅ Рассылка <code>{ $task_id }</code> успешно удалена.

        <blockquote>
        • <b>Всего сообщений</b>: { $total_count }
        • <b>Удалено</b>: { $deleted_count }
        • <b>Не удалось удалить</b>: { $failed_count }
        </blockquote>

ntf-importer =
    .not-file = ⚠️ <i>Отправьте базу данных в виде файла.</i>
    .db-failed = ❌ <i>Ошибка при экспорте пользователей из базы данных.</i>
    .users-empty = ❌ <i>Список пользователей в базе данных пуст.</i>

    .started = ✅ <i>Импорт запущен. Дождитесь завершения...</i>
    .already-running = ⚠️ <i>Импорт уже выполняется. Пожалуйста, подождите.</i>

ntf-sync =
    .started = ✅ <i>Синхронизация запущена. Дождитесь завершения...</i>
    .users-not-found = ❌ <i>Пользователи для синхронизации не найдены.</i>
    .already-running = ⚠️ <i>Синхронизация уже выполняется. Пожалуйста, подождите.</i>

ntf-menu-editor =
    .button-saved = ✅ <i>Кнопка успешно сохранена.</i>
    .invalid-payload = ❌ <i>Недопустимый формат URL для payload.</i>

ntf-expert =
    .application =
        <b>Новая заявка эксперта #{ $id }</b>
        <b>ФИО:</b> { $name }
        <b>Специализация:</b> { $specialization }
        <b>Опыт работы:</b> { $experience }
        <b>Telegram ID:</b> <code>{ NUMBER($telegram_id, useGrouping: 0) }</code>
        { $username ->
            [0] { empty }
            *[HAS] <b>Username:</b> <a href="tg://user?id={ $telegram_id }">@{ $username }</a>
        }
    .application-approved = ✅ Ваша заявка эксперта одобрена. Кабинет эксперта доступен в главном меню.
    .application-rejected = ❌ Заявка эксперта отклонена. Причина: { $reason }
    .price-changed =
        Эксперт { $expert } (анкета #{ $expert_id }) изменил цену.
        Период #{ $duration_id }: { $price } { $currency }
    .withdrawal-request =
        <b>Новая заявка на вывод #{ $id }</b>
        Эксперт: { $expert }
        Сумма: { $amount } { $currency }
        Банк: { $bank }
    .withdrawal-approved = ✅ Заявка #{ $id } на вывод { $amount } { $currency } одобрена.
    .withdrawal-rejected = ❌ Заявка #{ $id } отклонена. Причина: { $reason }
