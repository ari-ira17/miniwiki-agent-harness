# Источники адаптированных навыков

Проверка: 03.11.2026. Навыки прочитаны по закреплённым commit и адаптированы
внутри проекта для Codex; удалённый код не исполнялся. Указанные хеши — версии
источников, а не версии MiniWiki. Лицензии и сведения об изменениях сохранены
рядом с каждым адаптированным SKILL.md. Три собственных навыка MiniWiki
(add-wiki-endpoint, security-review, session-handoff) не являются установкой
этих внешних источников.

## webapp-testing

- Источник: [anthropics/skills — SKILL.md](https://github.com/anthropics/skills/blob/fa0fa64bdc967915dc8399e803be67759e1e62b8/skills/webapp-testing/SKILL.md), commit `fa0fa64bdc967915dc8399e803be67759e1e62b8`.
- Лицензия: [Apache-2.0 и copyright Anthropic](https://github.com/anthropics/skills/blob/fa0fa64bdc967915dc8399e803be67759e1e62b8/skills/webapp-testing/LICENSE.txt); локально `.agents/skills/webapp-testing/LICENSE.txt` и `NOTICE.txt`.
- Адаптация: не копируем helper для запуска серверов и примеры; порядок
  исследования интерфейса, проверок и реальных доказательств привязан к MiniWiki.
  Готовность динамического экрана проверяется конкретным условием. Локальный
  NOTICE — уведомление об этой адаптации; в каталоге исходного навыка отдельного
  NOTICE нет.
- Риск: отсутствие приложения, браузера или runtime означает «не проверено»;
  фиктивный скриншот и отчёт об успешном запуске недопустимы.

## systematic-debugging

- Источник: [obra/superpowers — SKILL.md](https://github.com/obra/superpowers/blob/c74782ead66b8ded584d9b9cf64dcba95457f320/skills/systematic-debugging/SKILL.md), commit `c74782ead66b8ded584d9b9cf64dcba95457f320`.
- Лицензия: [MIT, copyright Jesse Vincent](https://github.com/obra/superpowers/blob/c74782ead66b8ded584d9b9cf64dcba95457f320/LICENSE); локально `.agents/skills/systematic-debugging/LICENSE.txt` и `NOTICE.txt`.
- Адаптация: четыре этапа диагностики сокращены; внешние субнавыки и ссылки на
  неустановленные файлы заменены локальными шагами; примеры с env и keychain
  удалены. Результат проверки не подменяется утверждением о причине сбоя.
- Риск: диагностические сообщения и данные могут содержать секреты; нельзя
  выводить их без необходимости. Отсутствующее окружение отмечать явно.

## grill-with-docs

- Источник: [LinnetCodes/grill-me — SKILL.md](https://github.com/LinnetCodes/grill-me/blob/01ba2d0070575f9d4983b9033fc043406fac8e02/skills/grill-with-docs/SKILL.md), commit `01ba2d0070575f9d4983b9033fc043406fac8e02`.
- Прочитаны зависимые процедуры [grilling](https://github.com/LinnetCodes/grill-me/blob/01ba2d0070575f9d4983b9033fc043406fac8e02/skills/grilling/SKILL.md) и [domain-modeling](https://github.com/LinnetCodes/grill-me/blob/01ba2d0070575f9d4983b9033fc043406fac8e02/skills/domain-modeling/SKILL.md).
- Лицензия: [MIT, copyright LinnetCodes](https://github.com/LinnetCodes/grill-me/blob/01ba2d0070575f9d4983b9033fc043406fac8e02/LICENSE); локально `.agents/skills/grill-with-docs/LICENSE.txt` и `NOTICE.txt`.
- Происхождение: [README LinnetCodes](https://github.com/LinnetCodes/grill-me/blob/01ba2d0070575f9d4983b9033fc043406fac8e02/README.md) называет `mattpocock/skills` источником адаптации. Отдельно прочитаны [wrapper Matt Pocock](https://github.com/mattpocock/skills/blob/447ca70872026d5b79d6073a546dac082117fed7/skills/engineering/grill-with-docs/SKILL.md) и его [MIT-лицензия](https://github.com/mattpocock/skills/blob/447ca70872026d5b79d6073a546dac082117fed7/LICENSE), copyright 2026 Matt Pocock; копия — `LICENSE-upstream.txt`. Точная версия исходника, унаследованная LinnetCodes, не установлена; указанный SHA подтверждает только отдельно прочитанную версию.
- Адаптация: процедура интервью и предметного анализа включена в SKILL.md без
  вызовов отсутствующих slash-команд; вместо `domain_models/` согласованные
  решения записываются в `docs/ai/DECISIONS.md`. Политика вызова исходной
  среды не переносится. Факты исследуются в репозитории до вопросов пользователю.
- Риск: обсуждение не означает согласия; ADR обновлять только после принятого
  пользователем решения, а действующие договорённости не переспрашивать.
