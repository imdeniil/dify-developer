# Связи и переходы между нодами (Edges & Routing) — Справочник

> Актуально для Dify 1.14.2 self-hosted. Последнее обновление: 2026-06-18.

В Dify workflow связи (edges) определяют не просто направление движения данных, а управляют логикой ветвления, параллельного выполнения, контекстом видимости переменных и границами изолированных циклов. 

> [!NOTE]
> Все описанные ниже базовые типы переходов (включая ветвление `human-input`, прямое схождение без агрегатора и условные переходы `if-else`) были **полностью верифицированы живыми тестами** на локальном инстансе Dify v1.14.2 с валидацией через базу данных.

---

## 1. Анатомия объекта связи (Edge) в DSL

Каждая связь в YAML/JSON DSL описывается следующим объектом:

```json
{
  "id": "1749000000001-source-1749000000002-target", // Конвенция: <source_id>-source-<target_id>-target
  "source": "1749000000001",                         // ID исходящей ноды
  "sourceHandle": "source",                           // Имя исходящего порта (handle)
  "target": "1749000000002",                         // ID входящей ноды
  "targetHandle": "target",                           // Имя входящего порта (всегда "target")
  "type": "custom",                                   // Всегда "custom"
  "zIndex": 0,                                        // 0 для внешних связей, 1002 для внутренних
  "data": {
    "isInIteration": false,                           // true, if edge is inside Iteration
    "isInLoop": false,                                // true, if edge is inside Loop
    "sourceType": "custom",                           // Node type of the source node
    "targetType": "custom"                            // Node type of the target node
  }
}
```

### Типы портов `sourceHandle`
*   `"source"` — стандартный выход для линейных переходов.
*   `case_id` — уникальный ID ветки в [nodes/if-else.md](nodes/if-else.md) ноде.
*   `class_id` — уникальный ID класса в [nodes/question-classifier.md](nodes/question-classifier.md) ноде.
*   `action_id` — ID кнопки действия в [nodes/human-input.md](nodes/human-input.md) ноде.
*   `"__timeout"` — ветка таймаута в [nodes/human-input.md](nodes/human-input.md) ноде.

### Типы нод в `sourceType` и `targetType`
В полях `data.sourceType` и `data.targetType` указывается системное имя типа ноды (например, `"if-else"`, `"question-classifier"`, `"iteration"`, `"iteration-start"`, `"loop"`, `"variable-aggregator"`). Для всех остальных стандартных нод (LLM, Code, HTTP, Tool, Start, End и т.д.) используется значение `"custom"`.

---

## 2. Типы переходов и правила маршрутизации

### А. Линейный переход (Linear Transition)
Связывает стандартные исполняемые ноды последовательно.

*   `sourceHandle`: `"source"`
*   `targetHandle`: `"target"`
*   `sourceType`: `"custom"` (или тип конкретной ноды)
*   `targetType`: `"custom"`
*   `zIndex`: `0`

```
[Start] --(source/target)--> [LLM] --(source/target)--> [Code]
```

### Б. Условное ветвление (If-Else Branching)
Маршрутизирует выполнение в зависимости от истинности логических условий.

*   `sourceType`: `"if-else"`
*   `targetType`: `"custom"`
*   `sourceHandle`: 
    *   Для веток True: точный `case_id`, заданный в настройках ноды.
    *   Для ветки False (Else): строго `"false"`.
*   `targetHandle`: `"target"`

```
                     ┌--[case_id_1]--> [LLM_Branch_A]
[If-Else Condition] -┤
                     └--["false"]----> [Code_Branch_B]
```

### В. Классификационный переход (Classifier Routing)
LLM определяет категорию запроса и направляет поток в соответствующую ветку.

*   `sourceType`: `"question-classifier"`
*   `targetType`: `"custom"`
*   `sourceHandle`: `class_id` (уникальный ID класса, заданный в ноде классификатора).
*   `targetHandle`: `"target"`

```
                        ┌--[class_weather]--> [Weather_API]
[Question Classifier] -┼--[class_math]-----> [Math_Code]
                        └--[class_other]----> [General_LLM]
```

### Г. Интерактивная пауза (Human-in-the-Loop Routing)
Приостанавливает workflow. Выполнение продолжается по ветке нажатой пользователем кнопки или ветке таймаута.

*   `sourceType`: `"human-input"`
*   `targetType`: `"custom"`
*   `sourceHandle`: 
    *   `action_id` (например, `"approve"`, `"reject"`).
    *   Специальный порт `"__timeout"` при истечении лимита ожидания.
*   `targetHandle`: `"target"`

> [!TIP]
> **Верифицировано**: При возобновлении выполнения Dify автоматически активирует только то ребро, `sourceHandle` которого совпадает со значением переданного в API `action` (например, `approve`), а остальные исходящие ветви переводятся в статус `skipped`.

```
                  ┌--["approve"]--> [Execute_Action]
[Human Input] ---┼--["reject"]---> [Cancel_Action]
                  └--["__timeout"]-> [Auto_Reject_Log]
```

### Д. Схождение параллельных веток (Merge / Variable Aggregator)
Используется для объединения результатов условных веток обратно в единый поток.

*   **Входящие связи** (из веток):
    *   `targetType`: `"variable-aggregator"`
    *   `targetHandle`: `"target"`
*   **Исходящая связь** (в общую ветку):
    *   `sourceType`: `"variable-aggregator"`
    *   `sourceHandle`: `"source"`
    *   `targetType`: `"custom"`

```
[Branch A (Code)] --┐
                    ├──> [Variable Aggregator] --(source/target)--> [Next Node]
[Branch B (Code)] --┘
```

