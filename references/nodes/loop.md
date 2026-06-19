> ⚠️ ИСТОЧНИК ИСТИНЫ: Pydantic-схема в бэкенде Dify (в пакете graphon.nodes (в entities.py для loop)).
> Если референс расходится с кодом — код прав. Перед генерацией DSL сверяй поля.

# Loop Node — Верифицированный справочник

> Протестировано на Dify 1.14.2 self-hosted, 2026-06-18.
> Все примеры — из реальных тестов, не из документации.

## Что это

Нода-контейнер для циклического выполнения шагов workflow. Позволяет повторять блок шагов заданное число раз (`loop_count`) или до выполнения условий выхода (`break_conditions`). Использует концепцию цикла с изменяемыми переменными (`loop_variables`).

## Базовая структура (DSL)

Цикл состоит из родительской ноды типа `loop`, стартовой точки `loop-start` (внутри контейнера) и дочерних нод.

```yaml
# Родитеский Loop-контейнер
- id: 'loop_node_id'
  type: custom
  data:
    title: Loop
    type: loop
    loop_count: 10
    logical_operator: and              # and | or (для условий выхода)
    start_node_id: 'loop_start_id'
    loop_variables:
      - id: 'var_id_1'
        label: num
        value_type: constant           # constant | variable
        var_type: number               # string | number | object | boolean | array[...]
        value: 1                       # начальное значение
    break_conditions:
      - id: 'cond_id_1'
        variable_selector: ['loop_node_id', 'num'] # отслеживаем переменную цикла
        comparison_operator: '≥'       # '=', '≠', '<', '>', '≥', '≤'
        value: '5'
        varType: number

# Внутренняя стартовая нода (loop-start)
- id: 'loop_start_id'
  type: custom-loop-start
  parentId: 'loop_node_id'
  data:
    type: loop-start
    isInLoop: true

# Внутренняя нода изменения переменной (Variable Assigner)
- id: 'assigner_id'
  type: custom
  parentId: 'loop_node_id'
  data:
    title: Incrementer
    type: assigner
    version: '2'
    isInLoop: true
    loop_id: 'loop_node_id'
    items:
      - input_type: constant
        operation: '+='                # '+=' | '-=' | 'over-write' | 'append' и др.
        value: 1
        variable_selector: ['loop_node_id', 'num']
        write_mode: over-write
```

## Жизненный цикл выполнения

1. **Инициализация:** Нода регистрирует переменные цикла (`loop_variables`) в пуле переменных по адресу `['loop_node_id', 'label_name']`.
2. **Проверка на старте:** Перед первой итерацией вычисляются условия выхода (`break_conditions`). Если они верны, цикл завершается сразу (сделано 0 шагов).
3. **Итерация:** Создается дочерний движок графа, который запускается с ноды `start_node_id`. Дочерние ноды цикла должны иметь атрибуты `parentId: loop_node_id` и `isInLoop: true`.
4. **Сброс переменных:** Между итерациями Dify **автоматически очищает** переменные, созданные обычными нодами внутри цикла (`_clear_loop_subgraph_variables`). Это гарантирует отсутствие "залипших" данных из предыдущих раундов. Сохраняются только задекларированные `loop_variables`.
5. **Финал раунда:** При завершении ветки (когда нет больше исходящих связей в цикле):
   * Считываются актуальные значения переменных `loop_variables`.
   * Переменная `loop_round` увеличивается на 1.
   * Оцениваются условия выхода. Если условия выполнены — цикл завершается со статусом `LOOP_BREAK`.
   * Если раунд достиг `loop_count` — цикл завершается со статусом `LOOP_COMPLETED`.
   * Иначе запускается следующий раунд.

## Особенности и ограничения

* **Явный `loop-end` не требуется:** В отличие от `iteration`, в цикле нет обязательной ноды `loop-end`. Достаточно, чтобы последняя нода в цикле (например, Assigner) не имела исходящих ребер.
* **Обновление переменных:** Изменение переменных цикла внутри итераций выполняется через ноду **Variable Assigner** (тип `assigner`), ссылающуюся на переменную родительского цикла `['loop_node_id', 'var_name']`.
* **Выходные значения:** После завершения цикла, нода Loop экспонирует:
  * Все объявленные `loop_variables` в их финальном состоянии.
  * Переменную `loop_round` (тип `number`) — количество выполненных итераций.
