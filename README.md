# Rakathon 2026 — kdo nedorazí na mamografický screening (VZP)

Предсказываем риск того, что адресно приглашённая клиентка **не пройдёт** маммографический
скрининг в течение 12 месяцев после приглашения; объясняем факторы, сегментируем, предлагаем
интервенции и считаем размер A/B-теста.

## Быстрый старт

```bash
python -m venv .venv
.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"

python -m screening synth                              # Synthetic data -> data/raw/synthetic.parquet
python -m screening profile                            # Data overview and leakage check
python -m screening train --time-budget 60 --n-trials 20
python -m screening score --input data/raw/new.csv     # Risk + segment + intervention -> reports/scored.csv
python -m screening export-ui                          # UI/slide aggregates -> reports/ui/data.json
mlflow ui --backend-store-uri sqlite:///mlflow.db      # http://127.0.0.1:5000
python -m screening power --p 0.10 --mde 0.02          # Sample size per A/B arm

pytest -m "not slow"     # Fast tests; `pytest` also runs the end-to-end test
```

## Данные VZP

1. Положить `Rakhaton2026.csv` в `data/raw/` (папка в `.gitignore`, **данные не коммитим**).
   Конфиг уже указывает на него; формат VZP распознаётся автоматически
   ([vzp.py](src/screening/data/vzp.py): переименование колонок, даты `dd.mm.yyyy`, флаги A/N → 1/0).
2. `python -m screening profile` → `python -m screening train` (~20 мин) → `python -m screening export-ui`.
   Вероятности калибруются (isotonic) на последних 6 мес. train — `calibration:` в конфиге.
   `reports/ui/data.json` содержит только агрегаты (группы < 20 скрыты), без идентификаторов.

Что важно знать о данных (EDA, 1 344 556 приглашений, 508 527 клиенток, 2020–2024):

- Таргет `SCREENING_12M_FLAG`, явка 19,3 %. `SCREENING_3M/6M_FLAG` — исходы ПОСЛЕ T0,
  в модель не идут (схема исключает их как таргеты).
- `PRIOR_INVITATION_COUNT` включает текущее приглашение → адаптер вычитает 1 (0 = первое).
- `PRIOR_SCREEN_COUNT_5Y` считает коды процедур (~2 на скрининг), `NEVER_SCREENED_BEFORE_FLAG`
  = «нет скрининга за 5 лет».
- `INVITATION_SEQUENCE` сбрасывается после явки (серия неответов).
- ~2,7 % приглашений уходят женщинам, прошедшим скрининг 0–6 мес. назад (явка ~2 %) —
  сегмент `recently_screened`.
- Окно 12 мес. закрыто для всех лет (`cutoff_date: 2025-12-31`). Бэктест честный:
  `split.purge_months: 12` — train содержит только приглашения с известным на 1.1.2024 исходом.

## Пайплайн

```
load ─► features ─► out-of-time split (train < test_year, test = test_year)
                     │
                     ├─► FLAML AutoML (GroupKFold по client_id) — выбор семейства моделей
                     │        └─ лучший конфиг LightGBM ─► warm-start для Optuna
                     ├─► Optuna: тюнинг LightGBM, early stopping, MedianPruner
                     ├─► чемпион: FLAML-лучшая vs Optuna-LightGBM на одних и тех же фолдах
                     └─► финальная модель ─► тест vs правило-baseline
                                               ├─ decile / calibration tables
                                               ├─ SHAP (LightGBM) / permutation (иначе)
                                               ├─ сегменты + интервенции
                                               └─ размер A/B по сегментам
```

Всё логируется в MLflow: родительский run `train`, вложенные — `flaml` и каждый
`optuna_trial_N`. CSV-отчёты дублируются в `reports/`, модель — в `models/model.joblib`
(бандл: модель + список признаков + уровни категорий; его читает `score`).

Таргет модели — `non_attendance = 1 − attended_12m` (положительный класс — неявка, ~81 %).

## Структура

| Модуль | Блок задания | Что делает |
|---|---|---|
| `data/load.py`, `data/split.py` | — | загрузка, маппинг колонок, обрезка незакрытого окна, temporal split + GroupKFold |
| `data/synthetic.py` | — | синтетика, откалиброванная под слайд 4 (≈19 % / 45 % / ≈3 %) |
| `features/build.py` | 01 KDO | производные признаки (только из имеющихся колонок) |
| `models/baseline.py` | 01 KDO | правило «число прошлых приглашений» — модель должна его побить |
| `data/profile.py` | — | обзор данных, single-feature AUC для поиска утечек |
| `models/flaml_search.py`, `models/optuna_tune.py` | 01 KDO | FLAML → Optuna |
| `models/champion.py` | 01 KDO | выбор финальной модели по CV на одинаковых фолдах (тест не используется) |
| `scoring.py` | 03 CO | скоринг новых приглашений: риск, дециль, сегмент, интервенция |
| `evaluation/metrics.py` | 01 KDO | AUC, PR-AUC, Brier, precision/lift@top-k, децили, калибровка |
| `evaluation/explain.py` | 02 PROČ | SHAP (LightGBM) или permutation-важности + направление влияния |
| `segments/rules.py` | 02–03 | сегменты-гипотезы со слайда 8 + интервенции |
| `experiment/power.py` | 04 JAK OVĚŘIT | размер выборки для A/B (две пропорции, ITT) |

## Важные оговорки

- **Высокий риск ≠ высокий эффект интервенции.** Модель ранжирует риск; кому интервенция
  *помогает*, покажет только эксперимент (дальше — uplift-модель на его результатах).
- SHAP показывает ассоциации, не причины.
- Одна клиентка встречается в нескольких годах — случайный split завышает метрики.
