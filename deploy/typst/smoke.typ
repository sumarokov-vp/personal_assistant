// Смоук образа: шаблон Smartist из локального пакета и кириллица.
// typst compile smoke.typ smoke.pdf — без ошибок и без предупреждений о шрифтах.
#import "@local/smartist:1.0.0": smartist

#show: smartist.with(
  title: "Протокол встречи",
  subtitle: "Проверка образа personal_assistant-bot",
  date: "09.11.2026",
)

= Повестка

Съешь же ещё этих мягких французских булок, да выпей чаю. *Полужирный*, _курсив_.

== Решения

- Шаблон Smartist собирается в контейнере.
- Код моноширинным: `typst compile smoke.typ`.

#table(
  columns: 2,
  [Кто], [Что делает],
  [Ассистент], [Собирает PDF протокола],
)