### Е. Прямое схождение веток (без Aggregator)
Используется, когда несколько параллельных веток (или ветки после `if-else`/классификатора) соединяются напрямую во входной порт одной стандартной ноды (например, LLM, Code или End) без промежуточного сумматора.

*   **Входящие связи** (из веток):
    *   `targetType`: `"custom"` (или тип целевой ноды)
    *   `targetHandle`: `"target"`
*   **Логика рантайма**:
    *   Целевая нода выполняет роль **барьера синхронизации** (join).
    *   Она ожидает завершения выполнения всех входящих ветвей, которые перешли в статус `succeeded` или `failed`.
    *   If какая-то из входящих ветвей была пропущена (статус `skipped` из-за невыполненного условия `if-else` или другого выбора в `human-input`), рантайм Dify игнорирует эту ветку и не ждет её, а целевая нода запускается сразу после окончания выполнения активных веток.
    *   *Важно*: В отличие от `variable-aggregator`, целевая нода не выполняет слияние данных автоматически — она просто получает доступ ко всему пулу переменных и запускается.

> [!TIP]
> **Верифицировано**: Живые тесты с ветвлением из `human-input` ноды напрямую в `End` ноду (минуя агрегатор) подтвердили, что рантайм Dify v1.14.2 корректно обрабатывает пропущенные ветви и выполняет финальный узел без зависаний.

```
[Branch A (Active)] --┐
                      ├──> [Standard Node (LLM/Code/End)]
[Branch B (Skipped)] -┘
```

---

## 3. Границы изолированных циклов (Iteration & Loop)

Переходы внутри контейнеров итераций и циклов подчиняются строгим правилам изоляции.

### А. Iteration Container (Итератор)
Используется для обработки элементов массива.

1.  **Вход в итератор (Outer Edge)**:
    *   `targetType`: `"iteration"`, `isInIteration: false`, `zIndex: 0`.
2.  **Точка старта внутри (Inner Start)**:
    *   Первая связь идет от служебной ноды `iteration-start` (`type: custom-iteration-start`) к первой рабочей внутренней ноде.
    *   `sourceType`: `"iteration-start"`, `isInIteration: true`, `iteration_id: <container_id>`, `zIndex: 1002`.
3.  **Связи внутри контейнера**:
    *   `isInIteration: true`, `iteration_id: <container_id>`, `zIndex: 1002`.
4.  **Выход из итератора (Outer Edge)**:
    *   `sourceType`: `"iteration"`, `isInIteration: false`, `zIndex: 0`.
    *   *Примечание*: Выходная связь ведет от самого контейнера `iteration`, а не от внутренних нод. Собранные результаты итерации доступны через `output` контейнера.

```
Outer: [Start] --(isInIteration: false)--> [Iteration Container] --(isInIteration: false)--> [End]
                                                 │
                                           (Внутри контейнера)
                                                 ▼
                                           [iteration-start] --(isInIteration: true, zIndex: 1002)--> [Inner_Code]
```

### Б. Loop Container (Цикл)
Используется для повторения шагов с изменяемыми переменными.

1.  **Вход в цикл (Outer Edge)**:
    *   `targetType`: `"loop"`, `isInLoop: false`, `zIndex: 0`.
2.  **Точка старта внутри (Inner Start)**:
    *   Связь от служебной ноды `loop-start` (`type: custom-loop-start`) к первой рабочей внутренней ноде.
    *   `sourceType`: `"loop-start"`, `isInLoop: true`, `loop_id: <container_id>`, `zIndex: 1002`.
3.  **Выход из цикла (Outer Edge)**:
    *   `sourceType`: `"loop"`, `isInLoop: false`, `zIndex: 0`.
    *   *Примечание*: Явной ноды завершения цикла (loop-end) в Dify нет. Цикл завершается автоматически по условиям `break_conditions` или достижению `loop_count`. Исходящая связь идет от родительского контейнера `loop`.

---

## 4. Правила видимости переменных (Variables Context)

При создании переходов Dify строит направленный ациклический граф (DAG). Это накладывает ограничения на доступность переменных:

1.  **Прямая видимость (Upstream Only)**:
    Любая нода может обращаться к выходным переменным только тех нод, которые находятся **строго выше по течению** (предки в графе переходов).
2.  **Изоляция веток (Branch Isolation)**:
    Если граф разделился в `if-else` или `question-classifier`, нода в ветке `A` **не может** прочитать данные из ноды в ветке `B`. Для объединения данных необходимо использовать [nodes/variable-aggregator.md](nodes/variable-aggregator.md).
3.  **Изоляция циклов (Loop/Iteration Isolation)**:
    *   Внутренние ноды цикла/итератора **могут** читать переменные внешних нод (находящихся до контейнера).
    *   Внешние ноды (после контейнера) **не могут** обращаться к переменным внутренних нод напрямую. Доступен только результирующий массив (через `iteration.output`) или обновленные разговорные/цикловые переменные (через `loop.loop_variables`).
    *   Между итерациями цикла `loop` Dify полностью очищает локальные переменные внутренних нод, сохраняя только объявленные `loop_variables`.

---

## 5. Параллельное выполнение веток

Если от одной ноды расходятся несколько исходящих ребер (без использования классификатора или условий), Dify запускает эти ветки **параллельно**:

```
          ┌---> [LLM_Task_A] ---> [Result_A] --┐
[Start] --┤                                    ├──> [Variable Aggregator]
          └---> [LLM_Task_B] ---> [Result_B] --┘
```

*   Каждая ветка выполняется Celery воркером независимо.
*   Блокировка происходит на ноде-синхронизаторе (например, [nodes/variable-aggregator.md](nodes/variable-aggregator.md) или `end`), которая ждет завершения всех входящих в нее путей.
